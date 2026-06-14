"""Tests for integrations/google_workspace.py"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from integrations.google_workspace import CalendarEvent, Email, GoogleWorkspace

TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"
ACCESS_TOKEN = "ya29.test-access-token"


@pytest.fixture
def gws() -> GoogleWorkspace:
    return GoogleWorkspace(
        client_id="client-id",
        client_secret="client-secret",
        refresh_token="refresh-token",
    )


def mock_token() -> None:
    respx.post(TOKEN_URL).mock(
        return_value=Response(200, json={"access_token": ACCESS_TOKEN})
    )


def auth_header() -> dict:
    return {"Authorization": f"Bearer {ACCESS_TOKEN}"}


def make_message_list(*msg_ids: str) -> dict:
    return {"messages": [{"id": mid} for mid in msg_ids]}


def make_message(
    msg_id: str,
    subject: str = "Test subject",
    sender: str = "sender@example.com",
    snippet: str = "email snippet",
    unread: bool = True,
) -> dict:
    return {
        "id": msg_id,
        "snippet": snippet,
        "labelIds": ["UNREAD", "INBOX"] if unread else ["INBOX"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
                {"name": "Date", "value": "Mon, 14 Jun 2026 08:00:00 +0000"},
            ]
        },
    }


# ─── Auth ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_get_access_token_exchanges_refresh_token(gws: GoogleWorkspace) -> None:
    mock_token()

    token = await gws._get_access_token()

    assert token == ACCESS_TOKEN
    assert gws._access_token == ACCESS_TOKEN


@pytest.mark.asyncio
@respx.mock
async def test_headers_include_bearer_token(gws: GoogleWorkspace) -> None:
    mock_token()

    headers = await gws._headers()

    assert headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"


# ─── list_emails ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_list_emails_returns_email_objects(gws: GoogleWorkspace) -> None:
    mock_token()
    respx.get(f"{GMAIL_BASE}/messages").mock(
        return_value=Response(200, json=make_message_list("msg1", "msg2"))
    )
    respx.get(f"{GMAIL_BASE}/messages/msg1").mock(
        return_value=Response(200, json=make_message("msg1", subject="Hello"))
    )
    respx.get(f"{GMAIL_BASE}/messages/msg2").mock(
        return_value=Response(200, json=make_message("msg2", subject="World", unread=False))
    )

    emails = await gws.list_emails()

    assert len(emails) == 2
    assert emails[0].subject == "Hello"
    assert emails[0].is_unread is True
    assert emails[1].subject == "World"
    assert emails[1].is_unread is False


@pytest.mark.asyncio
@respx.mock
async def test_list_emails_returns_empty_when_no_messages(gws: GoogleWorkspace) -> None:
    mock_token()
    respx.get(f"{GMAIL_BASE}/messages").mock(
        return_value=Response(200, json={})
    )

    emails = await gws.list_emails()

    assert emails == []


@pytest.mark.asyncio
@respx.mock
async def test_list_emails_skips_failed_message_fetch(gws: GoogleWorkspace) -> None:
    mock_token()
    respx.get(f"{GMAIL_BASE}/messages").mock(
        return_value=Response(200, json=make_message_list("ok", "bad"))
    )
    respx.get(f"{GMAIL_BASE}/messages/ok").mock(
        return_value=Response(200, json=make_message("ok", subject="Fine"))
    )
    respx.get(f"{GMAIL_BASE}/messages/bad").mock(
        return_value=Response(500)
    )

    emails = await gws.list_emails()

    assert len(emails) == 1
    assert emails[0].id == "ok"


@pytest.mark.asyncio
@respx.mock
async def test_list_emails_uses_no_subject_fallback(gws: GoogleWorkspace) -> None:
    mock_token()
    respx.get(f"{GMAIL_BASE}/messages").mock(
        return_value=Response(200, json=make_message_list("msg1"))
    )
    # Message with no Subject header
    respx.get(f"{GMAIL_BASE}/messages/msg1").mock(
        return_value=Response(200, json={
            "id": "msg1",
            "snippet": "...",
            "labelIds": [],
            "payload": {"headers": []},
        })
    )

    emails = await gws.list_emails()

    assert emails[0].subject == "(no subject)"


# ─── create_draft ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_create_draft_returns_draft_id(gws: GoogleWorkspace) -> None:
    mock_token()
    respx.post(f"{GMAIL_BASE}/drafts").mock(
        return_value=Response(200, json={"id": "draft-abc"})
    )

    draft_id = await gws.create_draft(
        to="recipient@example.com",
        subject="Meeting follow-up",
        body="Hi, just following up...",
    )

    assert draft_id == "draft-abc"


@pytest.mark.asyncio
@respx.mock
async def test_create_draft_sends_base64_encoded_message(gws: GoogleWorkspace) -> None:
    mock_token()
    route = respx.post(f"{GMAIL_BASE}/drafts").mock(
        return_value=Response(200, json={"id": "draft-xyz"})
    )

    await gws.create_draft("a@b.com", "Subject", "Body text")

    import json
    payload = json.loads(route.calls[0].request.content)
    assert "message" in payload
    assert "raw" in payload["message"]
    # raw should be non-empty base64
    assert len(payload["message"]["raw"]) > 0


# ─── list_events ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_list_events_returns_calendar_events(gws: GoogleWorkspace) -> None:
    mock_token()
    respx.get(f"{CALENDAR_BASE}/calendars/primary/events").mock(
        return_value=Response(200, json={"items": [
            {
                "id": "evt1",
                "summary": "Team standup",
                "start": {"dateTime": "2026-06-14T09:00:00Z"},
                "end": {"dateTime": "2026-06-14T09:30:00Z"},
                "location": "Zoom",
                "description": "Daily sync",
                "attendees": [{"email": "alice@example.com"}],
            }
        ]})
    )

    events = await gws.list_events()

    assert len(events) == 1
    assert events[0].title == "Team standup"
    assert events[0].start == "2026-06-14T09:00:00Z"
    assert events[0].location == "Zoom"
    assert events[0].attendees == ["alice@example.com"]


@pytest.mark.asyncio
@respx.mock
async def test_list_events_uses_date_fallback_for_all_day_events(gws: GoogleWorkspace) -> None:
    mock_token()
    respx.get(f"{CALENDAR_BASE}/calendars/primary/events").mock(
        return_value=Response(200, json={"items": [
            {
                "id": "evt2",
                "summary": "All-day event",
                "start": {"date": "2026-06-14"},
                "end": {"date": "2026-06-15"},
            }
        ]})
    )

    events = await gws.list_events()

    assert events[0].start == "2026-06-14"
    assert events[0].end == "2026-06-15"


@pytest.mark.asyncio
@respx.mock
async def test_list_events_returns_empty_when_no_items(gws: GoogleWorkspace) -> None:
    mock_token()
    respx.get(f"{CALENDAR_BASE}/calendars/primary/events").mock(
        return_value=Response(200, json={"items": []})
    )

    events = await gws.list_events()

    assert events == []


@pytest.mark.asyncio
@respx.mock
async def test_list_events_uses_no_title_fallback(gws: GoogleWorkspace) -> None:
    mock_token()
    respx.get(f"{CALENDAR_BASE}/calendars/primary/events").mock(
        return_value=Response(200, json={"items": [
            {"id": "e", "start": {"date": "2026-06-14"}, "end": {"date": "2026-06-14"}}
        ]})
    )

    events = await gws.list_events()

    assert events[0].title == "(no title)"
