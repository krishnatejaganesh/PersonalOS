# 🧠 PersonalOS

**Your model-agnostic personal AI operating system. Deploy once, swap models forever.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/krishnatejaganesh/PersonalOS?style=social)](https://github.com/krishnatejaganesh/PersonalOS)
[![Discord](https://img.shields.io/badge/Discord-Community-5865F2)](https://discord.gg/personalos)

> Claude 5 drops? Change one line. GPT-5 is better at code? Swap the agent. Your memory, workflows, and business agents stay intact forever.

---

## What is PersonalOS?

PersonalOS is an open-source personal AI operating system you deploy on your own VPS. It gives you:

- **A persistent second brain** — memory that survives model changes, API updates, and platform shutdowns
- **A team of specialised agents** — Chief of Staff, Developer, SEO, Researcher, Support, and more
- **A self-improving loop** — agents log what works and reuse it; the system gets smarter every day
- **Model agnosticism** — use Claude, GPT, Gemini, Mistral, or any OpenRouter model; swap anytime
- **You own everything** — your data lives on your server, not a vendor's cloud

---

## Quick Start (30 minutes)

### What you need
- **A machine to run it on** — your Mac/Linux laptop, or a VPS ([Hetzner €6/mo](https://hetzner.com), [Hostinger $7/mo](https://hostinger.com))
- **Docker Desktop** (Mac/Windows) or Docker Engine (Linux) — [get it here](https://www.docker.com/products/docker-desktop/)
- **An [OpenRouter](https://openrouter.ai) API key** — ~$20 starting credit, covers weeks of use
- **A Telegram bot** — takes 2 minutes, instructions below

### Step 1 — Create your Telegram bot

Telegram is how PersonalOS talks to you. You need a bot token and your personal user ID.

**Get your bot token:**
1. Open Telegram and search for **@BotFather**
2. Send it `/newbot`
3. Choose a name (e.g. `My PersonalOS`) and a username (e.g. `mypersonalos_bot`)
4. BotFather replies with a token that looks like: `7123456789:AAFx...` — copy it

**Get your Telegram user ID:**
1. Search for **@userinfobot** in Telegram
2. Start it — it instantly replies with your numeric user ID (e.g. `123456789`)
3. Copy that number

You'll paste both into the setup wizard in a moment.

### Step 2 — Get an OpenRouter key

1. Go to [openrouter.ai/keys](https://openrouter.ai/keys) and sign up
2. Add ~$20 credit (covers weeks of daily use)
3. Create an API key — it starts with `sk-or-`

### Step 3 — Run setup

```bash
git clone https://github.com/krishnatejaganesh/PersonalOS
cd personalos
./scripts/setup.sh
```

The wizard asks for your name, timezone, OpenRouter key, Telegram token, and user ID — then starts everything automatically.

### Step 4 — Send your bot a message

Open Telegram, find your bot, and send:

```
Hello, are you there?
```

It should reply within a few seconds. You're running.

---

## Architecture

```
You (Telegram / Desktop / Web)
        │
        ▼
┌─────────────────────────────────────────┐
│           PersonalOS Core               │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │   Router    │  │  Self-Improve    │  │
│  │  (decides   │  │  Loop (learns    │  │
│  │  who acts)  │  │  from outcomes)  │  │
│  └──────┬──────┘  └──────────────────┘  │
│         │                               │
│  ┌──────▼──────────────────────────┐    │
│  │          Agent Pool             │    │
│  │  Chief-of-Staff │ Developer     │    │
│  │  SEO Agent      │ Researcher    │    │
│  │  Support Agent  │ [Your Custom] │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │    Memory Layer (PostgreSQL)     │   │
│  │  Episodic │ Semantic │ Workflow  │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
        │
        ▼
   Model Layer (OpenRouter)
   Claude │ GPT │ Gemini │ Mistral │ Any
```

**The key design principle:** The model is a plugin. Your identity, memory, and agents are the product.

---

## Core Features

### 🔁 Self-Improving Loop

Every completed task is evaluated and stored. Future tasks check the library first.

```sql
-- What gets stored after every task
INSERT INTO workflow_outcomes (task_type, steps, outcome, score)
VALUES ('seo_article', '[...]', 'published, 2k views in 24h', 0.92);

-- What gets retrieved before every task
SELECT steps FROM workflow_outcomes
WHERE task_type = $1 AND score > 0.75
ORDER BY score DESC LIMIT 1;
```

The system doesn't get smarter by changing the model — it gets smarter by building a library of *what actually worked for you*.

### 🤖 Agent Roster

| Agent | What it does | Default model |
|-------|-------------|---------------|
| Chief of Staff | Morning briefings, email triage, calendar, priorities | Claude Sonnet |
| Developer | Code, PRs, debugging, architecture review | Claude Sonnet / Opus for hard problems |
| SEO Agent | Content strategy, keyword research, article drafts | Gemini Flash (cost efficient) |
| Researcher | Deep research, competitor analysis, reports | Perplexity / Claude Opus |
| Support | Customer email drafts, ticket routing | Claude Haiku (fast + cheap) |

### 🔄 Model Watching

```bash
# Runs every Sunday, sends you a Telegram report
personalos model-watch

# Output:
# 📊 Weekly Model Report
# Best for coding this week: claude-opus-4-6 (benchmark score: 94)
# Best for writing: claude-sonnet-4-6 (cost-efficiency winner)
# New model alert: google/gemini-2.5-pro — consider testing for research tasks
# Your current stack looks optimal. No changes recommended.
```

### 🧩 Personas

Personas are pre-built configurations for common life situations. Clone the one closest to you, then customise:

```bash
personalos persona use solo-founder   # bootstrapped founder running multiple businesses
personalos persona use freelancer     # client work, project tracking, invoicing
personalos persona use student        # studying, research, deadlines
personalos persona use ecommerce      # store management, ads, inventory
```

---

## Daily Automation

Out of the box, PersonalOS runs these automatically:

| Time | Job | What happens |
|------|-----|--------------|
| 8:00am | Morning Briefing | Top 3 priorities + urgent emails + calendar + one market insight → Telegram |
| 12:00pm | Midday Check | Anything urgent since morning → Telegram only if needed |
| 7:00pm | Evening Wrap | Unanswered urgent items + day summary → Telegram |
| Sunday 9am | Weekly Review | Model benchmarks + workflow performance report |

You can add, remove, or modify all of these with natural language in Hermes chat.

---

## Usage Examples

Once running, you talk to PersonalOS naturally via Telegram or the desktop app:

```
"What should I focus on today?"
→ Reads your calendar, flags urgent emails, checks open tasks, gives you top 3.

"There's a bug where the PDF export crashes on files over 50MB. Fix it."
→ Developer agent reads your codebase, finds the bug, opens a PR, messages you.

"Write an SEO article about [topic] for my site."
→ SEO agent researches, outlines, drafts, formats for WordPress, sends for review.

"Book me a flight to Berlin next Thursday."
→ Checks your calendar, searches options, proposes 3 flights, books on confirmation.

"Handle the angry email from John about his refund."
→ Reads the context, drafts a resolution email, asks you to approve before sending.
```

---

## Connecting Your Data

PersonalOS is only as useful as the data it can see. Connect your sources:

```bash
# In Hermes chat or terminal
/skill load google-workspace     # Gmail + Calendar + Drive
/skill load github               # Code repositories
/skill load telegram             # Already done in setup
/skill load browser-automation   # Any website without an API
```

For businesses without APIs (POS systems, custom dashboards), the browser automation skill reads any web interface.

---

## Adding Your Own Agents

```bash
cp -r agents/developer agents/my-custom-agent
nano agents/my-custom-agent/soul.md   # edit the identity
nano agents/my-custom-agent/config.yaml
```

See [docs/creating-agents.md](docs/creating-agents.md) for the full guide.

---

## Cost

| Usage level | Monthly cost | What you get |
|-------------|-------------|--------------|
| Light (personal) | $30–60 | VPS + API for daily briefings + on-demand tasks |
| Medium (+ business) | $60–150 | Multiple agents running scheduled tasks |
| Heavy (full ops) | $150–400 | All agents active, high task volume |

The biggest variable is API usage. Routing lightweight tasks to Gemini Flash and heavy reasoning to Claude Sonnet cuts costs 5–10x versus using one model for everything. PersonalOS does this automatically.

---

## Project Structure

```
personalos/
├── README.md
├── LICENSE                    # MIT
├── .env.example               # all config documented
├── docker-compose.yml         # one-command deployment
├── scripts/
│   ├── setup.sh               # interactive setup wizard
│   └── update.sh              # pull latest + restart
├── core/
│   ├── router.py              # task → agent routing
│   ├── self_improve.py        # outcome logging + retrieval
│   └── model_watcher.py       # weekly benchmark + alerts
├── agents/
│   ├── chief-of-staff/
│   │   ├── soul.md            # agent identity
│   │   ├── config.yaml        # tools, model, cron schedule
│   │   └── prompts/           # task-specific prompt templates
│   ├── developer/
│   ├── seo/
│   ├── researcher/
│   └── support/
├── memory/
│   └── schemas/
│       └── init.sql           # full Postgres schema
├── integrations/
│   ├── telegram.py
│   ├── google_workspace.py
│   └── github.py
├── personas/
│   ├── solo-founder/
│   ├── freelancer/
│   ├── student/
│   └── ecommerce/
└── docs/
    ├── quickstart.md
    ├── creating-agents.md
    ├── connecting-data.md
    ├── self-improve-loop.md
    └── model-guide.md
```

---

## Contributing

PersonalOS grows through community contributions. The most valuable contributions are **personas** and **agent profiles** — pre-built configurations for specific use cases.

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add:
- A new persona (your life situation as a starter config)
- A new agent (a specialised AI worker)
- A new integration (connecting a service)
- A skill template (reusable task patterns)

---

## Roadmap

- [ ] Web dashboard UI (no terminal required)
- [ ] One-click Hermes integration
- [ ] Persona marketplace
- [ ] iOS/Android companion app
- [ ] Multi-user / family mode
- [ ] Offline model support (Ollama)

---

## Community

- [Discord](https://discord.gg/personalos)
- [GitHub Discussions](https://github.com/krishnatejaganesh/PersonalOS/discussions)
- [Roadmap](https://github.com/krishnatejaganesh/PersonalOS/projects)

## License

MIT — use it, fork it, build on it. See [LICENSE](LICENSE).

---

*PersonalOS is not affiliated with Anthropic, OpenAI, Google, or any AI company. It's a community project.*
