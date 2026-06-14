# PersonalOS — Quickstart Guide

This guide gets you from zero to a running personal AI OS in under 30 minutes.

---

## Before you start

You need:

1. **A VPS running Ubuntu 22.04 or 24.04**
   - Recommended: [Hetzner CX22](https://hetzner.com) (€4.51/mo) or [Hostinger KVM 2](https://hostinger.com) (~$7/mo)
   - Minimum: 2 vCPU, 4GB RAM, 40GB disk
   - Must have a public IP (any VPS does by default)

2. **An OpenRouter API key**
   - Go to [openrouter.ai/keys](https://openrouter.ai/keys)
   - Click "Create Key"
   - Add $20 credit (enough for ~2 months of light use)
   - Set a monthly spending limit of $30 to avoid surprises

3. **A Telegram bot**
   - Open Telegram and message [@BotFather](https://t.me/botfather)
   - Send `/newbot`
   - BotFather asks for a display name (e.g. `My PersonalOS`) then a username (must end in `bot`, e.g. `mypersonalos_bot`)
   - BotFather replies with a token like `7123456789:AAF_abc123...` — copy it
   - Message [@userinfobot](https://t.me/userinfobot) — it replies with your numeric user ID (e.g. `123456789`)
   - Enter both when the setup script prompts for them

---

## Step 1 — SSH into your VPS

```bash
ssh root@your-server-ip
```

If you've never used SSH before: your VPS provider shows this command in their dashboard after you create the server.

---

## Step 2 — Clone and run setup

```bash
git clone https://github.com/personalos/personalos
cd personalos
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The setup script will:
- Install Docker and dependencies
- Ask you 5 questions (name, timezone, OpenRouter key, Telegram token, persona)
- Start all services
- Run a health check

Total time: ~10 minutes.

---

## Step 3 — First conversation

Open Telegram on your phone. Find the bot you created (search by the name you gave it).

Send it:

```
Hello
```

It should reply within a few seconds. If it doesn't, run:

```bash
docker compose logs api --tail=50
```

---

## Step 4 — Tell it about yourself

This is the most important step. The more context you give, the more useful PersonalOS becomes immediately.

Copy and paste this into Telegram, filled in for you:

```
Remember these things about me permanently:

My name is [your name].
My timezone is [timezone, e.g. "Europe/London"].
My work: [describe what you do — one paragraph].
My businesses/projects: [list them, what they are].
My priorities in order: [e.g. revenue, product, family].
My communication preference: brief bullet points, no fluff.

Flag urgent things immediately. Batch non-urgent into the morning briefing.
Always show me before sending emails or taking any action.
```

---

## Step 5 — Connect your email

In Telegram or the Hermes desktop app, type:

```
/skill load google-workspace
```

Follow the Google OAuth prompts. After connecting, test it:

```
Read my last 5 unread emails and summarise them
```

---

## Step 6 — Your first morning briefing

At 8am tomorrow (weekdays), you'll receive your first automatic morning briefing on Telegram covering:
- Urgent emails
- Today's calendar
- Top 3 priorities
- One market insight

If you want to test it now:

```
Run the morning briefing now
```

---

## What to do next

Once the basics are working, explore these in order:

1. **Connect GitHub** (if you have code projects)
   ```
   /skill load github
   ```

2. **Add your business context** — tell it about your specific products, customers, and workflows

3. **Customise your schedule** — change briefing times or add new automated jobs

4. **Explore agents** — try routing tasks explicitly:
   ```
   @developer there's a bug in my login flow — it redirects to a 404 after OAuth
   @researcher give me a competitor analysis of SmallPDF and PDF24
   ```

---

## Common issues

**Bot doesn't respond**
```bash
docker compose logs api --tail=100
docker compose ps   # check all containers are "running"
```

**"Unauthorized" errors**
Your OpenRouter key may be invalid or out of credit. Check [openrouter.ai/activity](https://openrouter.ai/activity).

**Docker not found**
```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl start docker
```

**Database connection failed**
```bash
docker compose restart db
docker compose logs db --tail=50
```

---

## Getting help

- [GitHub Discussions](https://github.com/personalos/personalos/discussions) — questions and ideas
- [Discord](https://discord.gg/personalos) — live community chat
- [Issues](https://github.com/personalos/personalos/issues) — bug reports
