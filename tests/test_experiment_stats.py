"""Statistical correctness of the experiment engine, checked by simulation (seeded)."""

from __future__ import annotations

import numpy as np
import pytest

from flowpilot.experiments.stats import (
    compare,
    detectable_effect,
    holm,
    naive_variance,
    ratio_estimate,
    srm_p_value,
    units_per_arm,
)

RUNS = 2000


def coverage_owner_level(rng: np.random.Generator) -> float:
    hits = 0
    for _ in range(RUNS):
        arms = [rng.binomial(1, 0.38, 2000).astype(np.float64) for _ in range(2)]
        ones = np.ones(2000)
        c = compare("m", ratio_estimate(arms[0], ones), ratio_estimate(arms[1], ones))
        hits += c.ci95[0] <= 0.0 <= c.ci95[1]
    return hits / RUNS


def test_aa_coverage_owner_level() -> None:
    assert 0.935 <= coverage_owner_level(np.random.default_rng(1)) <= 0.965


def clustered_arm(rng: np.random.Generator, units: int) -> tuple[np.ndarray, np.ndarray]:
    """Workspaces with 1-12 users whose retention shares a workspace-level propensity."""
    n = rng.integers(1, 13, units).astype(np.float64)
    propensity = rng.beta(2.0, 3.0, units)
    y = rng.binomial(n.astype(np.int64), propensity).astype(np.float64)
    return y, n


def test_aa_coverage_with_clustered_users_and_naive_undercoverage() -> None:
    rng = np.random.default_rng(2)
    delta_hits = naive_hits = 0
    for _ in range(RUNS):
        (y0, n0), (y1, n1) = clustered_arm(rng, 800), clustered_arm(rng, 800)
        c = compare("m", ratio_estimate(y0, n0), ratio_estimate(y1, n1))
        delta_hits += c.ci95[0] <= 0.0 <= c.ci95[1]
        se_naive = np.sqrt(naive_variance(y0, n0) + naive_variance(y1, n1))
        naive_hits += abs(c.diff) <= 1.959964 * se_naive
    assert 0.935 <= delta_hits / RUNS <= 0.965
    # Ignoring that users of one workspace are correlated gives intervals that are too narrow.
    assert naive_hits / RUNS < 0.85


def test_known_effect_is_recovered() -> None:
    rng = np.random.default_rng(3)
    ones = np.ones(20_000)
    c = compare("m", ratio_estimate(rng.binomial(1, 0.38, 20_000).astype(float), ones),
                ratio_estimate(rng.binomial(1, 0.41, 20_000).astype(float), ones))
    assert c.ci95[0] <= 0.03 <= c.ci95[1]
    assert c.ci95[0] > 0


def test_srm_flags_skewed_split_and_rarely_flags_fair_ones() -> None:
    assert srm_p_value(5250, 4750) < 1e-5
    rng = np.random.default_rng(4)
    fair = [srm_p_value(int(t), 10_000 - int(t)) for t in rng.binomial(10_000, 0.5, 5000)]
    assert np.mean(np.array(fair) < 0.001) < 0.004


def test_holm_matches_textbook_example() -> None:
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert holm([0.5]) == [0.5]


def test_planner_and_detectable_effect_are_consistent() -> None:
    n = units_per_arm(0.38, 0.03)
    assert 4_100 <= n <= 4_200
    assert detectable_effect(0.38, n) == pytest.approx(0.03, rel=0.05)
    assert units_per_arm(0.38, 0.015) > 3.5 * n  # halving the MDE needs about 4x the units
