# Deploy the DNH Care blog agent on Oracle Cloud

A standing Python service: each day it drafts a blog post, sends it to your Telegram
with **Approve / Reject** buttons, and on approval commits to `main` → GitHub Pages
publishes it to dnhcare.co.in. Approve/Reject and topic management all happen in Telegram.

> The bot's working clone (`REPO_DIR`) must be on the **`main`** branch and must already
> contain the `blog/`, `agent/topics.md`, `agent/check_post.py`, and `agent/bot/` files.
> So merge `development → main` first (the blog + agent + bot all land on main together).

## 0. One-time: the secrets
The bot reads **Telegram** creds from system env vars `DNH_Telegram_Token` and
`DNH_Telegram_ID` (already set on the user's Windows machine). Content generation uses
**Groq** (`DNHCARE_Groq_Api`, or `GROQ_API_KEY`). You still need a **GitHub PAT** for publishing.
- **GitHub PAT** — github.com → Settings → Developer settings → *Fine-grained tokens* →
  repo access = `shafeequealipt-dotcom/DNHCare`, permission **Contents: Read and write**.
- **Groq key** — console.groq.com → API Keys → create key (`gsk_...`).
- On the Oracle VM, export the three system secrets (or add them to `.env`):
  ```bash
  export DNH_Telegram_Token=...      # bot token
  export DNH_Telegram_ID=...         # numeric chat id
  export DNHCARE_Groq_Api=gsk_...
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
nano agent/bot/.env     # GITHUB_TOKEN, REPO_DIR=/opt/dnhcare/DNHCare, POST_TIME (IST),
                        # DNHCARE_Groq_Api (if not exported), DEFAULT_MODEL
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
In Telegram: send `/start`, then `/generate`. You should get a draft with Approve/Reject.
Approve once and confirm the post appears at `https://dnhcare.co.in/blog/` within ~2 min.
`Ctrl-C` to stop.

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
- A draft arrives every day at `POST_TIME` — **✅ Approve** publishes; **✏️ Reject** then
  reply with your changes and it rewrites.
- `/generate` — draft right now.
- `/topics` — see the queue.
- `/addtopic [Skin] Why winter worsens eczema` — queue a topic.
- `/model` shows the current writing model; `/models` lists Groq's live model catalog, numbered;
  `/setmodel <number>` (or any Groq model id) switches. Changes take effect immediately and
  persist across restarts.
- When the queue runs low it auto-picks a timely, healthcare-relevant topic.

## Notes
- The agent only ever **commits on approval** — nothing is published without your tap.
- Every draft must pass `agent/check_post.py` (no medical overclaims, disclaimer + author +
  schema present, ≥380 words) before it's even shown to you.
- To change the daily time: edit `POST_TIME` in `.env`, then `sudo systemctl restart dnhcare-bot`.
- Cost: content is generated via Groq's free tier by default (llama-3.3-70b-versatile etc.),
  so ~free; switch to any other Groq model anytime with `/setmodel`.
