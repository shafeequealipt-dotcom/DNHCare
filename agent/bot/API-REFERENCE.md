# API Integration Reference — where to change what

This bot depends on three external APIs. Whenever a key expires, a provider gets
swapped, or an endpoint changes, this is the checklist of every file that touches
it. Provider swap history: OpenRouter → Groq (2026-07-08) → Cloudflare Workers AI
(2026-07-16). Both swaps are worked examples throughout — read both gotcha lists
below before starting a new one; the failure modes differ per provider.

---

## 1. LLM provider (currently Cloudflare Workers AI) — content generation

Used for: blog post generation, GBP post blurbs, daily topic auto-pick, weekly
digest topic suggestions. All calls funnel through one client (`llm.py`), so a
provider swap touches a small, fixed set of files.

| File | What lives there |
|---|---|
| `agent/bot/config.py` | `CF_API_TOKEN` / `CF_ACCOUNT_ID` / `CF_BASE_URL` env vars (`DNH_CloudFlare_API`, `DNH_CloudFlare_AccountID`); `PRESET_MODELS` (fallback model list shown by `/models` if the live fetch fails); `DEFAULT_MODEL` |
| `agent/bot/llm.py` | The actual `OpenAI(base_url=..., api_key=...)` client; `list_models()` (live model-list fetch); `chat()` (the one function every other module calls) |
| `agent/bot/bot.py` | `cmd_models()` calls `llm.list_models()`; user-facing text ("Fetching models from Cloudflare…") |
| `agent/bot/content.py`, `agent/bot/topics.py`, `agent/bot/insights.py` | Call `llm.chat(...)` — provider-agnostic, no changes needed on a swap. Only their docstrings/comments name the provider. |
| `agent/bot/.env.example` | Template env var names + a realistic value format |
| `CAVEMAN.md` (DAILY AGENT section) | High-level description of the provider + model list |
| `agent/bot/SETUP-ORACLE.md` | Fresh-VM setup instructions |

### Checklist for a provider swap
1. **config.py**: add the new provider's `_env(...)` lines (API key + base URL); update `PRESET_MODELS` to that provider's real current model ids; update `DEFAULT_MODEL`.
2. **llm.py**: point the `OpenAI(base_url=..., api_key=...)` client at the new provider; update `list_models()`'s endpoint path and any provider-specific filtering (a chat-completions base URL and a model-*listing* URL are NOT always the same host/path — see Cloudflare gotcha below).
3. **Test locally BEFORE touching Oracle** (see Testing pattern below) — a bad swap breaks every future post. Don't trust docs for exact endpoint shapes — hit the real API with `curl` first; both swaps below found real discrepancies this way.
4. **Universal gotcha (bit us on every swap so far) — stale `DEFAULT_MODEL` / persisted model overriding the new provider.** `config.DEFAULT_MODEL` reads from `.env` first, config default second — if the **VM's `.env`** has an old `DEFAULT_MODEL=<old-provider-model-id>` line, it silently overrides your new code. Separately, `state.json` on the VM persists whatever model was last active via `/setmodel` — if that's an old-provider id, the bot will try to use it and fail on the very next `/generate`. **After deploying a provider swap, always**: (a) grep the VM's `.env` for a stale `DEFAULT_MODEL=` line and fix it, (b) run `config.set_model(config.DEFAULT_MODEL)` once on the VM to reset the persisted state.
5. **Provider-specific gotchas found so far:**
   - **Groq (2026-07-08)**: its edge (fronted by Cloudflare, unrelated to Cloudflare Workers AI below) 403s the default `Python-urllib/x.y` User-Agent on the plain stdlib GET used in `list_models()` — while `curl` with the same key returns 200. Fix: set an explicit `User-Agent` header on that one request. The OpenAI SDK client used for `chat()` is unaffected — it sets its own UA.
   - **Cloudflare Workers AI (2026-07-16)**: the model-*listing* endpoint is **NOT** under the OpenAI-compatible base URL (`.../ai/v1`) — it's a separate REST endpoint, `GET https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/models/search`. Each result has `task.name` (filter to `"Text Generation"` for chat-capable models) and `tags` (exclude `moderation`/`guardrails`-tagged classifiers like `llama-guard`). Also: that endpoint's `page`/`per_page` query params don't paginate as documented — `page=2` returns 0 results regardless of the `total_count` shown in `result_info` — confirmed live. A single unparameterized call returns the full accessible result set; don't build pagination-following logic around `total_count` without verifying it first.
6. **Docs**: update `.env.example`, `CAVEMAN.md`, `SETUP-ORACLE.md` — grep for the old provider name to catch every mention (`grep -rn "OldProviderName" agent/`).
7. **Secrets**: new key goes in `~/.zshrc` (source of truth) → Oracle's `agent/bot/.env` (via stdin, never echoed) → restart `dnhcare-bot`.

### Testing pattern (do this locally before any deploy)
```python
from agent.bot import llm, config
ids = llm.list_models()                      # live roster fetch works?
llm.chat(messages=[...])                     # plain chat works?
llm.chat(messages=[...], response_format={"type": "json_object"})  # JSON mode works?
# full pipeline:
from agent.bot import content, publisher
post = content.generate_post("[Category] a real topic")
html = content.render_html(post, publisher.recent_posts(2))
path = publisher.stage_draft(post.slug, html)
ok, out = publisher.run_gate(path)           # passes agent/check_post.py?
publisher.discard(post.slug)                 # clean up the test file
```

---

## 2. Google Business Profile (GBP) — local-post auto-publish + weekly digest

Used for: posting the approved blog to the clinic's Google listing on Approve;
weekly performance/keyword digest (`/report`).

| File | What lives there |
|---|---|
| `agent/bot/config.py` | `GBP_CLIENT_ID/SECRET/REFRESH_TOKEN/ACCOUNT_ID/LOCATION_ID`, optional `GBP_POST_IMAGE_URL`; `gbp_enabled()/set_gbp_enabled()`, `gbp_cta()/set_gbp_cta()`, `record_gbp_post()/get_gbp_posts()` — all persisted in `state.json` |
| `agent/bot/gbp.py` | OAuth refresh-token exchange (`_access_token()`); `_api()` (v4 REST helper); `create_local_post()`, `delete_local_post()` |
| `agent/bot/gbp_auth.py` | **One-time, manual-only** OAuth bootstrap: `login` mints the refresh token, `discover` lists account/location ids. Never run by the bot itself. |
| `agent/bot/insights.py` | Performance API (`businessprofileperformance.googleapis.com`) for metrics + search keywords; v4 API for review snapshot |
| `agent/bot/bot.py` | Approve-flow GBP post; `/gbp`, `/report` commands |
| `agent/bot/content.py` | `Post.gbp_summary` field + `gbp_blurb()` fallback chain |

### If Google rotates the OAuth client (new Client ID/Secret)
1. Re-run the manual bootstrap: `python3 -m agent.bot.gbp_auth login` (needs the NEW `GBP_CLIENT_ID`/`GBP_CLIENT_SECRET` in `.env` first) → produces a new `GBP_REFRESH_TOKEN`.
2. `GBP_ACCOUNT_ID`/`GBP_LOCATION_ID` don't change (they identify the business, not the OAuth client) — no need to re-run `discover` unless the listing itself changed.
3. Update all 3 changed values in Oracle's `.env`, restart the bot.

### Known API limitation (don't rebuild this — Google removed it)
`accounts.locations.localPosts.reportInsights` (per-post view counts) returns a
plain 404 as of 2026 — confirmed via a live test. `insights.post_insights()` is
a documented always-`None` stub for this reason; don't spend time "fixing" it
without first re-checking Google's docs for a replacement endpoint.

---

## 3. GitHub (publishing target)

Used for: committing + pushing approved posts to `main`, which triggers
`deploy-production.yml` → Oracle auto-pulls → live in ~15s.

| File | What lives there |
|---|---|
| `agent/bot/config.py` | `GITHUB_TOKEN` (env `DNH_GitHub_Token`, or `DNH_Github_Token`/`GITHUB_TOKEN`), `GITHUB_REPO`, `PUBLISH_BRANCH`, `REPO_DIR` |
| `agent/bot/publisher.py` | Every `git` call (`sync_main`, `publish`, `update_prompt`) builds the remote URL as `https://x-access-token:{config.GITHUB_TOKEN}@github.com/{config.GITHUB_REPO}.git` |

### If the GitHub PAT expires or is rotated
1. New fine-grained PAT needs **Contents: Read and write** on `shafeequealipt-dotcom/DNHCare`.
2. Update `DNH_GitHub_Token` in Oracle's `agent/bot/.env`, restart the bot.
3. Sanity check before trusting it: `curl -H "Authorization: token $NEW_TOKEN" https://api.github.com/repos/shafeequealipt-dotcom/DNHCare` → expect `200`.

---

## General rule for any API change
1. Read the relevant module(s) above before editing — don't guess at shapes; a v4-style deprecated endpoint (see the `reportInsights` note) can look correct and still 404.
2. Test live, locally, with real credentials, before touching Oracle. Never assume a client library or endpoint format from memory — verify with one real call.
3. Deploy to Oracle: pull code → update `.env` (via stdin, never echoed/logged) → restart `dnhcare-bot` → re-verify live (a plain API call through the actual code, not just "service is active").
4. Update this file and `CAVEMAN.md` with what changed and why, so the next swap starts from a working checklist instead of re-discovering the same gotchas.
