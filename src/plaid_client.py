

from __future__ import annotations

from datetime import date
from typing import List

from .merchant import normalize_descriptor
from .models import Transaction, TxnKind


def from_plaid_transaction(p: dict) -> Transaction:
    """Map a Plaid transaction dict -> our Transaction model.

    Plaid amounts are positive for outflow (purchase) and negative for inflow
    (credit/refund); we normalize to positive `amount` + an explicit `kind`.
    """
    amt = p["amount"]
    kind = TxnKind.PURCHASE if amt > 0 else TxnKind.CREDIT
    raw = (p.get("merchant_name") or p.get("name") or "").strip()
    return Transaction(
        id=p["transaction_id"],
        kind=kind,
        posted_date=date.fromisoformat(p["date"]),
        amount=abs(amt),
        merchant_raw=raw,
        merchant=normalize_descriptor(raw),
        descriptor=p.get("name", ""),
    )


def load_sample_transactions() -> List[Transaction]:
    """Deterministic mock feed for offline testing of the full loop."""
    def tx(tid, kind, d, amt, raw, desc=""):
        return Transaction(tid, kind, date.fromisoformat(d), amt,
                           raw, normalize_descriptor(raw), desc or raw)

    return [
        # Qualifies the Blue Bottle offer; credit posts 9 days later.
        tx("t1", TxnKind.PURCHASE, "2026-06-02", 58.40, "SQ *BLUE BOTTLE 8001234 CA"),
        tx("t2", TxnKind.CREDIT,   "2026-06-11", 10.00, "AMEX OFFER CREDIT BLUE BOTTLE",
           "Amex Offer Credit - Blue Bottle"),
        # Qualifies the Sweetgreen offer; credit never posts -> MISSING.
        tx("t3", TxnKind.PURCHASE, "2026-06-03", 24.10, "TST* SWEETGREEN - MIDTOWN NY"),
        # Below the Nike min spend -> stays PENDING_PURCHASE.
        tx("t4", TxnKind.PURCHASE, "2026-06-05", 42.00, "NIKE #221 PORTLAND OR"),
        # Unrelated noise.
        tx("t5", TxnKind.PURCHASE, "2026-06-06", 7.25, "STARBUCKS #1102 BUFFALO NY"),
    ]
