
from __future__ import annotations

import re
from difflib import SequenceMatcher

# Payment-processor / aggregator prefixes that prepend the real merchant name.
_PREFIXES = [
    "sq *", "sq*", "tst*", "tst *", "pp*", "pp *", "paypal *", "pyp*", "pyp *",
    "sp *", "sp*", "ec*", "wl *", "in *", "googl*", "google *", "amzn mktp",
    "amazon mktp", "uber *", "doordash*", "dd *",
]

# Generic noise tokens to drop after prefix removal.
_NOISE_TOKENS = {
    "llc", "inc", "co", "corp", "ltd", "the", "com", "usa", "us",
    "store", "purchase", "payment", "pos", "debit", "online",
}

# US state codes that often trail a descriptor as a location tag.
_STATE_CODES = {
    "al","ak","az","ar","ca","co","ct","de","fl","ga","hi","id","il","in",
    "ia","ks","ky","la","me","md","ma","mi","mn","ms","mo","mt","ne","nv",
    "nh","nj","nm","ny","nc","nd","oh","ok","or","pa","ri","sc","sd","tn",
    "tx","ut","vt","va","wa","wv","wi","wy",
}

# Descriptor fragments that signal a statement credit from a card-linked offer.
_CREDIT_HINTS = (
    "offer credit", "statement credit", "amex offer", "chase offer",
    "cash back", "cashback", "reward", "credit adjustment",
)


def normalize_descriptor(raw: str) -> str:
    """Reduce a raw merchant/descriptor string to a canonical lowercase name."""
    s = raw.lower().strip()

    # Strip a leading processor prefix (longest match first).
    for p in sorted(_PREFIXES, key=len, reverse=True):
        if s.startswith(p):
            s = s[len(p):].strip()
            break

    # Drop store numbers (#1234) and long digit runs (phone/order ids).
    s = re.sub(r"#\s*\d+", " ", s)
    s = re.sub(r"\b\d{3,}\b", " ", s)

    # Replace remaining punctuation with spaces, collapse whitespace.
    s = re.sub(r"[^a-z0-9]+", " ", s)
    tokens = [t for t in s.split() if t]

    # Trim a trailing state code, then drop noise tokens and bare digits.
    if tokens and tokens[-1] in _STATE_CODES:
        tokens = tokens[:-1]
    tokens = [t for t in tokens if t not in _NOISE_TOKENS and not t.isdigit()]

    return " ".join(tokens).strip()


def similarity(a: str, b: str) -> float:
    """Normalized similarity in [0, 1] between two already-normalized names."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    # Token containment short-circuit: "blue bottle" vs "blue bottle coffee".
    ta, tb = set(a.split()), set(b.split())
    if ta and tb and (ta <= tb or tb <= ta):
        return max(0.9, SequenceMatcher(None, a, b).ratio())
    return SequenceMatcher(None, a, b).ratio()


def merchant_match(a_raw: str, b_raw: str, threshold: float = 0.82) -> bool:
    """True if two raw merchant strings refer to the same merchant."""
    return similarity(normalize_descriptor(a_raw), normalize_descriptor(b_raw)) >= threshold


def looks_like_offer_credit(descriptor: str) -> bool:
    """Heuristic: does this descriptor read like a card-linked offer payout?"""
    d = descriptor.lower()
    return any(h in d for h in _CREDIT_HINTS)
