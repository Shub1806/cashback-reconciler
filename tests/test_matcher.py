"""Tests for the reconciliation matcher -- one per status outcome."""

from datetime import date

from src.matcher import expected_credit, reconcile
from src.models import (
    Issuer,
    Offer,
    ReconStatus,
    RewardKind,
    Transaction,
    TxnKind,
)
from src.merchant import normalize_descriptor


def _offer(**kw):
    base = dict(
        id="o1", issuer=Issuer.AMEX, merchant_raw="Blue Bottle Coffee",
        merchant="blue bottle", reward_kind=RewardKind.FLAT, reward_amount=10.0,
        min_spend=50.0, valid_from=date(2026, 6, 1), valid_to=date(2026, 6, 30),
    )
    base.update(kw)
    return Offer(**base)


def _tx(tid, kind, d, amt, raw, desc=""):
    return Transaction(tid, kind, date.fromisoformat(d), amt,
                       raw, normalize_descriptor(raw), desc or raw)


def test_posted_when_credit_arrives_in_window():
    offer = _offer()
    txns = [
        _tx("p", TxnKind.PURCHASE, "2026-06-02", 58.40, "SQ *BLUE BOTTLE 8001234 CA"),
        _tx("c", TxnKind.CREDIT, "2026-06-11", 10.00, "AMEX OFFER CREDIT BB",
            "Amex Offer Credit Blue Bottle"),
    ]
    r = reconcile(offer, txns, as_of=date(2026, 6, 20))
    assert r.status is ReconStatus.POSTED
    assert r.observed_amount == 10.00
    assert r.verified is True


def test_missing_when_window_passes_without_credit():
    offer = _offer()
    txns = [_tx("p", TxnKind.PURCHASE, "2026-06-02", 58.40, "SQ *BLUE BOTTLE CA")]
    r = reconcile(offer, txns, as_of=date(2026, 6, 25))  # > 14 days after purchase
    assert r.status is ReconStatus.MISSING
    assert r.expected_credit == 10.00
    assert "owed" in r.note


def test_awaiting_credit_inside_window():
    offer = _offer()
    txns = [_tx("p", TxnKind.PURCHASE, "2026-06-02", 58.40, "SQ *BLUE BOTTLE CA")]
    r = reconcile(offer, txns, as_of=date(2026, 6, 10))  # still within 14 days
    assert r.status is ReconStatus.AWAITING_CREDIT


def test_pending_when_below_min_spend():
    offer = _offer(min_spend=80.0)
    txns = [_tx("p", TxnKind.PURCHASE, "2026-06-02", 58.40, "SQ *BLUE BOTTLE CA")]
    r = reconcile(offer, txns, as_of=date(2026, 6, 10))
    assert r.status is ReconStatus.PENDING_PURCHASE


def test_percent_offer_caps_at_reward_amount():
    offer = _offer(reward_kind=RewardKind.PERCENT, percent=0.10, reward_amount=15.0,
                   min_spend=0.0)
    cheap = _tx("a", TxnKind.PURCHASE, "2026-06-02", 80.0, "Blue Bottle")
    pricey = _tx("b", TxnKind.PURCHASE, "2026-06-02", 300.0, "Blue Bottle")
    assert expected_credit(offer, cheap) == 8.00     # 10% of 80
    assert expected_credit(offer, pricey) == 15.00   # capped


def test_wrong_merchant_does_not_qualify():
    offer = _offer()
    txns = [_tx("p", TxnKind.PURCHASE, "2026-06-02", 99.0, "STARBUCKS #1 BUFFALO NY")]
    r = reconcile(offer, txns, as_of=date(2026, 6, 25))
    assert r.status is ReconStatus.PENDING_PURCHASE
