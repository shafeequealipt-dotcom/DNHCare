"""One-time Google Business Profile OAuth bootstrap (run manually, NOT by the bot).

Produces the three .env values the bot needs:
  GBP_REFRESH_TOKEN   (step 1 — consent flow)
  GBP_ACCOUNT_ID      (step 2 — discovery)
  GBP_LOCATION_ID     (step 2 — discovery)

Usage (from the repo root, with GBP_CLIENT_ID + GBP_CLIENT_SECRET already in
agent/bot/.env or exported):

  1) python3 -m agent.bot.gbp_auth login
       Prints a Google consent URL. Open it in any browser, sign in with the
       Google account that OWNS the clinic's Business Profile, approve, and
       paste the code back. Prints the GBP_REFRESH_TOKEN line to add to .env.

  2) python3 -m agent.bot.gbp_auth discover
       (needs GBP_REFRESH_TOKEN in .env) Lists your accounts and locations and
       prints the GBP_ACCOUNT_ID / GBP_LOCATION_ID lines to add to .env.

Uses the OAuth out-of-band-style manual copy/paste flow via the loopback-less
"urn:ietf:wg:oauth:2.0:oob" replacement: a local HTTP-free manual code paste
(redirect to localhost is not usable on a headless VM, so we use the
device-style manual flow with redirect_uri=urn:ietf:wg:oauth:2.0:oob when
allowed, falling back to instructing an explicit localhost copy).
"""
import json
import sys
import urllib.request
import urllib.parse
from . import config

SCOPE = "https://www.googleapis.com/auth/business.manage"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
# Desktop-app clients accept the local redirect; on a headless box the browser
# will land on an unreachable localhost URL — the code is still in that URL's
# ?code= parameter, which the user copies back here.
REDIRECT = "http://localhost:8765"
ACCT_MGMT = "https://mybusinessaccountmanagement.googleapis.com/v1"
BIZ_INFO = "https://mybusinessbusinessinformation.googleapis.com/v1"


def _require(*pairs):
    missing = [n for n, v in pairs if not v]
    if missing:
        sys.exit(f"Missing in .env / environment: {', '.join(missing)}")


def login():
    _require(("GBP_CLIENT_ID", config.GBP_CLIENT_ID),
             ("GBP_CLIENT_SECRET", config.GBP_CLIENT_SECRET))
    params = urllib.parse.urlencode({
        "client_id": config.GBP_CLIENT_ID,
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",     # -> refresh token
        "prompt": "consent",          # force refresh token even on re-consent
    })
    print("\n1. Open this URL in a browser and approve with the account that")
    print("   owns the clinic's Business Profile:\n")
    print(f"   {AUTH_URL}?{params}\n")
    print("2. After approving, the browser goes to a localhost URL that won't")
    print("   load — that's fine. Copy the value of the `code=` parameter from")
    print("   the address bar (everything between code= and the next &).\n")
    code = input("Paste the code here: ").strip()
    body = urllib.parse.urlencode({
        "client_id": config.GBP_CLIENT_ID,
        "client_secret": config.GBP_CLIENT_SECRET,
        "code": urllib.parse.unquote(code),
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.load(r)
    rt = tok.get("refresh_token")
    if not rt:
        sys.exit(f"No refresh_token in response (got keys: {list(tok)}). "
                 "Re-run and ensure prompt=consent screen appeared.")
    print("\nAdd this line to agent/bot/.env:\n")
    print(f"GBP_REFRESH_TOKEN={rt}\n")


def _get(url):
    from .gbp import _access_token  # reuse the refresh flow
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {_access_token()}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def discover():
    _require(("GBP_CLIENT_ID", config.GBP_CLIENT_ID),
             ("GBP_CLIENT_SECRET", config.GBP_CLIENT_SECRET),
             ("GBP_REFRESH_TOKEN", config.GBP_REFRESH_TOKEN))
    accts = _get(ACCT_MGMT + "/accounts").get("accounts", [])
    if not accts:
        sys.exit("No Business Profile accounts visible to this Google account.")
    for a in accts:
        aid = a["name"].split("/")[-1]
        print(f"\nAccount: {a.get('accountName', '?')}  ->  GBP_ACCOUNT_ID={aid}")
        locs = _get(f"{BIZ_INFO}/accounts/{aid}/locations"
                    "?readMask=name,title,storefrontAddress").get("locations", [])
        for l in locs:
            lid = l["name"].split("/")[-1]
            print(f"  Location: {l.get('title', '?')}  ->  GBP_LOCATION_ID={lid}")
    print("\nAdd the matching GBP_ACCOUNT_ID and GBP_LOCATION_ID lines to agent/bot/.env\n")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "login":
        login()
    elif cmd == "discover":
        discover()
    else:
        print(__doc__)
