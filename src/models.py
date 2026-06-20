
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class Issuer(str, Enum):
    AMEX = "amex"
    CHASE = "chase"


class RewardKind(str, Enum):
    FLAT = "flat"        # e.g. "spend $50, get $10"
    PERCENT = "percent"  # e.g. "10% back, up to $15"


class TxnKind(str, Enum):
    PURCHASE = "purchase"
    CREDIT = "credit"    # statement credit (how card-linked offers pay out)


class ReconStatus(str, Enum):
    PENDING_PURCHASE = "pending_purchase"  # offer active, no qualifying spend yet
    AWAITING_CREDIT = "awaiting_credit"    # qualified, still inside posting window
    POSTED = "posted"                      # credit arrived -> promise kept
    MISSING = "missing"                    # window passed, no credit -> you're owed


@dataclass
class Offer:
    """A card-linked offer the user activated, extracted from issuer email."""
    id: str
    issuer: Issuer
    merchant_raw: str                 # as written in the offer
    merchant: str                     # normalized canonical name
    reward_kind: RewardKind
    reward_amount: float              # flat payout, or the cap for percent offers
    valid_from: date
    valid_to: date
    min_spend: float = 0.0
    percent: Optional[float] = None   # e.g. 0.10 for "10% back" (PERCENT only)
    source_email_id: Optional[str] = None


@dataclass
class Transaction:
    """A line from the card statement (purchase or statement credit)."""
    id: str
    kind: TxnKind
    posted_date: date
    amount: float                     # always positive; `kind` carries the sign meaning
    merchant_raw: str
    merchant: str                     # normalized canonical name
    descriptor: str = ""              # raw bank descriptor, kept for credit matching


@dataclass
class ReconResult:
    offer_id: str
    status: ReconStatus
    as_of: date
    qualifying_txn_id: Optional[str] = None
    expected_credit: Optional[float] = None
    observed_credit_id: Optional[str] = None
    observed_amount: Optional[float] = None
    note: str = ""
    # set True once confirmed against real Plaid data (vs. self-reported);
    # the reliability index weights these more heavily.
    verified: bool = False
