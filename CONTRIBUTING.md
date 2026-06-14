# Contributing to PersonalOS

Thank you for contributing. PersonalOS grows through community contributions,
and the most impactful ones are simple: a persona that fits your life, an agent
profile for your work, or an integration for a tool you use.

---

## What to contribute

### 🧑 Personas (most wanted)

A persona is a pre-built configuration for a specific life situation.
We have: `solo-founder`, `freelancer`, `student`, `ecommerce`, `default`.

We want personas for:
- Parent managing family + work
- Creator (YouTuber, newsletter writer, podcaster)
- Researcher / academic
- Remote team manager
- Investor / VC
- Athlete / sports professional
- Doctor / healthcare worker
- Anything we haven't thought of

To add a persona:

```bash
cp -r personas/default personas/your-persona-name
# Edit persona.yaml with your priorities, briefing focus, memory starters
# Open a PR with title: "Add [persona name] persona"
```

See `personas/solo-founder/persona.yaml` for the full format with comments.

### 🤖 Agent Profiles

An agent is a specialist AI worker. We have: Chief of Staff, Developer,
SEO, Researcher, Support.

Agents we'd love to see:
- Finance agent (bookkeeping, expenses, P&L summary)
- Legal agent (contract review, basic legal questions)
- Health agent (workout planning, nutrition tracking)
- Travel agent (flight search, itinerary building)
- Social media agent (post scheduling, engagement)

To add an agent:

```bash
cp -r agents/researcher agents/your-agent-name
# Edit soul.md (identity + principles)
# Edit config.yaml (model, tools, triggers)
# Open a PR with title: "Add [agent name] agent"
```

### 🔌 Integrations

An integration connects PersonalOS to an external service.
See `integrations/` for examples.

Services we need:
- Notion
- Linear
- Airtable
- Shopify
- QuickBooks / Xero
- HubSpot
- Twitter/X

### 📄 Skill Templates

A skill template is a reusable prompt pattern for a common task.
See `skills/examples/` for the format.

---

## How to contribute

1. **Fork** the repository
2. **Create a branch**: `git checkout -b add-parent-persona`
3. **Make your changes**
4. **Test it**: run `./scripts/setup.sh` in a test environment and verify it works
5. **Open a PR** with a clear title and description

### PR title format

```
Add [name] persona
Add [name] agent
Add [service] integration
Fix [what]: [brief description]
Docs: [what]
```

---

## Quality bar

**Personas** — must include:
- At least 5 priorities in the right order for this person
- Realistic `briefing_focus` for their daily situation
- Sensible `autonomous_ok` and `requires_confirmation` lists
- At least 3 `starter_memory` entries that give immediate useful context
- A clear description in the header comment explaining who should use it

**Agents** — must include:
- A `soul.md` with clear principles, not just a job description
- At least 3 "what you never do" rules (these prevent common failures)
- A `config.yaml` with realistic trigger keywords
- A description that makes it clear what this agent handles vs what it doesn't

**Integrations** — must include:
- Working code (tested against the real API)
- Error handling — integrations will fail; handle it gracefully
- A note in the docstring about required credentials and where to get them

---

## Code style

- Python: follow the existing style (type hints, docstrings, `asyncio`)
- YAML: 2-space indent, comment non-obvious fields
- Markdown: clear headers, no unnecessary formatting

---

## First contribution?

Look for issues labelled `good first issue`. These are usually adding a
persona for a use case we've sketched but haven't built out, or improving
documentation.

---

## Questions?

Open a GitHub Discussion or join the [Discord](https://discord.gg/personalos).
