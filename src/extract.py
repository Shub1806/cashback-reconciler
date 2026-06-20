
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from .llm import chat
from .models import Issuer, Offer, RewardKind

SYSTEM_PROMPT = """Extract a single card-linked cashback offer from an issuer email.
Return ONLY a JSON object, no prose, no markdown fences, with these fields:

  issuer:        "amex" or "chase"
  merchant:      clean canonical merchant name (e.g. "Blue Bottle Coffee")
  reward_kind:   "flat" for "spend $X get $Y", "percent" for "Z% back up to $Y"
  reward_amount: number -- the flat payout, or the cap for percent offers
  percent:       number 0-1 for percent offers (e.g. 0.10), else null
  min_spend:     number -- minimum qualifying spend, 0 if none
  valid_from:    "YYYY-MM-DD"
  valid_to:      "YYYY-MM-DD" -- the offer expiration / use-by date

Rules:
- If the email is not a card-linked offer, return {"is_offer": false}.
- Never invent values. If a field is genuinely absent, use null (or 0 for min_spend).
- "up to $X" with a percent => reward_kind "percent", reward_amount = X (the cap)."""


def extract_offer_from_email(email_text: str, offer_id: str,
                             source_email_id: Optional[str] = None) -> Optional[Offer]:
    """Parse one email into an Offer, or None if it isn't an offer email."""
    raw = chat(SYSTEM_PROMPT, email_text, max_tokens=512)
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(raw)
    if data.get("is_offer") is False:
        return None
    return _to_offer(data, offer_id, source_email_id)


def _to_offer(d: dict, offer_id: str, source_email_id: Optional[str]) -> Offer:
    def _d(s: str) -> date:
        return datetime.strptime(s, "%Y-%m-%d").date()

    return Offer(
        id=offer_id,
        issuer=Issuer(d["issuer"]),
        merchant_raw=d["merchant"],
        merchant=d["merchant"],
        reward_kind=RewardKind(d["reward_kind"]),
        reward_amount=float(d["reward_amount"]),
        percent=(float(d["percent"]) if d.get("percent") is not None else None),
        min_spend=float(d.get("min_spend") or 0.0),
        valid_from=_d(d["valid_from"]),
        valid_to=_d(d["valid_to"]),
        source_email_id=source_email_id,
    )
