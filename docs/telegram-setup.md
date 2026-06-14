# Setting Up Telegram for PersonalOS

Telegram is how PersonalOS talks to you — morning briefings, task results, alerts, and your commands all flow through it. This guide walks you through the full setup from scratch.

---

## Why Telegram?

- Works on your phone, desktop, and browser
- Bot API is free and has no rate limits for personal use
- Instant push notifications — no polling
- You own the channel; no vendor lock-in

---

## Step 1 — Create your bot

1. Open Telegram and search for **[@BotFather](https://t.me/botfather)** (the official bot, blue checkmark)
2. Tap **Start** or send `/start`
3. Send `/newbot`
4. BotFather asks for a **display name** — this is what appears in chats (e.g. `My PersonalOS`)
5. BotFather asks for a **username** — must be unique and end in `bot` (e.g. `mypersonalos_bot`)
6. BotFather replies with your token:

```
Done! Congratulations on your new bot. You will find it at t.me/mypersonalos_bot.
Use this token to access the HTTP API:

7123456789:AAF_abc123XYZexampleTokenHere

Keep your token secure and store it safely.
```

**Copy this token.** You'll need it during setup.

> Keep your token private — anyone with it can send messages as your bot.

---

## Step 2 — Get your Telegram user ID

PersonalOS uses your user ID to make sure it only responds to you (not anyone who finds your bot).

1. Search for **[@userinfobot](https://t.me/userinfobot)** in Telegram
2. Tap **Start**
3. It replies immediately with your info:

```
Id: 123456789
First: Krishna
Last: Teja
Username: @krishnateja
Language: en
```

**Copy the number next to `Id:`** — that's your user ID.

---

## Step 3 — Lock down your bot (recommended)

By default your bot is publicly findable. Two settings to change in BotFather:

**Disable group chats** (your bot is personal, not for groups):
1. Send `/mybots` to BotFather
2. Select your bot
3. Tap **Bot Settings → Allow Groups? → Turn off**

**Disable joining via link**:
1. In the same Bot Settings menu
2. Tap **Group Privacy → Turn on** (this means the bot can only see messages directed at it)

---

## Step 4 — Enter your credentials during setup

When you run `./scripts/setup.sh`, it will ask:

```
Telegram bot token: 7123456789:AAF_abc123...
Your Telegram user ID: 123456789
```

Paste them in. The script writes them to your `.env` file automatically.

If you've already run setup and need to update them, open `.env` and edit:

```env
TELEGRAM_BOT_TOKEN=7123456789:AAF_abc123...
TELEGRAM_USER_ID=123456789
```

Then restart:

```bash
docker compose restart api
```

---

## Step 5 — Test the connection

Find your bot in Telegram (search by its username) and send:

```
Hello
```

It should reply within a few seconds. If it doesn't:

```bash
docker compose logs api --tail=50
```

Look for lines mentioning `telegram` or `webhook` — the error will be there.

---

## Talking to PersonalOS

Once connected, everything is plain English:

```
What should I focus on today?
Run the morning briefing now
@developer fix the login bug on the checkout page
Read my last 5 emails and flag anything urgent
```

You can also use slash commands for skills:

```
/skill load google-workspace
/skill load github
```

---

## Common issues

**Bot doesn't respond at all**

Check the bot token is correct in `.env` and that the API container is running:

```bash
docker compose ps
docker compose logs api --tail=50
```

**"Unauthorized" in the logs**

Your bot token is wrong or was regenerated. Get a new one from BotFather:
1. Send `/mybots` → select your bot → **API Token → Revoke current token**
2. Update `TELEGRAM_BOT_TOKEN` in `.env`
3. Run `docker compose restart api`

**Bot responds to anyone, not just you**

Your `TELEGRAM_USER_ID` in `.env` is wrong or missing. Get it from [@userinfobot](https://t.me/userinfobot) and update `.env`, then restart.

**Messages deliver but very slowly**

PersonalOS is polling Telegram by default. If you're on a VPS with a public IP, you can switch to webhooks for instant delivery — see the [connecting data guide](connecting-data.md).

---

## Multiple devices

Telegram syncs across all your devices automatically. Your bot messages appear on your phone, desktop app, and web — no extra setup needed.

---

## Getting help

- [Discord](https://discord.gg/personalos) — live community chat
- [GitHub Discussions](https://github.com/krishnatejaganesh/PersonalOS/discussions) — questions and ideas
