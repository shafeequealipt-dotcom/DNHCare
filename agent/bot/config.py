"""Central config — loads .env, defines brand constants, category -> service mapping."""
import os
from dotenv import load_dotenv

# Load agent/bot/.env regardless of the current working directory.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ.get("GITHUB_REPO", "shafeequealipt-dotcom/DNHCare")
REPO_DIR = os.environ["REPO_DIR"]
POST_TIME = os.environ.get("POST_TIME", "06:00")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")
CLAUDE_EFFORT = os.environ.get("CLAUDE_EFFORT", "medium")

BLOG_DIR = os.path.join(REPO_DIR, "blog")
TOPICS_FILE = os.path.join(REPO_DIR, "agent", "topics.md")
SITEMAP_FILE = os.path.join(REPO_DIR, "sitemap.xml")
CHECK_SCRIPT = os.path.join(REPO_DIR, "agent", "check_post.py")

# Brand facts (kept in sync with CAVEMAN.md)
CLINIC_NAME = "Dr. Nafia's Homoeopathic Medical Centre"
PHONE = "+91 96637 79358"
WA = "https://wa.me/919663779358"
ADDRESS_LINE = "Opp. KK School, Gunjur Main Road, Varthur, Bengaluru, Karnataka 560087"

# category -> (service page filename, nice service label)
CATEGORY_SERVICE = {
    "Skin": ("skin-treatment.html", "Homeopathy for skin complaints"),
    "Allergies": ("allergy-treatment.html", "Homeopathy for allergies & sinusitis"),
    "Children": ("pediatric-care.html", "Homeopathic care for children"),
    "Migraine": ("migraine-treatment.html", "Homeopathic migraine & headache care"),
    "Women": ("womens-health.html", "Women's health & thyroid support"),
}
CATEGORIES = list(CATEGORY_SERVICE.keys())
