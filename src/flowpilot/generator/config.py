"""Parameters of the synthetic Tasklane world.

Every number here is a documented assumption (see docs/DATA_SCENARIOS.md). Scenario parameters
are part of the frozen ground truth: they may be calibrated so the realized effect matches the
documented size, but never tuned to make the monitor or the agent look better.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

PLATFORMS = ("web", "ios", "android")
CHANNELS = ("organic_search", "paid_search", "paid_social", "referral", "partner")
COMPANY_SIZES = ("1-10", "11-50", "51-200")  # small, medium, large teams
COUNTRIES = ("US", "GB", "CA", "DE", "AU", "other")
BROWSERS = ("chrome", "safari", "edge", "firefox")


def day_offset(d: date, start: date) -> int:
    return (d - start).days


@dataclass(frozen=True)
class Release:
    platform: str
    version: str
    released_on: date


@dataclass(frozen=True)
class ExperimentSpec:
    experiment_id: str
    name: str
    hypothesis: str
    primary_metric: str
    guardrail_metrics: tuple[str, ...]
    baseline_rate: float
    mde_abs: float
    start: date
    end: date  # exclusive


RELEASES: tuple[Release, ...] = (
    Release("ios", "4.8", date(2026, 4, 20)),
    Release("ios", "4.9", date(2026, 5, 25)),
    Release("ios", "4.10", date(2026, 7, 6)),
    Release("ios", "4.11", date(2026, 8, 31)),
    Release("ios", "4.12", date(2026, 10, 26)),
    Release("android", "7.0", date(2026, 4, 27)),
    Release("android", "7.1", date(2026, 6, 15)),
    Release("android", "7.2", date(2026, 8, 24)),
    Release("android", "7.3", date(2026, 10, 27)),
)

EXPERIMENTS: tuple[ExperimentSpec, ...] = (
    ExperimentSpec(
        "E2",
        "Smart due-date suggestions",
        "Suggesting due dates when a task is created makes new users come back in week 1.",
        "week1_retention",
        ("activation_rate",),
        0.50,
        0.03,
        date(2026, 8, 3),
        date(2026, 8, 31),
    ),
    ExperimentSpec(
        "E1",
        "Onboarding checklist",
        "A guided checklist after signup gets more new workspaces to their first project, "
        "which raises activation.",
        "activation_rate",
        ("week1_retention", "trial_to_paid"),
        0.38,
        0.03,
        date(2026, 9, 14),
        date(2026, 10, 12),
    ),
    ExperimentSpec(
        "E3",
        "Aggressive upgrade prompt",
        "Showing the upgrade prompt on every session during the trial raises trial-to-paid "
        "conversion.",
        "trial_to_paid",
        ("week2_retention", "activation_rate"),
        0.09,
        0.02,
        date(2026, 9, 28),
        date(2026, 10, 26),
    ),
    ExperimentSpec(
        "E4",
        "Pricing page redesign",
        "A simpler pricing page raises trial-to-paid conversion.",
        "trial_to_paid",
        ("activation_rate",),
        0.09,
        0.02,
        date(2026, 10, 5),
        date(2026, 11, 2),
    ),
)


@dataclass(frozen=True)
class Scenarios:
    # S1: iOS 4.12 breaks the invite flow (multiplier on P(invite sent | project created)).
    s1_platform: str = "ios"
    s1_version: str = "4.12"
    s1_invite_multiplier: float = 0.68
    # S1b: decoy channel-mix shift; paid search share rises from this date.
    s1b_start: date = date(2026, 10, 26)
    s1b_channel_probs: tuple[float, ...] = (0.32, 0.25, 0.18, 0.15, 0.10)
    # S2: new paid-social targeting from this date lowers long-run engagement (not activation).
    s2_channel: str = "paid_social"
    s2_start: date = date(2026, 9, 7)
    s2_floor_multiplier: float = 0.77
    s2_lifetime_multiplier: float = 0.69
    # S3: Timeline view ships on web only.
    s3_feature: str = "timeline_view"
    s3_launch: date = date(2026, 8, 17)
    s3_adopter_share_web: float = 0.35
    # S4: integrations usage depends on team size only; integrations have no effect.
    s4_integration_share_by_size: tuple[float, ...] = (0.08, 0.25, 0.55)
    # S5: Android 7.3 stops sending task_created events (tracking gap, behavior unchanged).
    s5_platform: str = "android"
    s5_version: str = "7.3"
    s5_event: str = "task_created"
    s5_start: date = date(2026, 11, 3)
    s5_end: date = date(2026, 11, 6)  # exclusive
    # E1: checklist raises P(project created).
    e1_project_uplift: float = 0.06
    # E3: upgrade prompt raises conversion but lowers engagement.
    e3_conversion_uplift: float = 0.015
    e3_engagement_multiplier: float = 0.86
    # E4: assignment bug drops treatment workspaces whose founder signed up in Safari.
    e4_dropped_browser: str = "safari"
    # Prompt-injection strings placed in user-generated names.
    injection_share: float = 0.002


@dataclass(frozen=True)
class WorldConfig:
    seed: int = 20261116
    start: date = date(2026, 5, 4)  # Monday
    end: date = date(2026, 11, 16)  # exclusive; data covers 28 full weeks
    weekly_signups: float = 2500.0
    scale: float = 1.0  # tests use a smaller world
    channel_probs: tuple[float, ...] = (0.35, 0.20, 0.20, 0.15, 0.10)
    platform_probs: tuple[float, ...] = (0.55, 0.30, 0.15)
    scenarios: Scenarios = field(default_factory=Scenarios)

    @property
    def n_days(self) -> int:
        return (self.end - self.start).days

    @property
    def start_epoch_s(self) -> int:
        midnight = datetime(self.start.year, self.start.month, self.start.day, tzinfo=UTC)
        return int(midnight.timestamp())
