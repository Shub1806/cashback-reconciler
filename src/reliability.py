

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Tuple

Z = 1.96  # 95% confidence

# Weights for effective sample size.
W_VERIFIED = 1.0
W_SELF_REPORT = 0.3


def wilson_interval(successes: float, n: float, z: float = Z) -> Tuple[float, float, float]:
    """Return (low, point, high) for a Wilson score interval.

    Accepts fractional counts so weighted observations work directly.
    """
    if n <= 0:
        return (0.0, 0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    low = (center - margin) / denom
    high = (center + margin) / denom
    return (max(0.0, low), p, min(1.0, high))


@dataclass
class Score:
    key: str
    n: float            # weighted sample size
    raw_n: int          # number of observations (unweighted)
    point: float        # raw posted rate
    low: float          # Wilson lower bound -- the trust-earning number
    high: float


class ReliabilityIndex:
    """Accumulates posted/missed observations keyed by (issuer, scope)."""

    def __init__(self) -> None:
        # key -> [weighted_successes, weighted_n, raw_n]
        self._acc: Dict[str, list] = defaultdict(lambda: [0.0, 0.0, 0])

    @staticmethod
    def key(issuer: str, scope: str = "all") -> str:
        return f"{issuer}:{scope}"

    def add(self, issuer: str, posted: bool, verified: bool, scope: str = "all") -> None:
        w = W_VERIFIED if verified else W_SELF_REPORT
        acc = self._acc[self.key(issuer, scope)]
        acc[0] += w if posted else 0.0
        acc[1] += w
        acc[2] += 1

    def score(self, issuer: str, scope: str = "all") -> Score:
        k = self.key(issuer, scope)
        succ, n, raw = self._acc[k]
        low, point, high = wilson_interval(succ, n)
        return Score(k, round(n, 2), raw, round(point, 4), round(low, 4), round(high, 4))

    def leaderboard(self, min_raw_n: int = 1) -> list:
        """Issuers ranked by Wilson lower bound (volume-aware trust ranking)."""
        rows = []
        for k in self._acc:
            issuer, scope = k.split(":", 1)
            s = self.score(issuer, scope)
            if s.raw_n >= min_raw_n:
                rows.append(s)
        return sorted(rows, key=lambda s: s.low, reverse=True)
