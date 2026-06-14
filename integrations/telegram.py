"""
PersonalOS — Telegram Integration
Handles all inbound messages and outbound notifications via the Telegram Bot API.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

import httpx

logger = logging.getLogger(__name__)

MessageHandler = Callable[[str, int], Awaitable[None]]


class TelegramClient:
    """Send messages and receive updates via the Telegram Bot API."""

    BASE = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, token: str, allowed_user_id: int) -> None:
        self.token = token
        self.allowed_user_id = allowed_user_id
        self._offset: int = 0

    # ── Sending ─────────────────────────────────────────────────────────────

    async def send(self, text: str, parse_mode: str = "Markdown") -> None:
        """Send a message to the allowed user."""
        await self._call("sendMessage", {
            "chat_id": self.allowed_user_id,
            "text": text,
            "parse_mode": parse_mode,
        })

    async def send_document(
        self, file_bytes: bytes, filename: str, caption: str = ""
    ) -> None:
        """Send a file to the allowed user."""
        url = self.BASE.format(token=self.token, method="sendDocument")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                data={"chat_id": self.allowed_user_id, "caption": caption},
                files={"document": (filename, file_bytes)},
            )
            resp.raise_for_status()

    # ── Polling ──────────────────────────────────────────────────────────────

    async def poll(self, handler: MessageHandler, timeout: int = 30) -> None:
        """
        Long-poll for updates and call handler(text, user_id) for each message.
        Only processes messages from allowed_user_id — all others are silently dropped.
        """
        updates = await self._call("getUpdates", {
            "offset": self._offset,
            "timeout": timeout,
            "allowed_updates": ["message"],
        })

        for update in updates.get("result", []):
            self._offset = update["update_id"] + 1
            message = update.get("message", {})
            from_id = message.get("from", {}).get("id")

            if from_id != self.allowed_user_id:
                logger.warning(
                    f"Telegram: ignored message from unauthorized user {from_id}"
                )
                continue

            text = message.get("text", "").strip()
            if text:
                await handler(text, from_id)

    # ── Private ──────────────────────────────────────────────────────────────

    async def _call(self, method: str, payload: dict) -> dict:
        url = self.BASE.format(token=self.token, method=method)
        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Telegram API error ({method}): {e}")
            return {}
