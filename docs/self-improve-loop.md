# How the Self-Improving Loop Works

PersonalOS gets smarter over time without changing the model.
Here's exactly how.

---

## The core idea

Every time an agent completes a task, the system:

1. **Evaluates** the outcome (did it actually work well?)
2. **Scores** it from 0.0 to 1.0
3. **Saves** the winning steps to a database
4. **Retrieves** those steps next time a similar task comes in

After weeks of use, PersonalOS has a library of proven playbooks for your
specific situation. It stops reasoning from scratch and starts from what worked.

---

## What gets saved

```sql
-- Example: a morning briefing that went well
{
  "task_type": "morning_briefing",
  "steps": [
    {"tool": "read_email", "args": {"count": 12, "filter": "unread"}},
    {"tool": "read_calendar", "args": {"days_ahead": 1}},
    {"tool": "web_search", "args": {"query": "{{USER_INDUSTRY}} news today"}},
    {"tool": "send_telegram", "args": {"format": "briefing_template"}}
  ],
  "score": 0.91,
  "outcome": "User replied: 'perfect, exactly what I needed'"
}
```

---

## The scoring system

The evaluator agent scores every outcome. The score reflects:

| Score | Meaning | Action |
|-------|---------|--------|
| 0.0–0.4 | Failed or poor quality | Not saved for reuse |
| 0.5–0.7 | Acceptable | Saved but low priority |
| 0.75–0.9 | Good | Reused as starting plan |
| 0.9–1.0 | Excellent | Prioritised for reuse |

The threshold for reuse is 0.75 by default. Change it in `.env`:
```
WORKFLOW_REUSE_THRESHOLD=0.75
```

---

## What "reuse" actually means

When a task comes in, the router checks the database:

```sql
SELECT steps FROM workflow_outcomes
WHERE task_type = 'morning_briefing'
  AND score >= 0.75
ORDER BY score DESC
LIMIT 1;
```

If a match exists, the agent is told:

> "A similar task was completed successfully before. Here's what worked:
> [steps]. Start from this plan and adapt it to today's context."

If no match exists, the agent reasons from scratch. That outcome is then
evaluated and potentially added to the library.

---

## The evaluator

The evaluator is a separate agent call (using the fast model, to keep costs down).
It sees:
- What the task was
- What steps the agent took
- What output was produced

And asks:
1. Did the task complete without errors?
2. Was the output accurate and relevant?
3. Were the steps efficient?
4. Would a human be satisfied?

---

## Weekly review

Every Sunday morning, PersonalOS sends you a self-improvement report:

```
📊 Self-Improvement Weekly Report

• morning_briefing: 5 runs, avg score 0.88, best 0.94, reused 4×
• email_reply_draft: 8 runs, avg score 0.79, best 0.89, reused 6×
• seo_article: 2 runs, avg score 0.71 — below reuse threshold, not yet in library
• bug_fix: 3 runs, avg score 0.85, best 0.92, reused 2×
```

This tells you which task types are "trained" and which still need a few runs to
build up a good playbook.

---

## Pruning poor workflows

Occasionally prune low-quality workflows so retrieval stays clean:

```
Ask PersonalOS: "Prune any workflows scored below 0.4"
```

Or it runs automatically once a month.

---

## The limits of self-improvement

**This is not model fine-tuning.** The AI model itself never changes.
What improves is the *starting plan* the agent receives, and the *context*
it has about what worked in your specific situation.

Think of it like this: a new chef reasons from cooking principles. An experienced
chef at your restaurant knows which dishes you order, which ingredients you prefer,
and which preparations have worked before. The self-improving loop builds that
restaurant-specific knowledge over time.

**Common failure mode:** if the evaluator is too lenient (scoring mediocre
outputs at 0.85), the system learns bad habits. The weekly review helps you
catch this. If you notice an agent producing outputs you wouldn't accept, check
recent scores:

```
Show me the last 10 workflow scores for morning_briefing
```

And if scores look inflated, tell PersonalOS:

```
Remember: be strict when scoring outcomes. A briefing that missed
an urgent email should score below 0.5, even if everything else was good.
```
