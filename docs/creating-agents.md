# Creating a Custom Agent

PersonalOS agents are just two files: a `soul.md` (identity) and a `config.yaml` (settings).
You can build one in 15 minutes.

---

## When to create a new agent

Create a new agent when:
- You have a specialist domain that none of the existing agents cover
- You want a separate identity and toolset for a distinct type of work
- You want the Chief of Staff to delegate to a specialist rather than handle it directly

Good candidates for custom agents:
- Finance agent (bookkeeping, invoicing, P&L)
- Social media agent (post writing, scheduling)
- Travel agent (flight search, itinerary planning)
- Health agent (workout plans, nutrition)
- Legal agent (contract review, basic compliance)

---

## Step 1 — Create the directory

```bash
# Replace 'finance' with your agent name (lowercase, hyphen-separated)
cp -r agents/researcher agents/finance
```

---

## Step 2 — Write the soul (`soul.md`)

The soul is the agent's identity. It's injected into every conversation this agent has.

```markdown
# Finance Agent — Soul

You are a financial analyst and bookkeeper working for {{USER_NAME}}.

## Your principles

- Numbers don't lie, but they can mislead. Always add context.
- Flag cashflow issues before they become crises.
- Keep the books clean — a small error caught early saves hours later.

## Communication style

- Lead with the number, then the interpretation.
- Use tables for financial data — they're easier to scan than prose.
- Flag anomalies clearly: "⚠️ This month's expenses are 23% above forecast."

## What you never do

- Never make financial recommendations without stating your assumptions.
- Never confuse revenue with profit — always be explicit.
- Never delete financial records, even if they look like duplicates.
```

**What makes a good soul:**

- **Principles** — not just what the agent does, but *how* it thinks
- **Communication style** — how it writes to you
- **Hard rules** — explicit "never do" list prevents the most common failures
- **The `{{USER_NAME}}` placeholder** — gets replaced with your actual name on startup

---

## Step 3 — Write the config (`config.yaml`)

```yaml
# Finance Agent Configuration

# Shown to the router when classifying tasks
description: "Bookkeeping, invoicing, expense tracking, P&L summaries, and cashflow monitoring"

# Which model to use (inherits from .env if blank)
model: "${FAST_MODEL}"

# Tools this agent can use
# Available tools: web_search, read_email, read_file, write_file,
#                  read_calendar, run_terminal, read_github, write_github,
#                  send_telegram, delegate_to_agent, read_memory, write_memory
tools:
  - read_file
  - write_file
  - web_search
  - read_memory

# Keywords that route tasks to this agent (regex supported)
triggers:
  - "invoice|billing|payment|paid|unpaid"
  - "expense|cost|spend|budget|forecast"
  - "revenue|profit|loss|p&l|cashflow"
  - "bookkeeping|accounting|tax|vat|gst"
  - "@finance"

# Memory tags this agent reads at startup
memory:
  read_on_start: true
  tags:
    - financial_context
    - business_metrics
    - invoice_policies
```

---

## Step 4 — Register the agent

PersonalOS discovers agents automatically from the `agents/` directory.
Restart the API to pick it up:

```bash
docker compose restart api
```

Test it:
```
@finance What are my top 3 unpaid invoices right now?
```

---

## Step 5 — Teach it your context

On first use, give your new agent relevant memory:

```
Remember for the finance agent:
- My fiscal year runs January to December
- I invoice in GBP
- Payment terms: 30 days net
- My Stripe revenue is the source of truth for digital revenue
- Restaurant revenue comes from Square dashboard
```

---

## Contributing your agent

If your agent could be useful to others, contribute it:

1. Fork the repo
2. Add your `agents/your-agent-name/` directory
3. Add a line to the agents table in `README.md`
4. Open a PR

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the quality bar.
