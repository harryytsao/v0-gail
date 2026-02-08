import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from src.config import settings
from src.evolution.temporal import std_dev, temporal_weight, weighted_mean
from src.models import BehavioralSignal

logger = logging.getLogger(__name__)


@dataclass
class ResolvedTrait:
    value: float
    confidence: float
    volatility: str  # "low", "medium", "high"
    arc: str | None  # detected arc label
    note: str


def signals_in_window(
    signals: list[BehavioralSignal],
    days: int,
    now: datetime | None = None,
) -> list[BehavioralSignal]:
    """Filter signals to those within a time window."""
    now = now or datetime.now(timezone.utc)
    cutoff_seconds = days * 86400
    return [
        s
        for s in signals
        if (now - s.extracted_at.replace(tzinfo=timezone.utc)).total_seconds() <= cutoff_seconds
    ]


def resolve_conflict(
    signals: list[BehavioralSignal],
    value_extractor: callable,
    now: datetime | None = None,
) -> ResolvedTrait:
    """Resolve conflicting signals using temporal analysis.

    Args:
        signals: List of behavioral signals of the same type.
        value_extractor: Function that extracts a numeric value from a signal.
        now: Current timestamp for computing recency.
    """
    now = now or datetime.now(timezone.utc)

    if not signals:
        return ResolvedTrait(
            value=0.0,
            confidence=0.0,
            volatility="low",
            arc=None,
            note="No signals available",
        )

    values = [value_extractor(s) for s in signals]
    values = [v for v in values if v is not None]
    if not values:
        return ResolvedTrait(
            value=0.0,
            confidence=0.0,
            volatility="low",
            arc=None,
            note="No extractable values",
        )

    # Split into recent and older windows
    recent_signals = signals_in_window(signals, days=30, now=now)
    older_signals = signals_in_window(signals, days=90, now=now)

    recent_values = [v for v in (value_extractor(s) for s in recent_signals) if v is not None]
    older_values = [v for v in (value_extractor(s) for s in older_signals) if v is not None]

    # Compute weights based on temporal decay
    weights = [temporal_weight(s.extracted_at, now) * s.confidence for s in signals]
    all_values_filtered = [value_extractor(s) for s in signals]
    pairs = [(v, w) for v, w in zip(all_values_filtered, weights) if v is not None]

    if not pairs:
        return ResolvedTrait(
            value=0.0,
            confidence=0.0,
            volatility="low",
            arc=None,
            note="No valid signal pairs",
        )

    filtered_values, filtered_weights = zip(*pairs)

    # Check recent signal consistency
    if recent_values and std_dev(recent_values) < settings.consistency_threshold:
        # Recent signals are consistent — trust the recent trend
        recent_weights = [
            temporal_weight(s.extracted_at, now) * s.confidence for s in recent_signals
        ]
        recent_vals = [v for v in (value_extractor(s) for s in recent_signals) if v is not None]
        if recent_vals:
            value = weighted_mean(
                recent_vals,
                recent_weights[: len(recent_vals)],
            )

            arc = _detect_simple_arc(older_values, recent_values)

            return ResolvedTrait(
                value=value,
                confidence=min(1.0, 0.5 + len(recent_values) * 0.1),
                volatility="low",
                arc=arc,
                note="Consistent recent behavior" + (
                    f" diverges from historical ({arc})" if arc else ""
                ),
            )

    # Recent signals are inconsistent — flag volatility
    overall = weighted_mean(list(filtered_values), list(filtered_weights))
    overall_std = std_dev(values)

    if overall_std > 3.0:
        volatility = "high"
    elif overall_std > 1.5:
        volatility = "medium"
    else:
        volatility = "low"

    return ResolvedTrait(
        value=overall,
        confidence=max(0.1, 0.5 - overall_std * 0.1),
        volatility=volatility,
        arc=None,
        note=f"Inconsistent signals (std={overall_std:.2f}) — context-dependent behavior",
    )


def _detect_simple_arc(
    older_values: list[float], recent_values: list[float]
) -> str | None:
    """Detect a simple behavioral arc from two value windows."""
    if not older_values or not recent_values:
        return None

    older_mean = sum(older_values) / len(older_values)
    recent_mean = sum(recent_values) / len(recent_values)
    diff = recent_mean - older_mean

    threshold = 1.5

    if diff > threshold:
        return "growth"
    elif diff < -threshold:
        return "declining"
    else:
        return "stable"
