"""
Amplifier agent integration endpoints.
Proxies to the Amplifier relay server (DO droplet) so the frontend never
calls the relay directly (avoids CORS, hides the auth token from the browser).
"""

import os
import logging
import httpx
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user

log = logging.getLogger(__name__)
router = APIRouter()

RELAY_URL = os.getenv("AMPLIFIER_RELAY_URL", "http://167.99.185.34:8080")
RELAY_KEY = os.getenv("AMPLIFIER_RELAY_KEY", "")

def _relay_headers() -> dict:
    return {"Authorization": f"Bearer {RELAY_KEY}"}


class BriefingResponse(BaseModel):
    status: str
    message: str


class DailyNoteResponse(BaseModel):
    date: str
    content: str | None
    found: bool
    holmes_section: str | None = None


def _extract_holmes_section(content: str) -> str | None:
    """Pull out the Holmes dossier block from the daily note if present."""
    if not content:
        return None
    markers = ["HOLMES DAILY DOSSIER", "## Holmes", "Holmes Daily"]
    for marker in markers:
        idx = content.find(marker)
        if idx != -1:
            # Take from the marker to the next major section (--- or ##)
            chunk = content[idx:]
            end = len(chunk)
            for delimiter in ["\n\n---", "\n## ", "\n# "]:
                pos = chunk.find(delimiter, 100)  # skip first 100 chars
                if pos != -1 and pos < end:
                    end = pos
            return chunk[:end].strip()
    return None


@router.post("/holmes-briefing", response_model=BriefingResponse)
async def trigger_holmes_briefing(user=Depends(get_verified_user)):
    """Trigger the Holmes morning intelligence scan."""
    if not RELAY_KEY:
        raise HTTPException(status_code=503, detail="AMPLIFIER_RELAY_KEY not configured")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{RELAY_URL}/amplifier/holmes-brief",
                headers=_relay_headers(),
            )
        if resp.status_code in (200, 202):
            return BriefingResponse(status="accepted", message="Holmes is running the intelligence scan. Check back in 2-3 minutes.")
        raise HTTPException(status_code=resp.status_code, detail=f"Relay error: {resp.text[:200]}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Relay timed out — Holmes may still be running.")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Cannot reach relay: {e}")


@router.get("/daily-note", response_model=DailyNoteResponse)
async def get_daily_note(user=Depends(get_verified_user)):
    """Fetch today's daily note and extract the Holmes section if present."""
    if not RELAY_KEY:
        raise HTTPException(status_code=503, detail="AMPLIFIER_RELAY_KEY not configured")
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.get(
                f"{RELAY_URL}/amplifier/daily-note",
                headers=_relay_headers(),
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"Relay error: {resp.text[:200]}")
        data = resp.json()
        content = data.get("content")
        return DailyNoteResponse(
            date=data.get("date", date.today().isoformat()),
            content=content,
            found=data.get("found", False),
            holmes_section=_extract_holmes_section(content) if content else None,
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Relay timed out.")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Cannot reach relay: {e}")
