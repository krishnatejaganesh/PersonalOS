"""
PersonalOS — GitHub Integration
Read and write to GitHub repositories via the GitHub REST API.
Requires: GITHUB_TOKEN in .env
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

BASE = "https://api.github.com"


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    url: str
    author: str
    draft: bool
    created_at: str
    labels: list[str] = field(default_factory=list)


@dataclass
class Issue:
    number: int
    title: str
    state: str
    url: str
    author: str
    created_at: str
    labels: list[str] = field(default_factory=list)


class GitHubClient:
    """Thin wrapper around the GitHub REST API."""

    def __init__(self, token: str, default_repo: str = "") -> None:
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.default_repo = default_repo   # "owner/repo"

    # ── Repos ────────────────────────────────────────────────────────────────

    async def list_pull_requests(
        self,
        repo: str = "",
        state: str = "open",
        max_results: int = 10,
    ) -> list[PullRequest]:
        """List pull requests for a repo."""
        repo = repo or self.default_repo
        data = await self._get(
            f"/repos/{repo}/pulls", {"state": state, "per_page": max_results}
        )
        return [
            PullRequest(
                number=pr["number"],
                title=pr["title"],
                state=pr["state"],
                url=pr["html_url"],
                author=pr["user"]["login"],
                draft=pr.get("draft", False),
                created_at=pr["created_at"],
                labels=[lb["name"] for lb in pr.get("labels", [])],
            )
            for pr in data
        ]

    async def list_issues(
        self,
        repo: str = "",
        state: str = "open",
        max_results: int = 10,
    ) -> list[Issue]:
        """List issues for a repo (excludes PRs)."""
        repo = repo or self.default_repo
        data = await self._get(
            f"/repos/{repo}/issues",
            {"state": state, "per_page": max_results},
        )
        return [
            Issue(
                number=item["number"],
                title=item["title"],
                state=item["state"],
                url=item["html_url"],
                author=item["user"]["login"],
                created_at=item["created_at"],
                labels=[lb["name"] for lb in item.get("labels", [])],
            )
            for item in data
            if "pull_request" not in item   # issues endpoint returns PRs too
        ]

    async def create_branch(
        self, repo: str = "", branch: str = "", from_branch: str = "main"
    ) -> str:
        """Create a new branch from an existing one. Returns the new branch SHA."""
        repo = repo or self.default_repo
        ref_data = await self._get(f"/repos/{repo}/git/ref/heads/{from_branch}")
        sha = ref_data["object"]["sha"]
        await self._post(f"/repos/{repo}/git/refs", {
            "ref": f"refs/heads/{branch}",
            "sha": sha,
        })
        logger.info(f"GitHub: created branch {branch!r} from {from_branch!r} in {repo}")
        return sha

    async def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        repo: str = "",
        draft: bool = True,
    ) -> PullRequest:
        """Open a pull request. Defaults to draft so nothing merges without review."""
        repo = repo or self.default_repo
        data = await self._post(f"/repos/{repo}/pulls", {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
            "draft": draft,
        })
        return PullRequest(
            number=data["number"],
            title=data["title"],
            state=data["state"],
            url=data["html_url"],
            author=data["user"]["login"],
            draft=data.get("draft", False),
            created_at=data["created_at"],
        )

    async def read_file(self, path: str, repo: str = "", ref: str = "main") -> str:
        """Read a file from the repo. Returns the decoded text content."""
        import base64
        repo = repo or self.default_repo
        data = await self._get(f"/repos/{repo}/contents/{path}", {"ref": ref})
        return base64.b64decode(data["content"]).decode()

    async def write_file(
        self,
        path: str,
        content: str,
        message: str,
        repo: str = "",
        branch: str = "main",
    ) -> None:
        """Create or update a file in the repo."""
        import base64
        repo = repo or self.default_repo
        encoded = base64.b64encode(content.encode()).decode()

        # Get existing SHA if file already exists (required for updates)
        sha: str | None = None
        try:
            existing = await self._get(
                f"/repos/{repo}/contents/{path}", {"ref": branch}
            )
            sha = existing.get("sha")
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                raise

        payload: dict = {
            "message": message,
            "content": encoded,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        await self._put(f"/repos/{repo}/contents/{path}", payload)
        logger.info(f"GitHub: wrote {path!r} to {repo}/{branch}")

    # ── Private ──────────────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict | None = None) -> dict | list:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BASE}{path}", headers=self._headers, params=params or {}
            )
            resp.raise_for_status()
            return resp.json()

    async def _post(self, path: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{BASE}{path}", headers=self._headers, json=payload
            )
            resp.raise_for_status()
            return resp.json()

    async def _put(self, path: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.put(
                f"{BASE}{path}", headers=self._headers, json=payload
            )
            resp.raise_for_status()
            return resp.json()
