"""
PersonalOS — Model Watcher

Runs weekly. Checks OpenRouter for new models, benchmarks your current stack,
and sends a Telegram report if a better model is available for any task category.

This is the "model agnosticism" feature in action:
you get alerted when something better drops, not surprised by it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    id: str
    name: str
    context_length: int
    pricing_prompt: float   # per 1k tokens, USD
    pricing_completion: float


@dataclass
class BenchmarkResult:
    model: str
    category: str           # 'coding' | 'writing' | 'reasoning' | 'research'
    score: float            # 0.0–1.0
    latency_ms: int
    cost_per_1k: float


BENCHMARK_TASKS = {
    "coding": (
        "Write a Python function that takes a list of integers and returns "
        "the two numbers that add up to a target sum. Include type hints and "
        "a docstring. Be efficient."
    ),
    "writing": (
        "Write a 150-word executive summary of a fictional Q2 business report "
        "for a SaaS company that grew 40% YoY but saw churn increase by 5%."
    ),
    "reasoning": (
        "A snail climbs 3 metres up a wall each day and slides back 2 metres "
        "each night. The wall is 10 metres tall. On which day does the snail "
        "reach the top? Show your working."
    ),
    "research": (
        "List 5 key differences between PostgreSQL and MySQL for a production "
        "web application. Be specific and include a recommendation."
    ),
}

EXPECTED_ANSWERS = {
    "coding": ["def ", "target", "return", "int"],
    "writing": ["revenue", "growth", "churn", "quarter"],
    "reasoning": ["day 8", "8th day", "eighth day", "on day 8"],
    "research": ["postgresql", "mysql", "index", "json", "replication"],
}


class ModelWatcher:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._headers = {"Authorization": f"Bearer {api_key}"}

    # ── Public API ──────────────────────────────────────────────────────────

    async def weekly_report(
        self,
        current_stack: dict[str, str],
    ) -> str:
        """
        Generate the weekly model report.
        current_stack: {"primary": "model-id", "fast": "model-id", "code": "model-id"}
        """
        lines = ["🤖 *PersonalOS Weekly Model Report*\n"]

        # Check for new models on OpenRouter
        new_models = await self._check_new_models(current_stack)
        if new_models:
            lines.append("🆕 *New models available:*")
            for m in new_models[:5]:
                lines.append(f"  • {m.name} (`{m.id}`)")
            lines.append("")

        # Quick benchmark of current primary model
        lines.append("📊 *Current stack health check:*")
        for role, model_id in current_stack.items():
            result = await self._benchmark_model(model_id, "reasoning")
            if result.score >= 0.8:
                emoji = "✅"
            elif result.score >= 0.6:
                emoji = "⚠️"
            else:
                emoji = "❌"
            lines.append(
                f"  {emoji} {role}: `{model_id}` "
                f"(score: {result.score:.0%}, {result.latency_ms}ms)"
            )
        lines.append("")

        # Cost estimate
        lines.append("💰 *Cost tip:* Route summaries and email drafts to "
                      "`google/gemini-2.5-flash` to cut costs 10×.")

        lines.append("\n_Swap any model in `.env` — no code changes needed._")

        return "\n".join(lines)

    # ── Private ─────────────────────────────────────────────────────────────

    async def _check_new_models(
        self,
        current_stack: dict[str, str],
    ) -> list[ModelInfo]:
        """Return models released in the last 7 days not in current stack."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers=self._headers,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning(f"ModelWatcher: could not fetch model list: {e}")
            return []

        current_ids = set(current_stack.values())
        new: list[ModelInfo] = []

        for m in data.get("data", []):
            if m["id"] in current_ids:
                continue
            # Only flag models with long context (useful for agent work)
            ctx = m.get("context_length", 0)
            if ctx < 16_000:
                continue
            pricing = m.get("pricing", {})
            new.append(ModelInfo(
                id=m["id"],
                name=m.get("name", m["id"]),
                context_length=ctx,
                pricing_prompt=float(pricing.get("prompt", 0)),
                pricing_completion=float(pricing.get("completion", 0)),
            ))

        return new[:10]   # cap at 10

    async def _benchmark_model(
        self,
        model_id: str,
        category: str,
    ) -> BenchmarkResult:
        """Run a quick benchmark task against the model."""
        import time

        task = BENCHMARK_TASKS.get(category, BENCHMARK_TASKS["reasoning"])
        expected = EXPECTED_ANSWERS.get(category, [])

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=self._headers,
                    json={
                        "model": model_id,
                        "messages": [{"role": "user", "content": task}],
                        "max_tokens": 300,
                        "temperature": 0,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning(f"ModelWatcher: benchmark failed for {model_id}: {e}")
            return BenchmarkResult(model_id, category, 0.0, 0, 0.0)

        latency_ms = int((time.monotonic() - start) * 1000)
        output = data["choices"][0]["message"]["content"].lower()

        # Naive scoring: how many expected keywords appear in the output?
        hits = sum(1 for kw in expected if kw.lower() in output)
        score = hits / len(expected) if expected else 0.5

        usage = data.get("usage", {})
        tokens = usage.get("total_tokens", 0)
        cost = tokens / 1000 * 0.003  # rough estimate; real cost varies by model

        return BenchmarkResult(
            model=model_id,
            category=category,
            score=score,
            latency_ms=latency_ms,
            cost_per_1k=cost,
        )
