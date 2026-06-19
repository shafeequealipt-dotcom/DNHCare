# Website Deployment Reference

Complete runbook for deploying a static/PHP site on Oracle VM with Nginx, GitHub Actions CI/CD, staging/production environments, clean URLs, SSL, and Google SEO indexing.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [DNS Setup](#2-dns-setup)
3. [Oracle VM — Nginx Setup](#3-oracle-vm--nginx-setup)
4. [SSL with Let's Encrypt (Certbot)](#4-ssl-with-lets-encrypt-certbot)
5. [Clean URLs (No Extension)](#5-clean-urls-no-extension)
6. [GitHub Actions — Auto Deploy](#6-github-actions--auto-deploy)
7. [GitHub Secrets](#7-github-secrets)
8. [Branch Strategy](#8-branch-strategy)
9. [Bot / Agent Publishing](#9-bot--agent-publishing)
10. [Schema.org Structured Data](#10-schemaorg-structured-data)
11. [Sitemap](#11-sitemap)
12. [Google SEO Indexing](#12-google-seo-indexing)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Architecture Overview

```
Developer / Bot
      │
      ▼
GitHub Repository
  ├── development branch ──► GitHub Actions ──► staging.yourdomain.com  (Oracle VM)
  └── main branch        ──► GitHub Actions ──► yourdomain.com          (Oracle VM)

Oracle VM (Ubuntu 22.04)
  ├── Nginx (web server)
  ├── Certbot (SSL)
  ├── ~/project           (main branch checkout)
  └── ~/project-staging   (development branch checkout)
```

**Flow:**
- Work on `development` → push → staging auto-deploys in ~15 sec
- Review on `staging.yourdomain.com` → merge to `main` → production auto-deploys in ~15 sec

---

## 2. DNS Setup

Go to your domain registrar (Namecheap, GoDaddy, Cloudflare, etc.).

### Records to add

| Type | Name      | Data (Value)     | TTL  |
|------|-----------|------------------|------|
| A    | `@`       | `YOUR_SERVER_IP` | 300  |
| A    | `www`     | `YOUR_SERVER_IP` | 300  |
| A    | `staging` | `YOUR_SERVER_IP` | 300  |

- TTL `300` = 5 minutes (fast propagation during cutover). Raise to `3600` after confirming.
- `@` = root domain (`yourdomain.com`)

### If migrating from GitHub Pages

GitHub Pages uses 4 A records that must be **deleted first**:

```
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```

Also delete any CNAME pointing to `username.github.io`.

### Check propagation

```bash
nslookup yourdomain.com 8.8.8.8       # Google DNS
nslookup yourdomain.com 1.1.1.1       # Cloudflare DNS
```

Wait until only your server IP appears (no old IPs mixed in).

---

## 3. Oracle VM — Nginx Setup

### SSH into the VM

```bash
ssh -i ~/.ssh/your-key.key ubuntu@YOUR_SERVER_IP
```

### Install Nginx (if not already installed)

```bash
sudo apt update && sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### Fix home directory permissions for Nginx

Nginx runs as `www-data`. If your site files are in `/home/ubuntu/`, grant traversal:

```bash
sudo chmod o+x /home/ubuntu
```

### Create Nginx config for production

```bash
sudo nano /etc/nginx/sites-available/yourdomain.com
```

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;
    root /home/ubuntu/project;

    server_tokens off;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Redirect /path/index → /path/ (canonical directory URLs)
    location ~ ^(.*)/index$ {
        return 301 $1/;
    }

    # Redirect .html URLs to clean URLs
    location ~ ^(.+)\.html$ {
        return 301 $1;
    }

    # Serve clean URLs: /about → about.html
    location / {
        try_files $uri $uri/index.html $uri.html =404;
    }

    # Cache static assets
    location ~* \.(css|js|svg|png|ico|woff2|jpg|webp)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### Create Nginx config for staging

```bash
sudo nano /etc/nginx/sites-available/staging.yourdomain.com
```

Same as above but:
- `server_name staging.yourdomain.com;`
- `root /home/ubuntu/project-staging;`

### Enable both configs

```bash
sudo ln -s /etc/nginx/sites-available/yourdomain.com /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/staging.yourdomain.com /etc/nginx/sites-enabled/
sudo nginx -t          # test — must say "ok"
sudo systemctl reload nginx
```

### Clone the staging repo

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git ~/project-staging
git -C ~/project-staging checkout development
```

---

## 4. SSL with Let's Encrypt (Certbot)

### Install Certbot (if not already installed)

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Issue certificates

Run **after DNS has fully propagated** (only your server IP in nslookup).

```bash
# Production
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com \
  --non-interactive --agree-tos -m you@email.com

# Staging
sudo certbot --nginx -d staging.yourdomain.com \
  --non-interactive --agree-tos -m you@email.com
```

Certbot automatically:
- Issues the certificate
- Edits your Nginx config to add SSL listeners
- Sets up auto-renewal (cron/systemd timer)

### Verify auto-renewal

```bash
sudo certbot renew --dry-run
```

Certificates expire every 90 days and renew automatically.

---

## 5. Clean URLs (No Extension)

The Nginx config above already handles clean URLs. Key rules explained:

```nginx
# /page/index  →  /page/
location ~ ^(.*)/index$ {
    return 301 $1/;
}

# /about.html  →  /about
location ~ ^(.+)\.html$ {
    return 301 $1;
}

# /about  →  serves about.html from disk (no redirect, no extension in URL)
location / {
    try_files $uri $uri/index.html $uri.html =404;
}
```

**What this means for your HTML files:**
- Files on disk remain `about.html`, `blog/my-post.html`
- URLs in browser become `/about`, `/blog/my-post`
- Old `.html` links from Google still work (301 redirect)

**Update your HTML files accordingly:**
- `<link rel="canonical" href="https://yourdomain.com/about" />` (no `.html`)
- `<meta property="og:url" content="https://yourdomain.com/about" />`
- `href="about"` not `href="about.html"` in internal links
- Schema `@id` and `url` fields: no `.html`

---

## 6. GitHub Actions — Auto Deploy

### deploy-production.yml

```yaml
# .github/workflows/deploy-production.yml
name: Deploy Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.ORACLE_SSH_KEY }}" > ~/.ssh/deploy.key
          chmod 600 ~/.ssh/deploy.key
          ssh-keyscan -H ${{ secrets.ORACLE_HOST }} >> ~/.ssh/known_hosts

      - name: Pull main → production
        run: |
          ssh -i ~/.ssh/deploy.key ubuntu@${{ secrets.ORACLE_HOST }} \
            'git -C ~/project fetch origin && git -C ~/project reset --hard origin/main'
```

### deploy-staging.yml

```yaml
# .github/workflows/deploy-staging.yml
name: Deploy Staging

on:
  push:
    branches: [development]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.ORACLE_SSH_KEY }}" > ~/.ssh/deploy.key
          chmod 600 ~/.ssh/deploy.key
          ssh-keyscan -H ${{ secrets.ORACLE_HOST }} >> ~/.ssh/known_hosts

      - name: Pull development → staging
        run: |
          ssh -i ~/.ssh/deploy.key ubuntu@${{ secrets.ORACLE_HOST }} \
            'git -C ~/project-staging fetch origin && git -C ~/project-staging reset --hard origin/development'
```

---

## 7. GitHub Secrets

Set these in **GitHub → Repo → Settings → Secrets and variables → Actions**.

| Secret Name     | Value                        | How to set                                    |
|-----------------|------------------------------|-----------------------------------------------|
| `ORACLE_SSH_KEY` | Contents of your `.key` file | `gh secret set ORACLE_SSH_KEY --body "$(cat ~/.ssh/your-key.key)"` |
| `ORACLE_HOST`   | `YOUR_SERVER_IP`             | `gh secret set ORACLE_HOST --body "140.x.x.x"` |

Or via CLI (PowerShell):

```powershell
$key = Get-Content C:\Users\You\.ssh\your-key.key -Raw
gh secret set ORACLE_SSH_KEY --body $key --repo USERNAME/REPO
gh secret set ORACLE_HOST --body "140.x.x.x" --repo USERNAME/REPO
```

Verify:

```bash
gh secret list --repo USERNAME/REPO
```

---

## 8. Branch Strategy

```
main          = LIVE production. Never push directly. Only merge from development.
development   = Active work. Push freely. Auto-deploys to staging.
```

### Day-to-day workflow

```bash
# Work on development
git checkout development
# ... make changes ...
git add .
git commit -m "your message"
git push origin development
# → staging.yourdomain.com updates in ~15 seconds

# When ready to go live: open PR and merge
gh pr create --base main --head development --title "your title"
gh pr merge <PR_NUMBER> --merge
# → yourdomain.com updates in ~15 seconds
```

### Merge conflicts

If the bot or someone else pushed to `main` while you were on `development`:

```bash
git fetch origin main
git merge origin/main
# resolve any conflicts
git push origin development
gh pr merge <PR_NUMBER> --merge
```

---

## 9. Bot / Agent Publishing

For a Telegram-controlled daily publishing bot (Python + systemd on Oracle):

### systemd service

```ini
# /etc/systemd/system/mybot.service
[Unit]
Description=My site blog agent
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/project
EnvironmentFile=/home/ubuntu/project/agent/bot/.env
ExecStart=/home/ubuntu/venv/bin/python -m agent.bot.bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable mybot
sudo systemctl start mybot
```

### Manage the service

```bash
sudo systemctl status mybot          # check running
sudo systemctl restart mybot         # restart (e.g. after code change)
sudo systemctl stop mybot            # stop
journalctl -u mybot -f               # live logs
```

### Deploy code updates to the bot

```bash
ssh -i ~/.ssh/your-key.key ubuntu@YOUR_SERVER_IP \
  'git -C ~/project pull && sudo systemctl restart mybot'
```

### .env file for the bot (chmod 600)

```env
REPO_DIR=/home/ubuntu/project
PUBLISH_BRANCH=main
GITHUB_TOKEN=github_pat_xxxx
POST_TIME=06:00
DEFAULT_MODEL=openai/gpt-oss-120b:free
```

**CRITICAL:** Only run ONE instance of the bot (same Telegram token → 409 Conflict error).

---

## 10. Schema.org Structured Data

Add JSON-LD blocks in `<head>`. Each block is a separate `<script type="application/ld+json">`.

### Local Business / Medical Clinic

```json
{
  "@context": "https://schema.org",
  "@type": "MedicalClinic",
  "@id": "https://yourdomain.com/#clinic",
  "name": "Your Clinic Name",
  "url": "https://yourdomain.com/",
  "telephone": "+91-XXXXXXXXXX",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "123 Main Street",
    "addressLocality": "City",
    "addressRegion": "State",
    "postalCode": "000000",
    "addressCountry": "IN"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.9",
    "reviewCount": "150"
  },
  "openingHoursSpecification": [
    {
      "@type": "OpeningHoursSpecification",
      "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],
      "opens": "10:00",
      "closes": "13:00"
    }
  ]
}
```

### WebSite

```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "@id": "https://yourdomain.com/#website",
  "url": "https://yourdomain.com/",
  "name": "Your Site Name",
  "publisher": { "@id": "https://yourdomain.com/#clinic" },
  "hasPart": { "@id": "https://yourdomain.com/blog/#blog" }
}
```

### BlogPosting (individual post)

```json
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "@id": "https://yourdomain.com/blog/my-post#post",
  "headline": "Post Title",
  "url": "https://yourdomain.com/blog/my-post",
  "datePublished": "2026-06-19",
  "dateModified": "2026-06-19",
  "author": {
    "@type": "Person",
    "@id": "https://yourdomain.com/#author",
    "name": "Author Name"
  },
  "publisher": { "@id": "https://yourdomain.com/#clinic" },
  "isPartOf": { "@id": "https://yourdomain.com/#website" }
}
```

### FAQPage

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is your question?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Your answer here."
      }
    }
  ]
}
```

### BreadcrumbList

```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://yourdomain.com/" },
    { "@type": "ListItem", "position": 2, "name": "Blog", "item": "https://yourdomain.com/blog/" },
    { "@type": "ListItem", "position": 3, "name": "Post Title", "item": "https://yourdomain.com/blog/my-post" }
  ]
}
```

### Test your schema

- [Google Rich Results Test](https://search.google.com/test/rich-results)
- [Schema Markup Validator](https://validator.schema.org/)

**Cross-page entity linking:** define `@id` once (e.g. `#clinic`, `#doctor`, `#website`) and reference it across pages. Google builds a knowledge graph from these links.

---

## 11. Sitemap

### sitemap.xml format

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://yourdomain.com/</loc><priority>1.0</priority></url>
  <url><loc>https://yourdomain.com/about</loc><priority>0.8</priority></url>
  <url><loc>https://yourdomain.com/blog/</loc><priority>0.7</priority></url>
  <url><loc>https://yourdomain.com/blog/my-post</loc><priority>0.6</priority></url>
</urlset>
```

**Rules:**
- Use clean URLs (no `.html`)
- `priority` 1.0 = homepage, 0.8 = key pages, 0.7 = section index, 0.6 = blog posts
- Place at `https://yourdomain.com/sitemap.xml`
- Reference in `robots.txt`: `Sitemap: https://yourdomain.com/sitemap.xml`

### robots.txt

```
User-agent: *
Allow: /
Sitemap: https://yourdomain.com/sitemap.xml
```

### Submit sitemap in Search Console

Google Search Console → Sitemaps → enter `sitemap.xml` → Submit.

---

## 12. Google SEO Indexing

### First-time setup

1. Go to [Google Search Console](https://search.google.com/search-console)
2. Add property → Domain (covers all subdomains + http/https)
3. Verify ownership via DNS TXT record (add in your registrar)
4. Submit sitemap (see above)

### Request indexing for specific pages

Search Console → URL Inspection → enter URL → **Request Indexing**

- Limit: ~10 URLs per day per property
- Google crawls within 24–72 hours after requesting
- Schema/rich results appear in SERPs within 1–2 weeks after crawl

### After major changes (URL migration, new schema, etc.)

Priority pages to reindex manually:
1. Homepage (`/`)
2. Key landing pages (`/about`, `/services`, `/contact`)
3. Blog index (`/blog/`)
4. Most important blog posts

### URL migration checklist (e.g. `.html` → clean URLs)

- [ ] 301 redirects configured in Nginx (old URLs → new URLs)
- [ ] Canonical tags updated to new URLs
- [ ] Sitemap updated to new URLs
- [ ] Internal links updated to new URLs
- [ ] Schema `url` and `@id` fields updated
- [ ] Request reindex for top 6–10 pages in Search Console

---

## 13. Troubleshooting

### Site returns 404 after DNS cutover

```bash
# Check Nginx can read files
sudo -u www-data ls /home/ubuntu/project/index.html

# If Permission denied: fix home dir
sudo chmod o+x /home/ubuntu

# Test Nginx config
sudo nginx -t
sudo systemctl reload nginx
```

### DNS still showing old IPs

```bash
nslookup yourdomain.com 8.8.8.8
```

If old IPs still appear → check registrar for leftover A records (common with GitHub Pages migration). Delete all old A records.

### Certbot fails with "Could not bind to IPv4/IPv6"

Nginx must be running and the domain must resolve to THIS server before Certbot can issue a cert.

### GitHub Actions deploy fails

```bash
gh run list --repo USERNAME/REPO --limit 5
gh run view <RUN_ID> --repo USERNAME/REPO --log
```

Common causes:
- `ORACLE_SSH_KEY` secret has wrong format (must include `-----BEGIN...-----END-----` headers)
- Server IP changed → update `ORACLE_HOST` secret
- SSH key not authorized on the server (`~/.ssh/authorized_keys`)

### Redirect loop

Check your Nginx config for conflicting `if` blocks or double-redirect rules. Use:

```bash
curl -sIL https://yourdomain.com/about | grep -E "HTTP|Location"
```

### Bot 409 Conflict (Telegram)

Two instances running with the same token. Stop all instances, then start only one:

```bash
sudo systemctl stop mybot
# kill any stray processes
pkill -f "python -m agent.bot"
sudo systemctl start mybot
```

---

## Quick Reference Commands

```bash
# SSH into server
ssh -i ~/.ssh/your-key.key ubuntu@YOUR_SERVER_IP

# Reload Nginx after config change
sudo nginx -t && sudo systemctl reload nginx

# Check Nginx error log
sudo tail -f /var/log/nginx/error.log

# Bot service management
sudo systemctl status|restart|stop mybot
journalctl -u mybot -f

# Deploy code to server
ssh -i ~/.ssh/your-key.key ubuntu@IP 'git -C ~/project pull && sudo systemctl restart mybot'

# Check DNS propagation
nslookup yourdomain.com 8.8.8.8

# Test redirects
curl -sIL https://yourdomain.com/old-page.html | grep -E "HTTP|Location"

# Verify SSL cert
echo | openssl s_client -connect yourdomain.com:443 2>/dev/null | grep "subject\|issuer\|notAfter"

# List GitHub secrets
gh secret list --repo USERNAME/REPO

# Check GitHub Actions runs
gh run list --repo USERNAME/REPO --limit 5
```
