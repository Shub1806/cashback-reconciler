"""Local web server for the dashboard.

Runs the reconciliation engine and exposes the result as JSON at /api/state,
and serves the dashboard page at /. Same origin for both, so no CORS setup.

    pip install flask
    python3 server.py
    # then open http://localhost:5000

The offers and transactions below are sample data, standing in until the live
email and Plaid feeds are wired. Everything the dashboard shows is computed by
the real engine, not hard-coded.
"""

from __future__ import annotations

from datetime import date

from flask import Flask, jsonify, send_from_directory

from src.matcher import expected_credit, find_qualifying_purchase, reconcile
from src.merchant import normalize_descriptor
from src.models import Issuer, Offer, ReconStatus, RewardKind, Transaction, TxnKind
from src.reliability import ReliabilityIndex

app = Flask(__name__, static_folder="frontend")

AS_OF = date(2026, 6, 20)


def _tx(tid, kind, d, amt, raw, desc=""):
    return Transaction(tid, kind, date.fromisoformat(d), amt,
                       raw, normalize_descriptor(raw), desc or raw)


TRANSACTIONS = [
    _tx("t1", TxnKind.PURCHASE, "2026-06-02", 31.40, "SQ *BLUE BOTTLE 8001 CA"),
    _tx("t2", TxnKind.CREDIT,   "2026-06-09", 5.00,  "AMEX OFFER CREDIT BLUE BOTTLE",
        "Amex Offer Credit - Blue Bottle"),
    _tx("t3", TxnKind.PURCHASE, "2026-06-03", 22.10, "TST* SWEETGREEN MIDTOWN NY"),
    _tx("t4", TxnKind.PURCHASE, "2026-06-01", 263.00, "DELTA AIR LINES 0061234 GA"),
    _tx("t5", TxnKind.PURCHASE, "2026-06-12", 96.20, "WHOLEFDS MKT #102 BUFFALO NY"),
    _tx("t6", TxnKind.PURCHASE, "2026-06-06", 44.00, "NIKE #221 PORTLAND OR"),
]

OFFERS = [
    Offer("o1", Issuer.AMEX, "Blue Bottle", "blue bottle", RewardKind.FLAT, 5.0,
          date(2026, 6, 1), date(2026, 6, 30), min_spend=25.0),
    Offer("o2", Issuer.AMEX, "Sweetgreen", "sweetgreen", RewardKind.FLAT, 7.0,
          date(2026, 6, 1), date(2026, 6, 30), min_spend=15.0),
    Offer("o3", Issuer.CHASE, "Delta", "delta", RewardKind.FLAT, 40.0,
          date(2026, 6, 1), date(2026, 6, 30), min_spend=200.0),
    Offer("o4", Issuer.AMEX, "Whole Foods", "wholefds mkt", RewardKind.PERCENT, 20.0,
          date(2026, 6, 1), date(2026, 7, 31), min_spend=0.0, percent=0.05),
    Offer("o5", Issuer.CHASE, "Nike", "nike", RewardKind.FLAT, 20.0,
          date(2026, 6, 1), date(2026, 6, 30), min_spend=75.0),
]

STATUS_LABEL = {
    ReconStatus.POSTED: "Posted",
    ReconStatus.MISSING: "Missing",
    ReconStatus.AWAITING_CREDIT: "Awaiting",
    ReconStatus.PENDING_PURCHASE: "Pending",
}


def offer_terms(o: Offer) -> str:
    if o.reward_kind is RewardKind.PERCENT:
        return f"{int((o.percent or 0) * 100)}% back, up to ${o.reward_amount:.0f}"
    if o.min_spend:
        return f"Spend ${o.min_spend:.0f}, get ${o.reward_amount:.0f} back"
    return f"Get ${o.reward_amount:.0f} back"


def _seed_history(idx: ReliabilityIndex) -> None:
    """Accumulated reliability from prior months.

    Placeholder history so the index reads meaningfully on first run. Replace
    with real resolved-offer records once the engine has processed live data.
    """
    history = {"amex": (47, 50), "chase": (41, 46), "citi": (33, 41), "capital one": (28, 39)}
    for issuer, (posted, total) in history.items():
        for i in range(total):
            idx.add(issuer, posted=(i < posted), verified=True)


def build_state() -> dict:
    idx = ReliabilityIndex()
    _seed_history(idx)

    rows = []
    owed_total = 0.0
    owed_count = 0

    for o in OFFERS:
        r = reconcile(o, TRANSACTIONS, as_of=AS_OF)
        amount = None
        if r.status is ReconStatus.POSTED:
            amount = f"+${r.observed_amount:.2f}"
            idx.add(o.issuer.value, posted=True, verified=True)
        elif r.status is ReconStatus.MISSING:
            amount = f"${r.expected_credit:.2f}"
            owed_total += r.expected_credit
            owed_count += 1
            idx.add(o.issuer.value, posted=False, verified=True)
        elif r.status is ReconStatus.AWAITING_CREDIT:
            amount = f"${r.expected_credit:.2f}"

        rows.append({
            "merchant": o.merchant_raw,
            "initial": o.merchant_raw[0].upper(),
            "terms": offer_terms(o),
            "status": STATUS_LABEL[r.status],
            "amount": amount or "—",
        })

    issuer_labels = {"amex": "American Express", "chase": "Chase",
                     "citi": "Citi", "capital one": "Capital One"}
    reliability = []
    for s in idx.leaderboard(min_raw_n=1):
        key = s.key.split(":", 1)[0]
        reliability.append({
            "issuer": issuer_labels.get(key, key.title()),
            "pct": round(s.point * 100),
            "n": s.raw_n,
        })

    return {
        "offers": rows,
        "owed_total": f"${owed_total:.2f}",
        "owed_count": owed_count,
        "reliability": reliability,
    }


@app.route("/api/state")
def state():
    return jsonify(build_state())


@app.route("/")
def home():
    return send_from_directory("frontend", "dashboard.html")


if __name__ == "__main__":
    app.run(port=5000, debug=True)
