"""Tests for core/self_improve.py"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import Response

from core.self_improve import Evaluator, WorkflowStore, after_task


# ─── Helpers ──────────────────────────────────────────────────────────────────

def openrouter_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def make_pool(fetchrow_result=None, fetch_result=None, execute_result="DELETE 3"):
    """Return a mock asyncpg pool."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.fetch = AsyncMock(return_value=fetch_result or [])
    conn.execute = AsyncMock(return_value=execute_result)

    pool = MagicMock()
    pool.acquire = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool, conn


# ─── Evaluator ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_evaluator_returns_score_and_notes() -> None:
    payload = json.dumps({"score": 0.9, "notes": "Clean and correct output."})
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json=openrouter_response(payload))
    )

    evaluator = Evaluator(fast_model="gemini-flash", api_key="test-key")
    score, notes = await evaluator.score("code_fix", {}, [], "output text")

    assert score == pytest.approx(0.9)
    assert notes == "Clean and correct output."


@pytest.mark.asyncio
@respx.mock
async def test_evaluator_strips_markdown_fences() -> None:
    payload = "```json\n" + json.dumps({"score": 0.8, "notes": "Good."}) + "\n```"
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json=openrouter_response(payload))
    )

    evaluator = Evaluator(fast_model="gemini-flash", api_key="test-key")
    score, notes = await evaluator.score("email_reply", {}, [], "output")

    assert score == pytest.approx(0.8)
    assert notes == "Good."


@pytest.mark.asyncio
@respx.mock
async def test_evaluator_clamps_score_to_valid_range() -> None:
    payload = json.dumps({"score": 1.5, "notes": "Over max."})
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json=openrouter_response(payload))
    )

    evaluator = Evaluator(fast_model="gemini-flash", api_key="test-key")
    score, _ = await evaluator.score("task", {}, [], "output")

    assert score == pytest.approx(1.0)


@pytest.mark.asyncio
@respx.mock
async def test_evaluator_returns_default_on_api_failure() -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(500)
    )

    evaluator = Evaluator(fast_model="gemini-flash", api_key="test-key")
    score, notes = await evaluator.score("task", {}, [], "output")

    assert score == pytest.approx(0.5)
    assert "Auto-scoring failed" in notes


@pytest.mark.asyncio
@respx.mock
async def test_evaluator_returns_default_on_malformed_json() -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json=openrouter_response("not json at all"))
    )

    evaluator = Evaluator(fast_model="gemini-flash", api_key="test-key")
    score, _ = await evaluator.score("task", {}, [], "output")

    assert score == pytest.approx(0.5)


# ─── WorkflowStore.save ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_workflow_store_save_marks_reuse_when_above_threshold() -> None:
    pool, conn = make_pool()
    store = WorkflowStore(pool, reuse_threshold=0.75)

    await store.save("code_fix", {}, [], "success", score=0.9)

    call_args = conn.execute.call_args
    # args: (sql, task_type, task_input, steps, outcome, score, reuse, notes)
    assert call_args.args[6] is True


@pytest.mark.asyncio
async def test_workflow_store_save_marks_no_reuse_when_below_threshold() -> None:
    pool, conn = make_pool()
    store = WorkflowStore(pool, reuse_threshold=0.75)

    await store.save("code_fix", {}, [], "poor result", score=0.5)

    call_args = conn.execute.call_args
    assert call_args.args[6] is False


# ─── WorkflowStore.best_workflow ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_best_workflow_returns_none_when_no_match() -> None:
    pool, _ = make_pool(fetchrow_result=None)
    store = WorkflowStore(pool)

    result = await store.best_workflow("nonexistent_task")

    assert result is None


@pytest.mark.asyncio
async def test_best_workflow_returns_steps_and_updates_by_id() -> None:
    steps = [{"tool": "read_file", "args": {"path": "main.py"}}]
    row = {
        "id": 42,
        "steps": json.dumps(steps),
        "score": 0.92,
        "times_reused": 3,
    }
    pool, conn = make_pool(fetchrow_result=row)
    store = WorkflowStore(pool)

    result = await store.best_workflow("code_fix")

    assert result == steps
    # UPDATE must use id=42, not task_type+score
    update_call = conn.execute.call_args
    assert update_call.args[1] == 42


@pytest.mark.asyncio
async def test_best_workflow_increments_times_reused() -> None:
    steps = [{"tool": "search"}]
    row = {"id": 7, "steps": json.dumps(steps), "score": 0.8, "times_reused": 1}
    pool, conn = make_pool(fetchrow_result=row)
    store = WorkflowStore(pool)

    await store.best_workflow("research")

    assert conn.execute.called


# ─── WorkflowStore.weekly_report ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_weekly_report_no_data() -> None:
    pool, _ = make_pool(fetch_result=[])
    store = WorkflowStore(pool)

    report = await store.weekly_report()

    assert "No workflow data" in report


@pytest.mark.asyncio
async def test_weekly_report_formats_rows() -> None:
    rows = [
        {
            "task_type": "code_fix",
            "total": 5,
            "avg_score": 0.88,
            "reuses": 3,
            "best_score": 0.95,
        }
    ]
    pool, _ = make_pool(fetch_result=rows)
    store = WorkflowStore(pool)

    report = await store.weekly_report()

    assert "code_fix" in report
    assert "0.88" in report
    assert "0.95" in report


# ─── WorkflowStore.prune_poor_workflows ───────────────────────────────────────

@pytest.mark.asyncio
async def test_prune_returns_count_of_deleted_rows() -> None:
    pool, _ = make_pool(execute_result="DELETE 7")
    store = WorkflowStore(pool)

    count = await store.prune_poor_workflows(min_score=0.4)

    assert count == 7


# ─── after_task ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_after_task_scores_and_saves() -> None:
    payload = json.dumps({"score": 0.85, "notes": "Good result."})
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json=openrouter_response(payload))
    )

    pool, conn = make_pool()
    evaluator = Evaluator(fast_model="gemini-flash", api_key="test-key")

    score = await after_task(
        db_pool=pool,
        evaluator=evaluator,
        task_type="code_fix",
        task_input={"description": "fix login bug"},
        steps=[{"tool": "edit_file"}],
        output="Fixed the bug in auth.py.",
    )

    assert score == pytest.approx(0.85)
    assert conn.execute.called
