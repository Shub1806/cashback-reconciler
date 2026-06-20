

from datetime import date

from src.matcher import reconcile
from src.models import Issuer, Offer, ReconStatus, RewardKind
from src.plaid_client import load_sample_transactions
from src.reliability import ReliabilityIndex

# Normally these come from extract.py parsing your inbox. Hardcoded here.
OFFERS = [
    Offer("o-bb", Issuer.AMEX, "Blue Bottle Coffee", "blue bottle",
          RewardKind.FLAT, 10.0, date(2026, 6, 1), date(2026, 6, 30), min_spend=50.0),
    Offer("o-sg", Issuer.AMEX, "Sweetgreen", "sweetgreen",
          RewardKind.FLAT, 7.0, date(2026, 6, 1), date(2026, 6, 30), min_spend=15.0),
    Offer("o-nk", Issuer.CHASE, "Nike", "nike",
          RewardKind.PERCENT, 20.0, date(2026, 6, 1), date(2026, 6, 30),
          min_spend=75.0, percent=0.10),
]

ICON = {
    ReconStatus.POSTED: "[OK ]",
    ReconStatus.MISSING: "[!! ]",
    ReconStatus.AWAITING_CREDIT: "[...]",
    ReconStatus.PENDING_PURCHASE: "[   ]",
}


def main() -> None:
    txns = load_sample_transactions()
    as_of = date(2026, 6, 20)  # "today" for the demo
    idx = ReliabilityIndex()

    print(f"\nReconciling {len(OFFERS)} offers as of {as_of}\n" + "-" * 60)
    for offer in OFFERS:
        r = reconcile(offer, txns, as_of=as_of)
        print(f"{ICON[r.status]} {offer.merchant_raw:<20} {r.status.value:<17} {r.note}")
        # Only resolved outcomes feed the index.
        if r.status is ReconStatus.POSTED:
            idx.add(offer.issuer.value, posted=True, verified=r.verified)
        elif r.status is ReconStatus.MISSING:
            idx.add(offer.issuer.value, posted=False, verified=r.verified)

    print("\nReliability index (Wilson lower bound = trust score)\n" + "-" * 60)
    for s in idx.leaderboard():
        print(f"  {s.key:<12} posted {s.point:>5.0%}  "
              f"trust {s.low:>5.0%}  (n={s.raw_n})")
    print("\nWith n=1 the trust score stays low on purpose -- it climbs with volume.\n")


if __name__ == "__main__":
    main()
