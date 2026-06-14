"""Tests for integrations/telegram.py"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import respx
from httpx import Response

from integrations.telegram import TelegramClient

TOKEN = "123:test-token"
USER_ID = 42
BASE = f"https://api.telegram.org/bot{TOKEN}"


def tg_ok(result=None) -> dict:
    return {"ok": True, "result": result or []}


@pytest.fixture
def client() -> TelegramClient:
    return TelegramClient(token=TOKEN, allowed_user_id=USER_ID)


# ─── send ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_send_posts_to_sendmessage(client: TelegramClient) -> None:
    route = respx.post(f"{BASE}/sendMessage").mock(return_value=Response(200, json=tg_ok()))

    await client.send("Hello!")

    assert route.called
    body = route.calls[0].request.content
    import json
    payload = json.loads(body)
    assert payload["chat_id"] == USER_ID
    assert payload["text"] == "Hello!"
    assert payload["parse_mode"] == "Markdown"


@pytest.mark.asyncio
@respx.mock
async def test_send_uses_custom_parse_mode(client: TelegramClient) -> None:
    route = respx.post(f"{BASE}/sendMessage").mock(return_value=Response(200, json=tg_ok()))

    await client.send("Hello!", parse_mode="HTML")

    import json
    payload = json.loads(route.calls[0].request.content)
    assert payload["parse_mode"] == "HTML"


@pytest.mark.asyncio
@respx.mock
async def test_send_returns_silently_on_api_error(client: TelegramClient) -> None:
    respx.post(f"{BASE}/sendMessage").mock(return_value=Response(500))

    # Should not raise
    await client.send("Hello!")


# ─── send_document ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_send_document_posts_file(client: TelegramClient) -> None:
    route = respx.post(f"{BASE}/sendDocument").mock(return_value=Response(200, json=tg_ok()))

    await client.send_document(b"file content", "report.pdf", caption="Weekly report")

    assert route.called
    # caption and chat_id are sent as form data
    request = route.calls[0].request
    assert b"report.pdf" in request.content
    assert b"Weekly report" in request.content


# ─── poll ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_poll_calls_handler_for_allowed_user(client: TelegramClient) -> None:
    updates = tg_ok(result=[
        {
            "update_id": 1,
            "message": {
                "text": "Fix the bug",
                "from": {"id": USER_ID},
            },
        }
    ])
    respx.post(f"{BASE}/getUpdates").mock(return_value=Response(200, json=updates))

    handler = AsyncMock()
    await client.poll(handler)

    handler.assert_called_once_with("Fix the bug", USER_ID)


@pytest.mark.asyncio
@respx.mock
async def test_poll_ignores_unauthorized_users(client: TelegramClient) -> None:
    updates = tg_ok(result=[
        {
            "update_id": 2,
            "message": {
                "text": "Hack attempt",
                "from": {"id": 9999},
            },
        }
    ])
    respx.post(f"{BASE}/getUpdates").mock(return_value=Response(200, json=updates))

    handler = AsyncMock()
    await client.poll(handler)

    handler.assert_not_called()


@pytest.mark.asyncio
@respx.mock
async def test_poll_advances_offset(client: TelegramClient) -> None:
    updates = tg_ok(result=[
        {"update_id": 10, "message": {"text": "hi", "from": {"id": USER_ID}}},
        {"update_id": 11, "message": {"text": "hey", "from": {"id": USER_ID}}},
    ])
    respx.post(f"{BASE}/getUpdates").mock(return_value=Response(200, json=updates))

    await client.poll(AsyncMock())

    assert client._offset == 12   # last update_id + 1


@pytest.mark.asyncio
@respx.mock
async def test_poll_skips_empty_text(client: TelegramClient) -> None:
    updates = tg_ok(result=[
        {"update_id": 5, "message": {"text": "   ", "from": {"id": USER_ID}}},
    ])
    respx.post(f"{BASE}/getUpdates").mock(return_value=Response(200, json=updates))

    handler = AsyncMock()
    await client.poll(handler)

    handler.assert_not_called()


@pytest.mark.asyncio
@respx.mock
async def test_poll_handles_empty_update_list(client: TelegramClient) -> None:
    respx.post(f"{BASE}/getUpdates").mock(return_value=Response(200, json=tg_ok(result=[])))

    handler = AsyncMock()
    await client.poll(handler)   # should not raise

    handler.assert_not_called()
