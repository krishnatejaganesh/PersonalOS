"""Tests for integrations/github.py"""

from __future__ import annotations

import base64

import pytest
import respx
from httpx import Response

from integrations.github import GitHubClient, Issue, PullRequest

BASE = "https://api.github.com"
REPO = "owner/repo"


@pytest.fixture
def gh() -> GitHubClient:
    return GitHubClient(token="ghp_test", default_repo=REPO)


def make_pr(number: int = 1, draft: bool = False) -> dict:
    return {
        "number": number,
        "title": f"PR #{number}",
        "state": "open",
        "html_url": f"https://github.com/{REPO}/pull/{number}",
        "user": {"login": "krishna"},
        "draft": draft,
        "created_at": "2026-06-14T00:00:00Z",
        "labels": [],
    }


def make_issue(number: int = 10) -> dict:
    return {
        "number": number,
        "title": f"Issue #{number}",
        "state": "open",
        "html_url": f"https://github.com/{REPO}/issues/{number}",
        "user": {"login": "krishna"},
        "created_at": "2026-06-14T00:00:00Z",
        "labels": [{"name": "bug"}],
    }


# ─── list_pull_requests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_list_prs_returns_pull_request_objects(gh: GitHubClient) -> None:
    respx.get(f"{BASE}/repos/{REPO}/pulls").mock(
        return_value=Response(200, json=[make_pr(1), make_pr(2, draft=True)])
    )

    prs = await gh.list_pull_requests()

    assert len(prs) == 2
    assert prs[0].number == 1
    assert prs[0].draft is False
    assert prs[1].draft is True


@pytest.mark.asyncio
@respx.mock
async def test_list_prs_uses_default_repo(gh: GitHubClient) -> None:
    route = respx.get(f"{BASE}/repos/{REPO}/pulls").mock(
        return_value=Response(200, json=[])
    )

    await gh.list_pull_requests()

    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_list_prs_accepts_explicit_repo(gh: GitHubClient) -> None:
    route = respx.get(f"{BASE}/repos/other/repo/pulls").mock(
        return_value=Response(200, json=[])
    )

    await gh.list_pull_requests(repo="other/repo")

    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_list_prs_maps_labels(gh: GitHubClient) -> None:
    pr = make_pr(1)
    pr["labels"] = [{"name": "bug"}, {"name": "urgent"}]
    respx.get(f"{BASE}/repos/{REPO}/pulls").mock(
        return_value=Response(200, json=[pr])
    )

    prs = await gh.list_pull_requests()

    assert prs[0].labels == ["bug", "urgent"]


# ─── list_issues ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_list_issues_excludes_pull_requests(gh: GitHubClient) -> None:
    issue = make_issue(10)
    pr_as_issue = {**make_issue(11), "pull_request": {"url": "..."}}
    respx.get(f"{BASE}/repos/{REPO}/issues").mock(
        return_value=Response(200, json=[issue, pr_as_issue])
    )

    issues = await gh.list_issues()

    assert len(issues) == 1
    assert issues[0].number == 10


@pytest.mark.asyncio
@respx.mock
async def test_list_issues_maps_labels(gh: GitHubClient) -> None:
    respx.get(f"{BASE}/repos/{REPO}/issues").mock(
        return_value=Response(200, json=[make_issue(1)])
    )

    issues = await gh.list_issues()

    assert issues[0].labels == ["bug"]


# ─── create_branch ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_create_branch_returns_sha(gh: GitHubClient) -> None:
    sha = "abc123"
    respx.get(f"{BASE}/repos/{REPO}/git/ref/heads/main").mock(
        return_value=Response(200, json={"object": {"sha": sha}})
    )
    respx.post(f"{BASE}/repos/{REPO}/git/refs").mock(
        return_value=Response(201, json={})
    )

    result = await gh.create_branch(branch="feature/new")

    assert result == sha


@pytest.mark.asyncio
@respx.mock
async def test_create_branch_posts_correct_ref(gh: GitHubClient) -> None:
    respx.get(f"{BASE}/repos/{REPO}/git/ref/heads/main").mock(
        return_value=Response(200, json={"object": {"sha": "deadbeef"}})
    )
    route = respx.post(f"{BASE}/repos/{REPO}/git/refs").mock(
        return_value=Response(201, json={})
    )

    await gh.create_branch(branch="fix/bug")

    import json
    payload = json.loads(route.calls[0].request.content)
    assert payload["ref"] == "refs/heads/fix/bug"
    assert payload["sha"] == "deadbeef"


# ─── create_pull_request ─────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_create_pr_returns_pull_request(gh: GitHubClient) -> None:
    respx.post(f"{BASE}/repos/{REPO}/pulls").mock(
        return_value=Response(201, json=make_pr(42, draft=True))
    )

    pr = await gh.create_pull_request(
        title="Fix login bug",
        body="Closes #10",
        head="fix/login",
    )

    assert pr.number == 42
    assert pr.draft is True


@pytest.mark.asyncio
@respx.mock
async def test_create_pr_defaults_to_draft(gh: GitHubClient) -> None:
    route = respx.post(f"{BASE}/repos/{REPO}/pulls").mock(
        return_value=Response(201, json=make_pr(1, draft=True))
    )

    await gh.create_pull_request(title="t", body="b", head="branch")

    import json
    payload = json.loads(route.calls[0].request.content)
    assert payload["draft"] is True


# ─── read_file ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_read_file_decodes_base64_content(gh: GitHubClient) -> None:
    content = "print('hello')"
    encoded = base64.b64encode(content.encode()).decode()
    respx.get(f"{BASE}/repos/{REPO}/contents/main.py").mock(
        return_value=Response(200, json={"content": encoded})
    )

    result = await gh.read_file("main.py")

    assert result == content


# ─── write_file ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_write_file_creates_new_file(gh: GitHubClient) -> None:
    # 404 means file doesn't exist yet
    respx.get(f"{BASE}/repos/{REPO}/contents/new.py").mock(
        return_value=Response(404, json={"message": "Not Found"})
    )
    route = respx.put(f"{BASE}/repos/{REPO}/contents/new.py").mock(
        return_value=Response(201, json={})
    )

    await gh.write_file("new.py", "content", "add new.py")

    import json
    payload = json.loads(route.calls[0].request.content)
    assert "sha" not in payload
    assert payload["message"] == "add new.py"


@pytest.mark.asyncio
@respx.mock
async def test_write_file_includes_sha_when_updating(gh: GitHubClient) -> None:
    existing_sha = "existing-sha-123"
    respx.get(f"{BASE}/repos/{REPO}/contents/existing.py").mock(
        return_value=Response(200, json={"sha": existing_sha, "content": ""})
    )
    route = respx.put(f"{BASE}/repos/{REPO}/contents/existing.py").mock(
        return_value=Response(200, json={})
    )

    await gh.write_file("existing.py", "updated content", "update existing.py")

    import json
    payload = json.loads(route.calls[0].request.content)
    assert payload["sha"] == existing_sha


@pytest.mark.asyncio
@respx.mock
async def test_write_file_encodes_content_as_base64(gh: GitHubClient) -> None:
    respx.get(f"{BASE}/repos/{REPO}/contents/file.py").mock(
        return_value=Response(404, json={})
    )
    route = respx.put(f"{BASE}/repos/{REPO}/contents/file.py").mock(
        return_value=Response(201, json={})
    )

    await gh.write_file("file.py", "hello world", "msg")

    import json
    payload = json.loads(route.calls[0].request.content)
    decoded = base64.b64decode(payload["content"]).decode()
    assert decoded == "hello world"
