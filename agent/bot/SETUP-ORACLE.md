# Deploy the DNH Care blog agent on Oracle Cloud

A standing Python service: each day (at a randomized time inside your configured
window) it drafts a blog post, runs it through the safety gate, and — if it
passes — publishes it automatically (commits to `main` → GitHub Actions deploys
to dnhcare.co.in, and shares to Google Business Profile). No manual approval
step. Telegram is used for status/control (`/generate`, `/topics`, `/settime`,
etc.), not for gating what goes live.

> The bot's working clone (`REPO_DIR`) must be on the **`main`** branch and must already
> contain the `blog/`, `agent/topics.md`, `agent/check_post.py`, and `agent/bot/` files.
> So merge `development → main` first (the blog + agent + bot all land on main together).

## 0. One-time: the secrets
The bot reads **Telegram** creds from system env vars `DNH_Telegram_Token` and
`DNH_Telegram_ID` (already set on the user's Windows machine). Content generation uses
**Cloudflare Workers AI** (`DNH_CloudFlare_API` + `DNH_CloudFlare_AccountID`).
You still need a **GitHub PAT** for publishing.
- **GitHub PAT** — github.com → Settings → Developer settings → *Fine-grained tokens* →
  repo access = `shafeequealipt-dotcom/DNHCare`, permission **Contents: Read and write**.
- **Cloudflare API token** — dash.cloudflare.com → My Profile → API Tokens → create
  token with **Workers AI** read/edit permission. Also grab your **Account ID** from
  the dashboard sidebar.
- On the Oracle VM, export the four system secrets (or add them to `.env`):
  ```bash
  export DNH_Telegram_Token=...      # bot token
  export DNH_Telegram_ID=...         # numeric chat id
  export DNH_GitHub_Token=github_pat_...
  export DNH_CloudFlare_API=...
  export DNH_CloudFlare_AccountID=...
  ```

## 1. Provision the VM
Oracle Cloud → Compute → Instance. The **Always Free** `VM.Standard.A1.Flex`
(Ubuntu 22.04) is plenty. Open no inbound ports — the bot uses outbound long-polling only.
SSH in.

## 2. Install runtime + clone (on the VM)
```bash
sudo apt update && sudo apt install -y python3 python3-venv git
sudo useradd -m -d /opt/dnhcare dnhcare
sudo mkdir -p /opt/dnhcare && sudo chown -R dnhcare:dnhcare /opt/dnhcare
sudo -iu dnhcare

git clone https://github.com/shafeequealipt-dotcom/DNHCare.git /opt/dnhcare/DNHCare
cd /opt/dnhcare/DNHCare && git checkout main
python3 -m venv /opt/dnhcare/venv
/opt/dnhcare/venv/bin/pip install -r agent/bot/requirements.txt
```

## 3. Configure
```bash
cp agent/bot/.env.example agent/bot/.env
nano agent/bot/.env     # GITHUB_TOKEN, REPO_DIR=/opt/dnhcare/DNHCare,
                        # POST_WINDOW_START/END (IST),
                        # DNH_CloudFlare_API/AccountID (if not exported), DEFAULT_MODEL
```
Let git commit as the bot (used for the publish commits):
```bash
git config user.name  "DNH Care Bot"
git config user.email "bot@dnhcare.co.in"
```

## 4. Smoke test (still as dnhcare)
```bash
cd /opt/dnhcare/DNHCare
/opt/dnhcare/venv/bin/python -m agent.bot.bot
```
In Telegram: send `/start`, then `/generate`. It writes a draft, runs the safety gate, and
if it passes, publishes automatically — confirm the post appears at
`https://dnhcare.co.in/blog/` within ~2 min. `Ctrl-C` to stop.

## 5. Run it 24/7 with systemd
```bash
exit   # back to your sudo user
sudo cp /opt/dnhcare/DNHCare/agent/bot/deploy/dnhcare-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dnhcare-bot
sudo systemctl status dnhcare-bot          # should be "active (running)"
journalctl -u dnhcare-bot -f               # live logs
```

## Daily use (all in Telegram)
- Every day, at a fresh random minute inside your `/settime` window, a post is drafted
  and — if it passes the safety gate — published automatically (blog + Google Business
  Profile). You get a Telegram message once it's live; no approval needed.
- `/generate` — draft and auto-publish right now, outside the daily schedule.
- `/topics` — see the queue.
- `/addtopic [Skin] Why winter worsens eczema` — queue a topic.
- `/model` shows the current writing model; `/models` lists Cloudflare's live model catalog,
  numbered; `/setmodel <number>` (or any Cloudflare model id) switches. Changes take effect
  immediately and persist across restarts.
- When the queue runs low it auto-picks a timely, healthcare-relevant topic.

## Notes
- **No manual approval step.** The deterministic safety gate (`agent/check_post.py` —
  no medical overclaims, no remedy names, disclaimer + author + schema present, ≥380
  words) is the only check before a draft goes live. A gate failure blocks publishing;
  a pass publishes immediately.
- To change the daily window: `/settime 06:00-09:00` in Telegram (or edit
  `POST_WINDOW_START`/`POST_WINDOW_END` in `.env`, then `sudo systemctl restart dnhcare-bot`).
- Cost: content is generated via Cloudflare Workers AI's free tier by default
  (llama-3.3-70b-instruct-fp8-fast etc.), so ~free; switch to any other Cloudflare
  model anytime with `/setmodel`.
