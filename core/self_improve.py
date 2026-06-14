"""
PersonalOS — Self-Improving Loop

After every completed task:
1. Evaluator scores the outcome (0.0–1.0)
2. Score + steps saved to workflow_outcomes table
3. Next time the same task type runs, best workflow is loaded first

This means the system gets better over time without changing the model.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import asyncpg
import httpx

logger = logging.getLogger(__name__)


# ─── Outcome Evaluator ────────────────────────────────────────────────────

class Evaluator:
    """Scores task outcomes using the fast model."""

    def __init__(self, fast_model: str, api_key: str) -> None:
        self.model = fast_model
        self.api_key = api_key

    async def score(
        self,
        task_type: str,
        task_input: dict,
        steps: list[dict],
        output: str,
    ) -> tuple[float, str]:
        """
        Returns (score: 0.0–1.0, notes: str).
        Score meaning:
            0.0–0.4  — failed or poor quality
            0.5–0.7  — acceptable, room for improvement
            0.75–0.9 — good, worth reusing
            0.9–1.0  — excellent, prioritise for reuse
        """
        prompt = f"""You are a task quality evaluator \
for a personal AI operating system.

Score the outcome of this completed task on a scale from 0.0 to 1.0.

TASK TYPE: {task_type}
TASK INPUT: {json.dumps(task_input, indent=2)}
STEPS TAKEN: {json.dumps(steps, indent=2)}
OUTPUT PRODUCED:
{output}

Scoring criteria:
- Did the task complete without errors?
- Was the output accurate and relevant?
- Were the steps efficient (no unnecessary tool calls)?
- Would a human be satisfied with this result?

Reply in this exact JSON format:
{{
  "score": 0.85,
  "notes": "one sentence explaining the score"
}}
"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 100,
                        "temperature": 0,
                    },
                )
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"].strip()
                # Strip markdown fences if present
                text = text.replace("```json", "").replace("```", "").strip()
                data = json.loads(text)
                score = float(data.get("score", 0.5))
                notes = str(data.get("notes", ""))
                return max(0.0, min(1.0, score)), notes
        except Exception as e:
            logger.warning(f"Evaluator: scoring failed: {e}. Using default 0.5.")
            return 0.5, f"Auto-scoring failed: {e}"


# ─── Workflow Store ───────────────────────────────────────────────────────

class WorkflowStore:
    """Reads and writes workflow outcomes to PostgreSQL."""

    def __init__(self, db_pool: asyncpg.Pool, reuse_threshold: float = 0.75) -> None:
        self.pool = db_pool
        self.reuse_threshold = reuse_threshold

    async def save(
        self,
        task_type: str,
        task_input: dict,
        steps: list[dict],
        outcome: str,
        score: float,
        notes: str = "",
    ) -> None:
        """Save a workflow outcome after a completed task."""
        reuse = score >= self.reuse_threshold
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO workflow_outcomes
                    (task_type, task_input, steps, outcome, score, reuse, notes)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                task_type,
                json.dumps(task_input),
                json.dumps(steps),
                outcome,
                score,
                reuse,
                notes,
            )
        logger.info(
            f"SelfImprove: saved outcome for {task_type!r} "
            f"(score={score:.2f}, reuse={reuse})"
        )

    async def best_workflow(self, task_type: str) -> Optional[list[dict]]:
        """
        Retrieve the highest-scoring reusable workflow for this task type.
        Returns None if no workflow meets the threshold.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, steps, score, times_reused
                FROM workflow_outcomes
                WHERE task_type = $1
                  AND reuse = true
                  AND score >= $2
                ORDER BY score DESC
                LIMIT 1
                """,
                task_type,
                self.reuse_threshold,
            )
            if not row:
                return None

            # Increment reuse counter using id to avoid matching duplicate scores
            await conn.execute(
                """
                UPDATE workflow_outcomes
                SET times_reused = times_reused + 1,
                    last_reused = NOW()
                WHERE id = $1
                """,
                row["id"],
            )
            steps = json.loads(row["steps"])
            logger.info(
                f"SelfImprove: loaded workflow for {task_type!r} "
                f"(score={row['score']:.2f}, used {row['times_reused']} times before)"
            )
            return steps

    async def weekly_report(self) -> str:
        """Generate a weekly self-improvement summary."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    task_type,
                    COUNT(*) AS total,
                    AVG(score) AS avg_score,
                    SUM(times_reused) AS reuses,
                    MAX(score) AS best_score
                FROM workflow_outcomes
                WHERE created_at >= NOW() - INTERVAL '7 days'
                GROUP BY task_type
                ORDER BY avg_score DESC
                """
            )

        if not rows:
            return "No workflow data from the past 7 days yet."

        lines = ["📊 *Self-Improvement Weekly Report*\n"]
        for row in rows:
            lines.append(
                f"• *{row['task_type']}*: "
                f"{row['total']} runs, avg score {row['avg_score']:.2f}, "
                f"best {row['best_score']:.2f}, reused {row['reuses']}×"
            )
        return "\n".join(lines)

    async def prune_poor_workflows(self, min_score: float = 0.4) -> int:
        """Remove workflows below the minimum score — keeps retrieval clean."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM workflow_outcomes WHERE score < $1",
                min_score,
            )
        count = int(result.split()[-1])
        logger.info(f"SelfImprove: pruned {count} poor workflows (score < {min_score})")
        return count


# ─── Self-Improve Loop (called after every task) ──────────────────────────

async def after_task(
    *,
    db_pool: asyncpg.Pool,
    evaluator: Evaluator,
    task_type: str,
    task_input: dict,
    steps: list[dict],
    output: str,
) -> float:
    """
    Call this after every completed task.
    Scores the outcome and saves it.
    Returns the score so the caller can log it.
    """
    score, notes = await evaluator.score(task_type, task_input, steps, output)
    store = WorkflowStore(db_pool)
    await store.save(
        task_type=task_type,
        task_input=task_input,
        steps=steps,
        outcome=output[:500],  # trim to avoid huge rows
        score=score,
        notes=notes,
    )
    return score
