# Connecting Your Data

PersonalOS is only as useful as the data it can see.
This guide covers connecting the most common sources.

---

## Google Workspace (Gmail + Calendar + Drive)

The most important integration. Covers email, calendar, and files.

### Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (call it "PersonalOS")
3. Enable the Gmail API and Google Calendar API
4. Create OAuth 2.0 credentials (type: Desktop app)
5. Download the credentials JSON

Then in Hermes chat or Telegram:
```
/skill load google-workspace
```

Follow the OAuth prompts. After authorising, test:
```
Read my last 5 unread emails
What's on my calendar tomorrow?
```

### Add to `.env`

```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REFRESH_TOKEN=   # filled in automatically after OAuth
```

---

## GitHub

For the developer agent — read code, create branches, open PRs.

### Setup

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Name: "PersonalOS"
4. Scopes: `repo`, `read:user`
5. Copy the token

Add to `.env`:
```
GITHUB_TOKEN=ghp_your-token-here
GITHUB_DEFAULT_REPO=yourusername/your-repo
```

Test in chat:
```
@developer read my GitHub repo and summarise the architecture
```

---

## Telegram (already set up)

Telegram is set up during `./scripts/setup.sh`. No extra steps needed.

To verify it's working: send any message to your bot. It should reply.

---

## Business dashboards (no API)

For dashboards without a public API — POS systems, custom admin panels,
analytics tools — use browser automation.

In chat:
```
/skill load browser-automation
```

Then teach PersonalOS to read your dashboard:
```
Teach yourself a skill called "check-revenue": 
go to https://your-dashboard-url.com, log in with 
username [your@email.com] and password [yourpassword], 
navigate to the revenue section, and read today's 
total revenue. Return just the number.
```

PersonalOS stores this as a repeatable skill. You can then run:
```
Check my revenue
```

Or schedule it daily:
```
Create a cron job that runs "check-revenue" every day at 9am 
and sends the result to Telegram
```

**Security note:** Browser automation credentials are stored locally on your VPS,
not sent to any external service. Still, use a read-only account where possible.

---

## Notion

For knowledge base and project notes.

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Create a new integration
3. Copy the token
4. Share relevant Notion pages with your integration

Add to `.env`:
```
NOTION_TOKEN=secret_your-token-here
NOTION_DATABASE_ID=your-database-id
```

---

## Slack

For sending notifications to a Slack workspace.

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Create a new app
3. Add Bot Token Scopes: `chat:write`, `channels:read`
4. Install to workspace
5. Copy the Bot User OAuth Token

Add to `.env`:
```
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_DEFAULT_CHANNEL=#general
```

---

## Stripe (revenue monitoring)

For monitoring revenue from a digital product.

1. Go to [dashboard.stripe.com/apikeys](https://dashboard.stripe.com/apikeys)
2. Copy the **Restricted Key** (not the secret key)
3. Permissions needed: `read` on Charges, PaymentIntents, Subscriptions

Add to `.env`:
```
STRIPE_SECRET_KEY=rk_live_your-restricted-key
```

Test:
```
What was my Stripe revenue yesterday?
```

---

## Custom webhook

Send PersonalOS output to any URL — your own server, Zapier, Make, etc.

```
WEBHOOK_URL=https://your-server.com/personalos-webhook
```

Every task completion will POST a JSON payload to this URL with:
- `task_type`
- `agent`
- `output`
- `score`
- `timestamp`

---

## What about services without APIs?

For anything else — a POS system, a custom CRM, a SaaS dashboard — use
browser automation. PersonalOS can log in to any website, navigate to a
specific page, and extract data from it.

The pattern is always the same:
1. Load browser automation skill
2. Teach PersonalOS to navigate your specific dashboard
3. Save it as a named skill
4. Schedule it or run it on demand
