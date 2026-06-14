"""
PersonalOS — Task Router
Routes incoming tasks to the most appropriate agent based on:
1. Explicit agent mention ("@developer fix this bug")
2. Keyword matching against agent trigger lists
3. Semantic classification via the fast model
4. Fallback to Chief of Staff
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
import yaml

logger = logging.getLogger(__name__)

# ─── Agent Registry ────────────────────────────────────────────────────────

@dataclass
class AgentConfig:
    name: str
    soul_file: Path
    model: str
    tools: list[str]
    triggers: list[str]       # keyword patterns that route to this agent
    description: str = ""     # shown to the classifier model


def load_agent_configs(agents_dir: Path) -> dict[str, AgentConfig]:
    """Read every agent's config.yaml from the agents/ directory."""
    configs: dict[str, AgentConfig] = {}
    for config_file in agents_dir.glob("*/config.yaml"):
        agent_name = config_file.parent.name
        with config_file.open() as f:
            raw = yaml.safe_load(f)
        soul_file = config_file.parent / "soul.md"
        configs[agent_name] = AgentConfig(
            name=agent_name,
            soul_file=soul_file,
            model=raw.get("model", "anthropic/claude-sonnet-4-6"),
            tools=raw.get("tools", []),
            triggers=raw.get("triggers", []),
            description=raw.get("description", ""),
        )
    return configs


# ─── Router ───────────────────────────────────────────────────────────────

class Router:
    """Routes tasks to the right agent."""

    AGENT_ALIASES: dict[str, str] = {
        "dev": "developer",
        "cs": "chief-of-staff",
        "chief": "chief-of-staff",
        "research": "researcher",
    }

    def __init__(
        self,
        agents_dir: Path,
        fast_model: str,
        openrouter_api_key: str,
    ) -> None:
        self.agents = load_agent_configs(agents_dir)
        self.fast_model = fast_model
        self.api_key = openrouter_api_key
        # Build pattern dynamically so custom agents are picked up automatically
        names = list(self.agents.keys()) + list(self.AGENT_ALIASES.keys())
        pattern = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
        self.EXPLICIT_PATTERN = re.compile(
            rf"@(?P<agent>{pattern})", re.IGNORECASE
        )

    # ── Public API ──────────────────────────────────────────────────────────

    async def route(self, task: str, context: dict | None = None) -> str:
        """Return the agent name best suited to handle this task."""

        # 1. Explicit mention (@developer, @seo, etc.)
        match = self.EXPLICIT_PATTERN.search(task)
        if match:
            raw = match.group("agent").lower()
            agent = self.AGENT_ALIASES.get(raw, raw)
            if agent in self.agents:
                logger.info(f"Router: explicit mention → {agent}")
                return agent

        # 2. Keyword matching (fast, no API call)
        for agent_name, config in self.agents.items():
            for trigger in config.triggers:
                if re.search(trigger, task, re.IGNORECASE):
                    logger.info(f"Router: keyword match ({trigger!r}) → {agent_name}")
                    return agent_name

        # 3. Semantic classification via fast model
        classified = await self._classify(task)
        if classified and classified in self.agents:
            logger.info(f"Router: semantic classification → {classified}")
            return classified

        # 4. Fallback
        logger.info("Router: fallback → chief-of-staff")
        return "chief-of-staff"

    # ── Private ─────────────────────────────────────────────────────────────

    async def _classify(self, task: str) -> Optional[str]:
        """Use the fast model to pick the best agent."""
        agent_list = "\n".join(
            f"- {name}: {cfg.description}"
            for name, cfg in self.agents.items()
        )
        prompt = (
            f"You are a task router. Choose the best agent for the task.\n\n"
            f"AGENTS:\n{agent_list}\n\n"
            f"TASK: {task}\n\n"
            f"Reply with ONLY the agent name, nothing else. "
            f"If no specialist fits, reply: chief-of-staff"
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.fast_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 20,
                        "temperature": 0,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                result = data["choices"][0]["message"]["content"].strip().lower()
                # Normalise (model might return "Developer" or "the developer agent")
                for name in self.agents:
                    if name in result:
                        return name
        except Exception as e:
            logger.warning(f"Router: semantic classification failed: {e}")

        return None
