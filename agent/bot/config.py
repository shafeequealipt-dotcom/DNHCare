"""Central config — Telegram creds from system env (DNH_Telegram_*), OpenRouter for
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

# ---- OpenRouter (OpenAI-compatible) for content generation ----
OPENROUTER_API_KEY = _env("OPENROUTER_API_KEY", required=True)
OPENROUTER_BASE_URL = _env("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")

# Free models selectable from Telegram. /setmodel <id> accepts any OpenRouter id.
# (OpenRouter's free roster changes over time — refresh with /models or /setmodel.)
PRESET_MODELS = [
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-120b:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]
DEFAULT_MODEL = _env("DEFAULT_MODEL", default=PRESET_MODELS[0])

# ---- GitHub publish target ----
GITHUB_TOKEN = _env("GITHUB_TOKEN", required=True)
GITHUB_REPO = _env("GITHUB_REPO", default="shafeequealipt-dotcom/DNHCare")
REPO_DIR = _env("REPO_DIR", required=True)
POST_TIME = _env("POST_TIME", default="06:00")

BLOG_DIR = os.path.join(REPO_DIR, "blog")
TOPICS_FILE = os.path.join(REPO_DIR, "agent", "topics.md")
SITEMAP_FILE = os.path.join(REPO_DIR, "sitemap.xml")
CHECK_SCRIPT = os.path.join(REPO_DIR, "agent", "check_post.py")
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
