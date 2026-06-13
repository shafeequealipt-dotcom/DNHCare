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

from . import config, content, publisher, topics

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dnhcare-bot")

IST = ZoneInfo("Asia/Kolkata")
# Single in-flight draft (one clinic, one editor). {topic, post, html, awaiting_feedback}
PENDING: dict = {}


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
        "/addtopic <topic> – add a topic to the queue\n\n"
        "On each draft: ✅ Approve publishes it live; ✏️ Reject lets you reply with "
        "changes and I'll rewrite.")


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
        PENDING.clear()
        await context.bot.send_message(
            config.TELEGRAM_CHAT_ID,
            f"✅ Published — live in ~1–2 min:\n{url}")
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


def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("generate", cmd_generate))
    app.add_handler(CommandHandler("topics", cmd_topics))
    app.add_handler(CommandHandler("addtopic", cmd_addtopic))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    hh, mm = (int(x) for x in config.POST_TIME.split(":"))
    app.job_queue.run_daily(daily_job, time=datetime.time(hh, mm, tzinfo=IST))
    log.info("DNH Care bot started. Daily post at %s IST.", config.POST_TIME)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
