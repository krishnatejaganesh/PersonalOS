"""
PersonalOS — Google Workspace Integration
Provides read/write access to Gmail and Google Calendar via the Google REST APIs.
Requires: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN in .env
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"


@dataclass
class Email:
    id: str
    subject: str
    sender: str
    snippet: str
    date: str
    is_unread: bool


@dataclass
class CalendarEvent:
    id: str
    title: str
    start: str
    end: str
    location: str
    description: str
    attendees: list[str]


class GoogleWorkspace:
    """Thin wrapper around Gmail and Google Calendar REST APIs."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self._access_token: str | None = None

    # ── Auth ────────────────────────────────────────────────────────────────

    async def _get_access_token(self) -> str:
        """Exchange refresh token for a short-lived access token."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(TOKEN_URL, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            })
            resp.raise_for_status()
            self._access_token = resp.json()["access_token"]
        return self._access_token

    async def _headers(self) -> dict[str, str]:
        token = await self._get_access_token()
        return {"Authorization": f"Bearer {token}"}

    # ── Gmail ────────────────────────────────────────────────────────────────

    async def list_emails(
        self,
        query: str = "is:unread",
        max_results: int = 10,
    ) -> list[Email]:
        """List emails matching a Gmail search query."""
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GMAIL_BASE}/messages",
                headers=headers,
                params={"q": query, "maxResults": max_results},
            )
            resp.raise_for_status()
            message_ids = [m["id"] for m in resp.json().get("messages", [])]

        emails: list[Email] = []
        for msg_id in message_ids:
            email = await self._get_email(msg_id, headers)
            if email:
                emails.append(email)
        return emails

    async def _get_email(self, msg_id: str, headers: dict) -> Email | None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{GMAIL_BASE}/messages/{msg_id}",
                    headers=headers,
                    params={
                        "format": "metadata",
                        "metadataHeaders": ["Subject", "From", "Date"],
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            header_map = {
                h["name"]: h["value"]
                for h in data.get("payload", {}).get("headers", [])
            }
            labels = data.get("labelIds", [])
            return Email(
                id=msg_id,
                subject=header_map.get("Subject", "(no subject)"),
                sender=header_map.get("From", ""),
                snippet=data.get("snippet", ""),
                date=header_map.get("Date", ""),
                is_unread="UNREAD" in labels,
            )
        except Exception as e:
            logger.warning(f"GoogleWorkspace: failed to fetch email {msg_id}: {e}")
            return None

    async def create_draft(self, to: str, subject: str, body: str) -> str:
        """Create a Gmail draft. Returns the draft ID."""
        import base64
        from email.mime.text import MIMEText

        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        headers = await self._headers()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{GMAIL_BASE}/drafts",
                headers=headers,
                json={"message": {"raw": raw}},
            )
            resp.raise_for_status()
            return resp.json()["id"]

    # ── Calendar ─────────────────────────────────────────────────────────────

    async def list_events(
        self,
        calendar_id: str = "primary",
        days_ahead: int = 1,
    ) -> list[CalendarEvent]:
        """List calendar events for the next N days."""
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        time_max = now.replace(day=now.day + days_ahead).isoformat()

        headers = await self._headers()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{CALENDAR_BASE}/calendars/{calendar_id}/events",
                headers=headers,
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                },
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])

        return [
            CalendarEvent(
                id=item["id"],
                title=item.get("summary", "(no title)"),
                start=item.get("start", {}).get(
                    "dateTime", item.get("start", {}).get("date", "")
                ),
                end=item.get("end", {}).get(
                    "dateTime", item.get("end", {}).get("date", "")
                ),
                location=item.get("location", ""),
                description=item.get("description", ""),
                attendees=[
                    a.get("email", "") for a in item.get("attendees", [])
                ],
            )
            for item in items
        ]
