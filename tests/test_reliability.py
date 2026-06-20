"""Tests for the reliability index + Wilson math."""

from src.reliability import ReliabilityIndex, wilson_interval


def test_wilson_known_value():
    low, point, high = wilson_interval(8, 10)
    assert point == 0.8
    assert round(low, 2) == 0.49
    assert round(high, 2) == 0.94


def test_wilson_small_sample_is_not_overconfident():
    # 3/3 posted should NOT read as a confident 100%.
    low, point, high = wilson_interval(3, 3)
    assert point == 1.0
    assert low < 0.5  # lower bound stays cautious on tiny n


def test_index_tracks_posted_rate():
    idx = ReliabilityIndex()
    for posted in [True, True, True, False]:
        idx.add("amex", posted=posted, verified=True)
    s = idx.score("amex")
    assert s.raw_n == 4
    assert s.point == 0.75
    assert s.low < s.point < s.high


def test_self_reports_weighted_below_verified():
    verified = ReliabilityIndex()
    verified.add("chase", posted=True, verified=True)

    self_rep = ReliabilityIndex()
    self_rep.add("chase", posted=True, verified=False)

    # Same single positive observation, but the verified one carries more weight,
    # so its Wilson lower bound (the trust number) is higher.
    assert verified.score("chase").low > self_rep.score("chase").low


def test_leaderboard_ranks_by_lower_bound():
    idx = ReliabilityIndex()
    for _ in range(20):
        idx.add("amex", posted=True, verified=True)
    for _ in range(18):
        idx.add("chase", posted=True, verified=True)
    for _ in range(2):
        idx.add("chase", posted=False, verified=True)
    board = idx.leaderboard()
    assert [s.key for s in board][0] == "amex:all"  # higher reliability ranks first
