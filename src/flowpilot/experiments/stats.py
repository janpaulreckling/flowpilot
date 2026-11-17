"""Statistics for experiment analysis (docs/EXPERIMENTS.md). Pure functions, no I/O.

Each unit (workspace) contributes an outcome sum y and a user count n. The arm's rate is
sum(y) / sum(n); its variance comes from the delta method for a ratio of means, which stays
correct when several users of one workspace are correlated. With n = 1 for every unit it
reduces to the familiar p(1-p)/m.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel
from scipy import stats

Z95 = float(stats.norm.ppf(0.975))
Z90 = float(stats.norm.ppf(0.95))


class ArmEstimate(BaseModel):
    units: int
    users: int
    rate: float
    variance: float


class Comparison(BaseModel):
    metric: str
    control: ArmEstimate
    treatment: ArmEstimate
    diff: float  # treatment - control, absolute (rate units; x100 = percentage points)
    rel_diff: float | None  # diff / control rate
    se: float
    ci95: tuple[float, float]
    ci90: tuple[float, float]
    p_two_sided: float
    p_harm: float  # one-sided p-value for "treatment is worse" (higher is better)


def ratio_estimate(y: NDArray[np.float64], n: NDArray[np.float64]) -> ArmEstimate:
    """Delta-method estimate of sum(y)/sum(n) and its variance over independent units."""
    m = y.size
    if m < 2 or n.sum() == 0:
        raise ValueError("need at least two units with users")
    mean_y, mean_n = float(y.mean()), float(n.mean())
    r = mean_y / mean_n
    var_y = float(y.var(ddof=1))
    var_n = float(n.var(ddof=1))
    cov_yn = float(np.cov(y, n, ddof=1)[0, 1]) if var_n > 0 else 0.0
    variance = (var_y - 2 * r * cov_yn + r * r * var_n) / (m * mean_n**2)
    return ArmEstimate(units=m, users=int(n.sum()), rate=r, variance=max(variance, 0.0))


def naive_variance(y: NDArray[np.float64], n: NDArray[np.float64]) -> float:
    """Per-user binomial variance that ignores clustering (shown only for comparison)."""
    p = float(y.sum() / n.sum())
    return p * (1 - p) / float(n.sum())


def compare(metric: str, control: ArmEstimate, treatment: ArmEstimate) -> Comparison:
    diff = treatment.rate - control.rate
    se = math.sqrt(control.variance + treatment.variance)
    z = diff / se if se > 0 else 0.0
    return Comparison(
        metric=metric, control=control, treatment=treatment, diff=diff,
        rel_diff=diff / control.rate if control.rate else None, se=se,
        ci95=(diff - Z95 * se, diff + Z95 * se), ci90=(diff - Z90 * se, diff + Z90 * se),
        p_two_sided=float(2 * stats.norm.sf(abs(z))), p_harm=float(stats.norm.cdf(z)),
    )


def srm_p_value(control: int, treatment: int, share_treatment: float = 0.5) -> float:
    """Chi-square goodness-of-fit of the assignment split against the planned split."""
    total = control + treatment
    expected = [total * (1 - share_treatment), total * share_treatment]
    return float(stats.chisquare([control, treatment], f_exp=expected).pvalue)


def two_proportion_p(x1: int, n1: int, x2: int, n2: int) -> float:
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    return float(2 * stats.norm.sf(abs(x1 / n1 - x2 / n2) / se))


def holm(p_values: list[float]) -> list[float]:
    """Holm step-down adjusted p-values, in the input order."""
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted = [0.0] * len(p_values)
    running = 0.0
    m = len(p_values)
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[i]))
        adjusted[i] = running
    return adjusted


def units_per_arm(baseline: float, mde_abs: float, alpha: float = 0.05,
                  power: float = 0.8) -> int:
    """Two-sided two-proportion test, equal arms."""
    za, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    p2 = baseline + mde_abs
    var = baseline * (1 - baseline) + p2 * (1 - p2)
    return int(math.ceil((za + zb) ** 2 * var / mde_abs**2))


def detectable_effect(baseline: float, units: int, alpha: float = 0.05,
                      power: float = 0.8) -> float:
    """Approximate MDE for `units` per arm (variance evaluated at the baseline)."""
    za, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    return float((za + zb) * math.sqrt(2 * baseline * (1 - baseline) / units))
