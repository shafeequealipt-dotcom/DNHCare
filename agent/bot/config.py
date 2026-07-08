"""Central config — Telegram creds from system env (DNH_Telegram_*), Groq for
content generation, runtime-switchable model persisted in state.json."""
import os
import json
from dotenv import load_dotenv

# Load agent/bot/.env (does NOT override real system env vars).
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def _env(*names, default=None, required=False):
    """Return the first env var found among `names` (case-insensitive on Windows,
    exact on Linux — so we list common casings)."""
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    if required:
        raise RuntimeError(f"Missing required env var (any of): {', '.join(names)}")
    return default


# ---- Telegram (from the user's system env: DNH_Telegram_Token / DNH_Telegram_ID) ----
TELEGRAM_BOT_TOKEN = _env("DNH_Telegram_Token", "DNH_TELEGRAM_TOKEN",
                          "TELEGRAM_BOT_TOKEN", required=True)
TELEGRAM_CHAT_ID = int(_env("DNH_Telegram_ID", "DNH_TELEGRAM_ID",
                            "TELEGRAM_CHAT_ID", required=True))

# ---- Groq (OpenAI-compatible) for content generation ----
GROQ_API_KEY = _env("DNHCARE_Groq_Api", "GROQ_API_KEY", required=True)
GROQ_BASE_URL = _env("GROQ_BASE_URL", default="https://api.groq.com/openai/v1")

# Fallback list shown by /models when the LIVE roster fetch fails. The live fetch
# (llm.list_models) normally returns Groq's full current chat-capable catalog;
# this list only kicks in as a safety net. Groq's roster changes over time —
# refresh with /models or set any id with /setmodel.
PRESET_MODELS = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "qwen/qwen3-32b",
    "qwen/qwen3.6-27b",
    "llama-3.1-8b-instant",
    "groq/compound",
    "groq/compound-mini",
    "allam-2-7b",
]
DEFAULT_MODEL = _env("DEFAULT_MODEL", default=PRESET_MODELS[0])

# ---- Google Business Profile local posts (ALL optional — feature stays dormant
#      until every var is set in .env; see agent/bot/gbp_auth.py for the one-time
#      OAuth bootstrap that produces the refresh token + IDs) ----
GBP_CLIENT_ID = _env("GBP_CLIENT_ID")
GBP_CLIENT_SECRET = _env("GBP_CLIENT_SECRET")
GBP_REFRESH_TOKEN = _env("GBP_REFRESH_TOKEN")
GBP_ACCOUNT_ID = _env("GBP_ACCOUNT_ID")      # numeric id from accounts/{id}
GBP_LOCATION_ID = _env("GBP_LOCATION_ID")    # numeric id from locations/{id}
# Optional: public https image attached to every GBP post (dormant if unset).
GBP_POST_IMAGE_URL = _env("GBP_POST_IMAGE_URL")

# ---- GitHub publish target (token from env — set DNH_Github_Token or GITHUB_TOKEN) ----
GITHUB_TOKEN = _env("DNH_Github_Token", "DNH_GITHUB_TOKEN", "GITHUB_TOKEN", required=True)
GITHUB_REPO = _env("GITHUB_REPO", default="shafeequealipt-dotcom/DNHCare")
REPO_DIR = _env("REPO_DIR", required=True)
POST_TIME = _env("POST_TIME", default="06:00")  # default/seed; live value lives in state.json
# Weekly GBP performance digest — day (0=Mon..6=Sun) and time (IST). Static env,
# no /set command yet; edit .env + restart to change.
REPORT_DAY = int(_env("REPORT_DAY", default="0"))
REPORT_TIME = _env("REPORT_TIME", default="09:00")
# Branch the bot publishes to. main = live (auto-deploys). Use development for a dry run.
PUBLISH_BRANCH = _env("PUBLISH_BRANCH", default="main")

BLOG_DIR = os.path.join(REPO_DIR, "blog")
TOPICS_FILE = os.path.join(REPO_DIR, "agent", "topics.md")
SITEMAP_FILE = os.path.join(REPO_DIR, "sitemap.xml")
CHECK_SCRIPT = os.path.join(REPO_DIR, "agent", "check_post.py")
# Editable content-generation prompt (edit on GitHub, or via Telegram /setprompt).
PROMPT_FILE = os.path.join(REPO_DIR, "agent", "content_prompt.txt")
# Runtime state lives beside the code (gitignored) so git resets in REPO_DIR don't wipe it.
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

# Brand facts (kept in sync with CAVEMAN.md)
CLINIC_NAME = "Dr. Nafia's Homoeopathic Medical Centre"
PHONE = "+91 96637 79358"
WA = "https://wa.me/919663779358"
ADDRESS_LINE = "Opp. KK School, Gunjur Main Road, Varthur, Bengaluru, Karnataka 560087"

CATEGORY_SERVICE = {
    "Skin": ("skin-treatment.html", "Homeopathy for skin complaints"),
    "Allergies": ("allergy-treatment.html", "Homeopathy for allergies & sinusitis"),
    "Children": ("pediatric-care.html", "Homeopathic care for children"),
    "Migraine": ("migraine-treatment.html", "Homeopathic migraine & headache care"),
    "Women": ("womens-health.html", "Women's health & thyroid support"),
}
CATEGORIES = list(CATEGORY_SERVICE.keys())


# ---- runtime model state (switchable from Telegram) ----
def _read_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def get_model() -> str:
    return _read_state().get("model", DEFAULT_MODEL)


def set_model(model_id: str):
    state = _read_state()
    state["model"] = model_id.strip()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)
    return state["model"]


# ---- numbered model menu (the list last shown by /models), persisted so that
#      /setmodel <number> maps to exactly what the user saw, even as the live
#      free roster shifts between calls. ----
def set_model_menu(ids: list) -> list:
    state = _read_state()
    state["model_menu"] = list(ids)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)
    return state["model_menu"]


def get_model_menu() -> list:
    return _read_state().get("model_menu", [])


# ---- Google Business Profile toggle (runtime /gbp on|off, persisted) ----
def gbp_enabled() -> bool:
    return bool(_read_state().get("gbp_enabled", True))  # default ON once configured


def set_gbp_enabled(on: bool) -> bool:
    state = _read_state()
    state["gbp_enabled"] = bool(on)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)
    return state["gbp_enabled"]


# ---- GBP call-to-action type (runtime /gbp cta call|learn, persisted) ----
def gbp_cta() -> str:
    """"CALL" (default — Call-now button using the clinic's listed number) or
    "LEARN_MORE" (clickable link to the blog post)."""
    v = _read_state().get("gbp_cta", "CALL")
    return v if v in ("CALL", "LEARN_MORE") else "CALL"


def set_gbp_cta(v: str) -> str:
    v = v.strip().upper()
    if v in ("LEARN", "LEARN_MORE", "LEARNMORE"):
        v = "LEARN_MORE"
    else:
        v = "CALL"
    state = _read_state()
    state["gbp_cta"] = v
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)
    return v


# ---- recent GBP local posts (title + resource name), so the weekly digest can
#      report which post performed best via localPosts.reportInsights. Capped
#      to the most recent 15; oldest drop off automatically. ----
def record_gbp_post(title: str, resource_name: str):
    state = _read_state()
    posts = state.get("gbp_posts", [])
    posts.insert(0, {"title": title, "name": resource_name})
    state["gbp_posts"] = posts[:15]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def get_gbp_posts(n: int = 5) -> list:
    return _read_state().get("gbp_posts", [])[:n]


# ---- daily post time (switchable from Telegram), persisted ----
def get_post_time() -> str:
    return _read_state().get("post_time", POST_TIME)


def set_post_time(hhmm: str) -> str:
    """Validate and persist an HH:MM (24h IST) post time. Returns the normalized value."""
    h_str, _, m_str = hhmm.strip().partition(":")
    h, m = int(h_str), int(m_str)
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError("time must be 00:00–23:59")
    val = f"{h:02d}:{m:02d}"
    state = _read_state()
    state["post_time"] = val
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)
    return val
