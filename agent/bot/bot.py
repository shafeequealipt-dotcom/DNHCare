"""DNH Care daily blog agent — Telegram-controlled, draft -> approve -> publish.

Run:  python -m agent.bot.bot        (from the repo root, with .env present)
"""
import asyncio
import datetime
import logging
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          MessageHandler, ContextTypes, filters)

from . import config, content, gbp, insights, publisher, topics

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dnhcare-bot")

IST = ZoneInfo("Asia/Kolkata")
# Single in-flight draft (one clinic, one editor). {topic, post, html, awaiting_feedback}
PENDING: dict = {}
# Topics suggested by the last weekly GBP digest, keyed by the index shown in the
# message so an "Add" button tap can look the text back up.
PENDING_TOPICS: dict = {}


def _only_owner(update: Update) -> bool:
    chat = update.effective_chat
    return chat is not None and chat.id == config.TELEGRAM_CHAT_ID


def _kb():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve & publish", callback_data="approve"),
        InlineKeyboardButton("✏️ Reject", callback_data="reject"),
    ]])


def _preview(post) -> str:
    body = post.sections[0].paragraphs[0] if post.sections and post.sections[0].paragraphs else post.lede
    return (f"<b>{post.title}</b>\n"
            f"<i>{post.category} · {post.read_minutes} min read</i>\n\n"
            f"{post.meta_description}\n\n"
            f"{body[:300]}…\n\n"
            f"<code>blog/{post.slug}.html</code>")


def _generate_blocking(topic: str | None, feedback: str = ""):
    """All the network/git/subprocess work — run off the event loop."""
    publisher.sync_main()
    auto_note = None
    if topic is None:
        topic = topics.next_topic()
        if topic is None:
            topic = topics.autoselect_viral_topic()
            topics.add_topic(topic)
            auto_note = topic
    post = content.generate_post(topic, feedback)
    # Guard: never overwrite a live post. If this slug is already published, it's a
    # duplicate — surface it instead of silently clobbering the existing article.
    if publisher.slug_is_published(post.slug):
        raise RuntimeError(
            f"duplicate: a post with slug '{post.slug}' is already published "
            f"(blog/{post.slug}.html). Topic was: {topic}. Send /generate to try a "
            f"fresh topic, or /addtopic a new angle."
        )
    recent = publisher.recent_posts(2)
    html = content.render_html(post, recent)
    path = publisher.stage_draft(post.slug, html)
    ok, out = publisher.run_gate(path)
    if not ok:
        # one self-correction pass using the gate output as feedback
        post = content.generate_post(topic, feedback + "\nSafety/quality gate said:\n" + out)
        html = content.render_html(post, publisher.recent_posts(2))
        path = publisher.stage_draft(post.slug, html)
        ok, out = publisher.run_gate(path)
    return {"topic": topic, "post": post, "html": html, "ok": ok, "gate": out, "auto": auto_note}


async def generate_and_send(context: ContextTypes.DEFAULT_TYPE, topic=None, feedback=""):
    chat_id = config.TELEGRAM_CHAT_ID
    await context.bot.send_message(chat_id, "✍️ Writing today's draft… (~1 min)")
    try:
        res = await asyncio.to_thread(_generate_blocking, topic, feedback)
    except Exception as e:  # noqa
        log.exception("generation failed")
        await context.bot.send_message(chat_id, f"⚠️ Generation failed: {e}")
        return
    if not res["ok"]:
        publisher.discard(res["post"].slug)
        await context.bot.send_message(
            chat_id, "⚠️ Draft did not pass the safety gate twice:\n"
                     f"<pre>{res['gate']}</pre>\nSend /generate to try a fresh topic.",
            parse_mode=ParseMode.HTML)
        return
    PENDING.clear()
    PENDING.update({"topic": res["topic"], "post": res["post"],
                    "html": res["html"], "awaiting_feedback": False})
    note = (f"🌶️ Auto-picked a trending topic: <i>{res['auto']}</i>\n\n"
            if res["auto"] else "")
    await context.bot.send_message(chat_id, note + _preview(res["post"]),
                                   parse_mode=ParseMode.HTML, reply_markup=_kb())


# ---------------- handlers ----------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _only_owner(update):
        return
    await update.message.reply_text(
        "DNH Care blog agent.\n\n"
        "Every day I draft a post and send it here for your approval.\n\n"
        "Commands:\n"
        "/generate – write a draft now\n"
        "/topics – show the topic queue\n"
        "/addtopic <topic> – add a topic to the queue\n"
        "/model – show the current writing model\n"
        "/models – list all available Groq models, numbered\n"
        "/setmodel <number> – switch to a model by its number from /models\n"
        "/gbp – Google Business Profile auto-post status; /gbp on | off; "
        "/gbp cta call | learn\n"
        "/report – GBP weekly performance + search-keyword digest, on demand "
        "(also sent automatically)\n"
        "/time – show the daily post time\n"
        "/settime HH:MM – set the daily post time (IST)\n"
        "/prompt – show the content-generation prompt\n"
        "/setprompt <text> – update the prompt (also editable on GitHub)\n\n"
        "On each draft: ✅ Approve publishes it live; ✏️ Reject lets you reply with "
        "changes and I'll rewrite.")


def _schedule_daily(job_queue):
    """(Re)schedule the daily post job from the persisted time. Returns the time string."""
    for j in job_queue.get_jobs_by_name("daily_post"):
        j.schedule_removal()
    val = config.get_post_time()
    hh, mm = (int(x) for x in val.split(":"))
    job_queue.run_daily(daily_job, time=datetime.time(hh, mm, tzinfo=IST), name="daily_post")
    return val


async def cmd_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _only_owner(update):
        return
    await update.message.reply_text(f"Daily post time: {config.get_post_time()} IST")


async def cmd_settime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _only_owner(update):
        return
    arg = " ".join(context.args).strip()
    try:
        val = config.set_post_time(arg)
    except Exception:  # noqa
        await update.message.reply_text("Usage: /settime 06:30   (24-hour, IST)")
        return
    _schedule_daily(context.job_queue)
    await update.message.reply_text(f"Daily post time set to {val} IST. "
                                    "A draft will arrive then each day.")


async def cmd_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _only_owner(update):
        return
    text = publisher.read_prompt() or "(using built-in default prompt)"
    await update.message.reply_text(
        "Current content prompt (edit on GitHub at agent/content_prompt.txt, "
        "or send /setprompt followed by new text):\n\n" + text[:3500])


async def cmd_setprompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _only_owner(update):
        return
    parts = update.message.text.split(None, 1)
    body = parts[1].strip() if len(parts) > 1 else ""
    if len(body) < 40:
        await update.message.reply_text(
            "Send /setprompt followed by the full prompt text (keep the {clinic} and "
            "{categories} placeholders). Tip: edit agent/content_prompt.txt on GitHub for long edits.")
        return
    await update.message.reply_text("Updating the content prompt on GitHub…")
    try:
        await asyncio.to_thread(publisher.update_prompt, body)
    except Exception as e:  # noqa
        log.exception("prompt update failed")
        await update.message.reply_text(f"⚠️ Prompt update failed: {e}")
        return
    await update.message.reply_text("✅ Content prompt updated and committed. "
                                    "It takes effect on the next /generate.")


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _only_owner(update):
        return
    await update.message.reply_text(f"Current writing model:\n<code>{config.get_model()}</code>",
                                    parse_mode=ParseMode.HTML)


async def cmd_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _only_owner(update):
        return
    await update.message.reply_text("Fetching the current available models from Groq…")
    try:
        ids = await asyncio.to_thread(llm.list_models)
    except Exception as e:  # noqa
        log.exception("model list fetch failed")
        await update.message.reply_text(
            f"⚠️ Couldn't fetch the live list ({e}). Falling back to presets.")
        ids = list(config.PRESET_MODELS)
    if not ids:
        ids = list(config.PRESET_MODELS)
    config.set_model_menu(ids)          # persist the numbering for /setmodel <n>
    cur = config.get_model()
    lines = [f"{i} - {m}" + ("  ✅ current" if m == cur else "")
             for i, m in enumerate(ids, 1)]
    body = "\n".join(lines)
    tail = "\n\nSwitch with /setmodel <number> — e.g. /setmodel 3"
    # Telegram hard-limits messages at 4096 chars; chunk if the roster is huge.
    while body:
        chunk, body = body[:3500], body[3500:]
        if body:
            cut = chunk.rfind("\n")
            if cut > 0:
                body, chunk = chunk[cut + 1:] + body, chunk[:cut]
        await update.message.reply_text(
            f"Available Groq models ({len(ids)}):\n\n{chunk}" + (tail if not body else ""))


async def cmd_setmodel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _only_owner(update):
        return
    arg = " ".join(context.args).strip()
    if not arg:
        await update.message.reply_text(
            "Usage: /setmodel <number>  (run /models to see the numbered list)\n"
            "You can also pass a full model id, e.g. /setmodel openai/gpt-oss-20b:free")
        return
    # A bare number selects from the last /models menu; anything else is a raw model id.
    if arg.isdigit():
        menu = config.get_model_menu()
        if not menu:
            await update.message.reply_text(
                "No model list yet — run /models first, then /setmodel <number>.")
            return
        n = int(arg)
        if not (1 <= n <= len(menu)):
            await update.message.reply_text(
                f"Pick a number between 1 and {len(menu)} (run /models to see them).")
            return
        mid = menu[n - 1]
    else:
        mid = arg
    config.set_model(mid)
    await update.message.reply_text(f"Writing model set to:\n<code>{mid}</code>",
                                    parse_mode=ParseMode.HTML)


async def cmd_gbp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _only_owner(update):
        return
    arg = (" ".join(context.args)).strip().lower()
    if arg in ("on", "off"):
        config.set_gbp_enabled(arg == "on")
    elif arg.startswith("cta"):
        rest = arg[3:].strip()
        if rest in ("call", "learn", "learn_more", "learnmore"):
            config.set_gbp_cta(rest)
        else:
            await update.message.reply_text("Usage: /gbp cta call  or  /gbp cta learn")
            return
    if not gbp.is_configured():
        await update.message.reply_text(
            "Google Business Profile is NOT configured yet — the bot publishes the "
            "blog only.\nSetup: add GBP_CLIENT_ID/SECRET to agent/bot/.env, then run "
            "`python3 -m agent.bot.gbp_auth login` and `… discover` on the VM and add "
            "the printed values. See agent/bot/gbp_auth.py.")
        return
    state = "ON ✅" if config.gbp_enabled() else "OFF ⏸"
    cta = config.gbp_cta()
    cta_desc = ("Call now 📞 (clinic number; blog URL as plain text in the post)"
                if cta == "CALL" else "Learn more 🔗 (clickable link to the blog post)")
    await update.message.reply_text(
        f"Google Business Profile auto-post is {state}.\n"
        f"CTA button: {cta_desc}\n\n"
        "On ✅ Approve, the blog is published AND shared to the clinic's Google "
        "listing.\nToggle with /gbp on | /gbp off.\n"
        "Switch button with /gbp cta call | /gbp cta learn.")


async def cmd_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _only_owner(update):
        return
    await generate_and_send(context)


async def cmd_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _only_owner(update):
        return
    q = topics.list_queue()
    if not q:
        await update.message.reply_text("Queue is empty — I'll auto-pick a viral topic next run.")
        return
    lines = "\n".join(f"{i+1}. {t}" for i, t in enumerate(q[:20]))
    await update.message.reply_text(f"Topic queue ({len(q)}):\n{lines}")


async def cmd_addtopic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _only_owner(update):
        return
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Usage: /addtopic [Skin] Why winter worsens eczema")
        return
    added = topics.add_topic(text)
    await update.message.reply_text(f"Added to the queue:\n{added}")


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.message.chat.id != config.TELEGRAM_CHAT_ID:
        return
    if q.data.startswith("m:"):
        idx = int(q.data[2:])
        model = config.PRESET_MODELS[idx]
        config.set_model(model)
        await q.edit_message_text(f"Writing model set to:\n{model}")
        return
    if q.data.startswith("t:"):
        idx = int(q.data[2:])
        topic = PENDING_TOPICS.get(idx)
        if not topic:
            await context.bot.send_message(config.TELEGRAM_CHAT_ID,
                                           "That suggestion expired — run /report again.")
            return
        added = topics.add_topic(topic)
        await context.bot.send_message(config.TELEGRAM_CHAT_ID,
                                       f"Added to the queue:\n{added}")
        return
    if not PENDING.get("post"):
        await q.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(config.TELEGRAM_CHAT_ID,
                                       "That draft expired. Send /generate for a new one.")
        return
    if q.data == "approve":
        await q.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(config.TELEGRAM_CHAT_ID, "📤 Publishing…")
        try:
            url = await asyncio.to_thread(publisher.publish, PENDING["post"],
                                          PENDING["html"], PENDING["topic"])
        except Exception as e:  # noqa
            log.exception("publish failed")
            await context.bot.send_message(config.TELEGRAM_CHAT_ID, f"⚠️ Publish failed: {e}")
            return
        post = PENDING["post"]
        PENDING.clear()
        await context.bot.send_message(
            config.TELEGRAM_CHAT_ID,
            f"✅ Published — live in ~1–2 min:\n{url}")
        # Also share on the clinic's Google Business Profile (isolated: a GBP
        # failure never affects the already-published blog post).
        if gbp.is_enabled():
            clean_url = f"https://dnhcare.co.in/blog/{post.slug}"
            try:
                gbp_name = await asyncio.to_thread(
                    gbp.create_local_post, content.gbp_blurb(post), clean_url)
                config.record_gbp_post(post.title, gbp_name)
                await context.bot.send_message(
                    config.TELEGRAM_CHAT_ID,
                    "📍 Also posted to the clinic's Google Business Profile.")
            except Exception as e:  # noqa
                log.exception("GBP post failed")
                await context.bot.send_message(
                    config.TELEGRAM_CHAT_ID,
                    f"⚠️ Blog is live, but the Google Business Profile post "
                    f"failed: {e}\n(/gbp off silences this until fixed.)")
    elif q.data == "reject":
        PENDING["awaiting_feedback"] = True
        await q.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            config.TELEGRAM_CHAT_ID,
            "✏️ Reply with the changes you want and I'll rewrite the post.")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _only_owner(update):
        return
    if PENDING.get("awaiting_feedback"):
        feedback = update.message.text.strip()
        topic = PENDING.get("topic")
        publisher.discard(PENDING.get("post").slug)
        PENDING.clear()
        await generate_and_send(context, topic=topic, feedback=feedback)


async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    await generate_and_send(context)


async def _send_gbp_digest(context: ContextTypes.DEFAULT_TYPE):
    """Build and send the weekly GBP performance digest, with tap-to-add buttons
    for any suggested topics. Isolated: any failure here never touches posting."""
    chat_id = config.TELEGRAM_CHAT_ID
    if not gbp.is_configured():
        return  # silent — the feature is dormant, not an error
    try:
        text, suggestions = await asyncio.to_thread(insights.build_digest)
    except Exception as e:  # noqa
        log.exception("GBP digest failed")
        await context.bot.send_message(chat_id, f"⚠️ Weekly GBP report failed: {e}")
        return
    PENDING_TOPICS.clear()
    rows = []
    for i, s in enumerate(suggestions, 1):
        PENDING_TOPICS[i] = s
        rows.append([InlineKeyboardButton(f"Add #{i} to queue", callback_data=f"t:{i}")])
    kb = InlineKeyboardMarkup(rows) if rows else None
    await context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML,
                                   reply_markup=kb)


def _schedule_weekly_report(job_queue):
    for j in job_queue.get_jobs_by_name("weekly_gbp_report"):
        j.schedule_removal()
    hh, mm = (int(x) for x in config.REPORT_TIME.split(":"))
    job_queue.run_daily(_send_gbp_digest, time=datetime.time(hh, mm, tzinfo=IST),
                        days=(config.REPORT_DAY,), name="weekly_gbp_report")


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _only_owner(update):
        return
    if not gbp.is_configured():
        await update.message.reply_text(
            "Google Business Profile is not configured — no report to show. "
            "See /gbp for setup.")
        return
    await update.message.reply_text("📊 Building this week's GBP report…")
    await _send_gbp_digest(context)


def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("generate", cmd_generate))
    app.add_handler(CommandHandler("topics", cmd_topics))
    app.add_handler(CommandHandler("addtopic", cmd_addtopic))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("models", cmd_models))
    app.add_handler(CommandHandler("setmodel", cmd_setmodel))
    app.add_handler(CommandHandler("gbp", cmd_gbp))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("time", cmd_time))
    app.add_handler(CommandHandler("settime", cmd_settime))
    app.add_handler(CommandHandler("prompt", cmd_prompt))
    app.add_handler(CommandHandler("setprompt", cmd_setprompt))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    val = _schedule_daily(app.job_queue)
    if gbp.is_configured():
        _schedule_weekly_report(app.job_queue)
    log.info("DNH Care bot started. Daily post at %s IST. Publishing to '%s'.",
             val, config.PUBLISH_BRANCH)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
