"""Topic queue management — read/add/consume topics in agent/topics.md,
and auto-pick a viral, current, healthcare topic via Claude when the queue is low."""
import re
import datetime
from . import config, llm

_QUEUE_HDR = "## Queue (oldest first = next up)"
_DONE_HDR = "## Done (most recent first)"


def _read():
    with open(config.TOPICS_FILE, encoding="utf-8") as f:
        return f.read()


def _write(text):
    with open(config.TOPICS_FILE, "w", encoding="utf-8") as f:
        f.write(text)


def _split(text):
    """Return (head, queue_lines, done_block)."""
    qi = text.index(_QUEUE_HDR) + len(_QUEUE_HDR)
    di = text.index(_DONE_HDR)
    head = text[: text.index(_QUEUE_HDR) + len(_QUEUE_HDR)]
    queue_raw = text[qi:di]
    done_block = text[di:]
    queue_lines = [l for l in queue_raw.splitlines() if l.strip().startswith("- ")]
    return head, queue_lines, done_block


def list_queue():
    _, q, _ = _split(_read())
    return [l.strip()[2:].strip() for l in q]


def queue_count():
    return len(list_queue())


def add_topic(topic: str):
    """Append a topic to the bottom of the queue. Returns the cleaned topic line."""
    topic = topic.strip()
    if not topic.startswith("["):
        topic = "[General] " + topic  # tag optional; agent tolerates it
    text = _read()
    head, q, done = _split(text)
    q.append(f"- {topic}")
    new = head + "\n" + "\n".join(q) + "\n\n" + done
    _write(new)
    return topic


def next_topic():
    """Return the first queued topic string (without removing it), or None."""
    q = list_queue()
    return q[0] if q else None


def mark_done(topic: str, slug: str):
    """Move a topic from Queue to Done with today's date + filename."""
    text = _read()
    head, q, done = _split(text)
    q = [l for l in q if l.strip()[2:].strip() != topic.strip()]
    today = datetime.date.today().isoformat()
    done_lines = done.splitlines()
    insert_at = 1 if len(done_lines) > 1 else len(done_lines)
    done_lines.insert(insert_at, f"- {today} {topic}  -> {slug}.html")
    new = head + "\n" + "\n".join(q) + "\n\n" + "\n".join(done_lines) + "\n"
    _write(new)


def autoselect_viral_topic() -> str:
    """Ask the current OpenRouter model for ONE timely, shareable, healthcare-relevant
    blog topic suited to the clinic. Returns a '[Category] Title' line."""
    cats = " / ".join(config.CATEGORIES)
    today = datetime.date.today()
    month = today.strftime("%B")
    resp = llm.chat(
        temperature=0.8,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": (
                "You plan content for a homeopathy clinic in Varthur, Bengaluru "
                f"(Dr. Nafia's Homoeopathic Medical Centre). Categories: {cats}.\n"
                f"It is {month} {today.year} in Bengaluru, India. Considering the "
                "current season, typical weather, and health concerns common at this "
                "time of year, propose ONE blog topic that is timely, highly "
                "shareable, and genuinely useful. It MUST map to one of the categories "
                "and stay within safe, non-overclaiming homeopathy content.\n\n"
                "Reply with EXACTLY one line and nothing else, in this format:\n"
                "[Category] Title of the post"
            ),
        }],
    )
    text = (resp.choices[0].message.content or "").strip()
    line = next((l.strip() for l in reversed(text.splitlines())
                 if re.match(r"^\[[A-Za-z]+\]\s+.+", l.strip())), None)
    if not line:
        line = "[Skin] Seasonal skin care: a gentle homeopathic perspective"
    return line
