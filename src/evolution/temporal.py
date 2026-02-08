from datetime import datetime, timezone


def temporal_weight(signal_date: datetime, now: datetime | None = None) -> float:
    """Compute temporal weight based on signal age using decay windows.

    Windows:
        0-30 days:   weight 1.0
        30-90 days:  weight 0.6
        90-180 days: weight 0.3
        180+ days:   weight 0.1
    """
    now = now or datetime.now(timezone.utc)
    if signal_date.tzinfo is None:
        signal_date = signal_date.replace(tzinfo=timezone.utc)
    days = (now - signal_date).total_seconds() / 86400

    if days <= 30:
        return 1.0
    elif days <= 90:
        return 0.6
    elif days <= 180:
        return 0.3
    else:
        return 0.1


def weighted_mean(values: list[float], weights: list[float]) -> float:
    """Compute weighted mean, falling back to simple mean if weights sum to 0."""
    if not values:
        return 0.0
    total_w = sum(weights)
    if total_w == 0:
        return sum(values) / len(values)
    return sum(v * w for v, w in zip(values, weights)) / total_w


def std_dev(values: list[float]) -> float:
    """Compute standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance**0.5
