"""Hinweise bei Regimewechsel (D3). Kanaele: ntfy.sh (kostenlos, ohne Konto, App oder Browser) und E-Mail per SMTP
(etwa ein eigenes Gmail-Konto mit App-Passwort). Beide optional, konfiguriert in backend/.env."""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

import httpx

from . import store
from .config import get_settings
from .explain.base import ssl_context

TAGS = {"zone": "traffic_light", "phase": "arrows_counterclockwise", "regime": "warning", "confirmation": "handshake", "veto": "no_entry"}


def format_events(events: list[dict]) -> tuple[str, str]:
    """(Titel, Text) fuer eine Nachricht, laienverstaendlich und kompakt."""
    if len(events) == 1:
        e = events[0]
        return f"MacroPilot: {e['title']}", f"{e['detail']}\n\nStand {e['date']}."
    lines = [f"- {e['title']}: {e['detail']}" for e in events]
    return f"MacroPilot: {len(events)} Änderungen", "\n".join(lines) + f"\n\nStand {events[-1]['date']}."


async def send_ntfy(title: str, text: str, tags: list[str]) -> None:
    s = get_settings()
    url = f"{s.ntfy_server.rstrip('/')}/{s.ntfy_topic}"
    headers = {"Title": title.encode("ascii", "replace").decode(), "Tags": ",".join(tags[:3]) or "chart_with_upwards_trend", "Priority": "default"}
    async with httpx.AsyncClient(timeout=20.0, verify=ssl_context()) as client:
        r = await client.post(url, content=text.encode("utf-8"), headers=headers)
        r.raise_for_status()


def _send_email_sync(title: str, text: str) -> None:
    s = get_settings()
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = s.alert_email_from or s.smtp_user or ""
    msg["To"] = s.alert_email_to or ""
    msg.set_content(text)
    with smtplib.SMTP(s.smtp_host or "", s.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        if s.smtp_user and s.smtp_password:
            smtp.login(s.smtp_user, s.smtp_password)
        smtp.send_message(msg)


def configured_channels() -> list[str]:
    s = get_settings()
    out = []
    if s.ntfy_topic:
        out.append("ntfy")
    if s.smtp_host and s.alert_email_to:
        out.append("email")
    return out


async def send_pending() -> dict:
    """Verschickt alle noch nicht gemeldeten Ereignisse ueber jeden konfigurierten Kanal.
    Ohne Kanal bleiben sie ungemeldet (und erscheinen nur in der Aenderungsliste)."""
    events = store.unnotified_events()
    channels = configured_channels()
    if not events or not channels:
        return {"events": len(events), "sent": [], "failed": []}
    title, text = format_events(events)
    tags = sorted({TAGS.get(e["kind"], "bell") for e in events})
    sent, failed = [], []
    for ch in channels:
        try:
            if ch == "ntfy":
                await send_ntfy(title, text, tags)
            else:
                await asyncio.to_thread(_send_email_sync, title, text)
            sent.append(ch)
        except Exception as exc:  # noqa: BLE001 - ein toter Kanal darf den Refresh nicht stoppen
            failed.append(f"{ch}: {exc}")
    if sent:
        store.mark_notified(e["id"] for e in events)
    return {"events": len(events), "sent": sent, "failed": failed}
