"""Tests for core/router.py"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import respx
from httpx import Response

from core.router import AgentConfig, Router, load_agent_configs


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def make_router(tmp_path: Path, agents: dict | None = None) -> Router:
    """Build a Router with fake agent configs written to a temp directory."""
    if agents is None:
        agents = {
            "developer": {
                "model": "claude-sonnet-4-6",
                "tools": ["github"],
                "triggers": [r"\bfix\b", r"\bbug\b", r"\bcode\b"],
                "description": "Handles coding, PRs, and debugging.",
            },
            "seo": {
                "model": "gemini-flash",
                "tools": [],
                "triggers": [r"\bseo\b", r"\barticle\b", r"\bcontent\b"],
                "description": "Handles SEO and content writing.",
            },
            "chief-of-staff": {
                "model": "claude-sonnet-4-6",
                "tools": ["gmail", "calendar"],
                "triggers": [],
                "description": "General assistant and coordinator.",
            },
        }

    for name, cfg in agents.items():
        agent_dir = tmp_path / name
        agent_dir.mkdir()
        (agent_dir / "config.yaml").write_text(
            "\n".join(f"{k}: {json.dumps(v)}" for k, v in cfg.items())
        )
        (agent_dir / "soul.md").write_text(f"# {name}")

    return Router(tmp_path, fast_model="gemini-flash", openrouter_api_key="test-key")


def openrouter_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


# ─── load_agent_configs ────────────────────────────────────────────────────────

def test_load_agent_configs(tmp_path: Path) -> None:
    (tmp_path / "developer").mkdir()
    (tmp_path / "developer" / "config.yaml").write_text(
        'model: "claude-sonnet-4-6"\ntools: ["github"]\ntriggers: ["bug"]\ndescription: "dev"'
    )
    (tmp_path / "developer" / "soul.md").write_text("# developer")

    configs = load_agent_configs(tmp_path)
    assert "developer" in configs
    assert configs["developer"].model == "claude-sonnet-4-6"
    assert configs["developer"].tools == ["github"]
    assert configs["developer"].triggers == ["bug"]


def test_load_agent_configs_missing_fields_use_defaults(tmp_path: Path) -> None:
    (tmp_path / "minimal").mkdir()
    (tmp_path / "minimal" / "config.yaml").write_text("{}")
    (tmp_path / "minimal" / "soul.md").write_text("")

    configs = load_agent_configs(tmp_path)
    assert configs["minimal"].model == "anthropic/claude-sonnet-4-6"
    assert configs["minimal"].tools == []
    assert configs["minimal"].triggers == []


# ─── Explicit mention routing ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_explicit_mention_routes_correctly(tmp_path: Path) -> None:
    router = make_router(tmp_path)
    assert await router.route("@developer fix the login bug") == "developer"
    assert await router.route("@seo write an article") == "seo"


@pytest.mark.asyncio
async def test_alias_dev_routes_to_developer(tmp_path: Path) -> None:
    router = make_router(tmp_path)
    assert await router.route("@dev fix this") == "developer"


@pytest.mark.asyncio
async def test_alias_chief_routes_to_chief_of_staff(tmp_path: Path) -> None:
    router = make_router(tmp_path)
    assert await router.route("@chief what's my schedule?") == "chief-of-staff"


@pytest.mark.asyncio
async def test_explicit_mention_case_insensitive(tmp_path: Path) -> None:
    router = make_router(tmp_path)
    assert await router.route("@DEVELOPER please fix this") == "developer"


# ─── Keyword matching ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_keyword_match_bug_routes_to_developer(tmp_path: Path) -> None:
    router = make_router(tmp_path)
    assert await router.route("there's a bug in the payment flow") == "developer"


@pytest.mark.asyncio
async def test_keyword_match_article_routes_to_seo(tmp_path: Path) -> None:
    router = make_router(tmp_path)
    assert await router.route("write an article about Python") == "seo"


@pytest.mark.asyncio
async def test_keyword_match_is_case_insensitive(tmp_path: Path) -> None:
    router = make_router(tmp_path)
    assert await router.route("Fix the BUG please") == "developer"


# ─── Semantic classification ──────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_semantic_classification_used_when_no_keyword_match(tmp_path: Path) -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json=openrouter_response("developer"))
    )
    router = make_router(tmp_path)
    result = await router.route("I need help with something technical")
    assert result == "developer"


@pytest.mark.asyncio
@respx.mock
async def test_semantic_classification_api_failure_falls_back(tmp_path: Path) -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(500)
    )
    router = make_router(tmp_path)
    result = await router.route("something totally ambiguous")
    assert result == "chief-of-staff"


@pytest.mark.asyncio
@respx.mock
async def test_semantic_classification_unknown_agent_falls_back(tmp_path: Path) -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json=openrouter_response("unknown-agent-xyz"))
    )
    router = make_router(tmp_path)
    result = await router.route("something ambiguous")
    assert result == "chief-of-staff"


# ─── Fallback ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_fallback_to_chief_of_staff(tmp_path: Path) -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json=openrouter_response("chief-of-staff"))
    )
    router = make_router(tmp_path)
    result = await router.route("what should I focus on today?")
    assert result == "chief-of-staff"


# ─── Dynamic pattern picks up custom agents ──────────────────────────────────

@pytest.mark.asyncio
async def test_custom_agent_explicit_mention(tmp_path: Path) -> None:
    agents = {
        "my-custom-agent": {
            "model": "claude-sonnet-4-6",
            "tools": [],
            "triggers": [],
            "description": "Custom agent.",
        },
        "chief-of-staff": {
            "model": "claude-sonnet-4-6",
            "tools": [],
            "triggers": [],
            "description": "General assistant.",
        },
    }
    router = make_router(tmp_path, agents=agents)
    assert await router.route("@my-custom-agent do something") == "my-custom-agent"
