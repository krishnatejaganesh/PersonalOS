"""Tests for core/model_watcher.py"""

from __future__ import annotations

import time

import pytest
import respx
from httpx import Response

from core.model_watcher import BenchmarkResult, ModelWatcher


# ─── Helpers ──────────────────────────────────────────────────────────────────

def openrouter_response(content: str, tokens: int = 50) -> dict:
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"total_tokens": tokens},
    }


def make_model(model_id: str, ctx: int = 32_000, created_offset: int = -1) -> dict:
    """Return a fake OpenRouter model entry. created_offset is days from now."""
    return {
        "id": model_id,
        "name": model_id.split("/")[-1],
        "context_length": ctx,
        "created": time.time() + created_offset * 86_400,
        "pricing": {"prompt": "0.001", "completion": "0.002"},
    }


CURRENT_STACK = {
    "primary": "anthropic/claude-sonnet-4-6",
    "fast": "google/gemini-flash",
}


# ─── _check_new_models ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_check_new_models_returns_recent_models() -> None:
    new_model = make_model("openai/gpt-5", created_offset=-2)   # 2 days ago
    old_model = make_model("meta/llama-2", created_offset=-30)  # 30 days ago

    respx.get("https://openrouter.ai/api/v1/models").mock(
        return_value=Response(200, json={"data": [new_model, old_model]})
    )

    watcher = ModelWatcher(api_key="test-key")
    results = await watcher._check_new_models(CURRENT_STACK)

    ids = [m.id for m in results]
    assert "openai/gpt-5" in ids
    assert "meta/llama-2" not in ids


@pytest.mark.asyncio
@respx.mock
async def test_check_new_models_excludes_current_stack() -> None:
    existing = make_model("anthropic/claude-sonnet-4-6", created_offset=-1)

    respx.get("https://openrouter.ai/api/v1/models").mock(
        return_value=Response(200, json={"data": [existing]})
    )

    watcher = ModelWatcher(api_key="test-key")
    results = await watcher._check_new_models(CURRENT_STACK)

    assert all(m.id != "anthropic/claude-sonnet-4-6" for m in results)


@pytest.mark.asyncio
@respx.mock
async def test_check_new_models_excludes_small_context() -> None:
    small = make_model("tiny/model", ctx=4_000, created_offset=-1)

    respx.get("https://openrouter.ai/api/v1/models").mock(
        return_value=Response(200, json={"data": [small]})
    )

    watcher = ModelWatcher(api_key="test-key")
    results = await watcher._check_new_models(CURRENT_STACK)

    assert results == []


@pytest.mark.asyncio
@respx.mock
async def test_check_new_models_caps_at_ten() -> None:
    models = [make_model(f"vendor/model-{i}", created_offset=-1) for i in range(20)]

    respx.get("https://openrouter.ai/api/v1/models").mock(
        return_value=Response(200, json={"data": models})
    )

    watcher = ModelWatcher(api_key="test-key")
    results = await watcher._check_new_models(CURRENT_STACK)

    assert len(results) <= 10


@pytest.mark.asyncio
@respx.mock
async def test_check_new_models_returns_empty_on_api_error() -> None:
    respx.get("https://openrouter.ai/api/v1/models").mock(
        return_value=Response(500)
    )

    watcher = ModelWatcher(api_key="test-key")
    results = await watcher._check_new_models(CURRENT_STACK)

    assert results == []


# ─── _benchmark_model ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_benchmark_scores_by_keyword_hits() -> None:
    # For "reasoning" category the expected keywords include "day 8"
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(
            200,
            json=openrouter_response(
                "The snail reaches the top on day 8. Here's my working..."
            ),
        )
    )

    watcher = ModelWatcher(api_key="test-key")
    result = await watcher._benchmark_model("anthropic/claude-sonnet-4-6", "reasoning")

    assert result.score > 0
    assert result.latency_ms >= 0
    assert result.model == "anthropic/claude-sonnet-4-6"
    assert result.category == "reasoning"


@pytest.mark.asyncio
@respx.mock
async def test_benchmark_score_zero_on_no_keyword_hits() -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(
            200, json=openrouter_response("I have no idea what the answer is.")
        )
    )

    watcher = ModelWatcher(api_key="test-key")
    result = await watcher._benchmark_model("some/model", "reasoning")

    assert result.score == pytest.approx(0.0)


@pytest.mark.asyncio
@respx.mock
async def test_benchmark_returns_zero_result_on_api_error() -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(500)
    )

    watcher = ModelWatcher(api_key="test-key")
    result = await watcher._benchmark_model("some/model", "coding")

    assert result.score == pytest.approx(0.0)
    assert result.latency_ms == 0


@pytest.mark.asyncio
@respx.mock
async def test_benchmark_falls_back_to_reasoning_for_unknown_category() -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json=openrouter_response("day 8 of climbing"))
    )

    watcher = ModelWatcher(api_key="test-key")
    result = await watcher._benchmark_model("some/model", "unknown-category")

    assert result.category == "unknown-category"
    assert result.score >= 0


# ─── weekly_report ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_weekly_report_includes_stack_health() -> None:
    # Mock both model list and benchmark calls
    respx.get("https://openrouter.ai/api/v1/models").mock(
        return_value=Response(200, json={"data": []})
    )
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(
            200, json=openrouter_response("day 8 snail reasoning answer")
        )
    )

    watcher = ModelWatcher(api_key="test-key")
    report = await watcher.weekly_report(CURRENT_STACK)

    assert "PersonalOS Weekly Model Report" in report
    assert "primary" in report
    assert "fast" in report


@pytest.mark.asyncio
@respx.mock
async def test_weekly_report_shows_new_models_when_available() -> None:
    new_model = make_model("new-vendor/new-model", created_offset=-1)

    respx.get("https://openrouter.ai/api/v1/models").mock(
        return_value=Response(200, json={"data": [new_model]})
    )
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json=openrouter_response("some answer"))
    )

    watcher = ModelWatcher(api_key="test-key")
    report = await watcher.weekly_report(CURRENT_STACK)

    assert "new-model" in report
