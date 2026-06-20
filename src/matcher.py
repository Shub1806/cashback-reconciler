
from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, Optional

from .merchant import looks_like_offer_credit, merchant_match
from .models import (
    Offer,
    ReconResult,
    ReconStatus,
    RewardKind,
    Transaction,
    TxnKind,
)

# Default reconciliation parameters. Tune per issuer once you have data.
CREDIT_WINDOW_DAYS = 14     # how long after a purchase a credit may take to post
AMOUNT_TOLERANCE = 0.51     # $ slack between expected and observed credit


def expected_credit(offer: Offer, purchase: Transaction) -> float:
    """Credit the user should receive for a qualifying purchase."""
    if offer.reward_kind is RewardKind.FLAT:
        return round(offer.reward_amount, 2)
    pct = offer.percent or 0.0
    return round(min(purchase.amount * pct, offer.reward_amount), 2)


def find_qualifying_purchase(
    offer: Offer, txns: Iterable[Transaction]
) -> Optional[Transaction]:
    """Earliest purchase that satisfies merchant, date window and min spend."""
    candidates = [
        t for t in txns
        if t.kind is TxnKind.PURCHASE
        and offer.valid_from <= t.posted_date <= offer.valid_to
        and t.amount >= offer.min_spend
        and merchant_match(t.merchant, offer.merchant)
    ]
    return min(candidates, key=lambda t: t.posted_date) if candidates else None


def find_posted_credit(
    offer: Offer,
    purchase: Transaction,
    txns: Iterable[Transaction],
    amount: float,
    window_days: int = CREDIT_WINDOW_DAYS,
    tol: float = AMOUNT_TOLERANCE,
) -> Optional[Transaction]:
    """A statement credit matching the expected amount, after the purchase."""
    deadline = purchase.posted_date + timedelta(days=window_days)
    for t in txns:
        if t.kind is not TxnKind.CREDIT:
            continue
        if not (purchase.posted_date <= t.posted_date <= deadline):
            continue
        if abs(t.amount - amount) > tol:
            continue
        # Accept if it names the merchant OR reads like an offer credit.
        if merchant_match(t.merchant, offer.merchant) or looks_like_offer_credit(t.descriptor):
            return t
    return None


def reconcile(
    offer: Offer,
    txns: Iterable[Transaction],
    as_of: date,
    window_days: int = CREDIT_WINDOW_DAYS,
) -> ReconResult:
    """Resolve one offer against the transaction feed as of a given date."""
    txns = list(txns)
    purchase = find_qualifying_purchase(offer, txns)

    if purchase is None:
        if as_of <= offer.valid_to:
            return ReconResult(offer.id, ReconStatus.PENDING_PURCHASE, as_of,
                               note="Offer active; no qualifying purchase yet.")
        return ReconResult(offer.id, ReconStatus.PENDING_PURCHASE, as_of,
                           note="Offer expired without a qualifying purchase.")

    want = expected_credit(offer, purchase)
    credit = find_posted_credit(offer, purchase, txns, want, window_days)

    if credit is not None:
        return ReconResult(
            offer.id, ReconStatus.POSTED, as_of,
            qualifying_txn_id=purchase.id, expected_credit=want,
            observed_credit_id=credit.id, observed_amount=credit.amount,
            note="Credit posted as expected.", verified=True,
        )

    deadline = purchase.posted_date + timedelta(days=window_days)
    if as_of <= deadline:
        return ReconResult(
            offer.id, ReconStatus.AWAITING_CREDIT, as_of,
            qualifying_txn_id=purchase.id, expected_credit=want,
            note=f"Qualified on {purchase.posted_date}; credit due by {deadline}.",
        )

    return ReconResult(
        offer.id, ReconStatus.MISSING, as_of,
        qualifying_txn_id=purchase.id, expected_credit=want,
        note=f"No credit by {deadline}. You appear to be owed ${want:.2f}.",
        verified=True,
    )
