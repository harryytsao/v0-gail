def generate_reasoning(
    dimension: str,
    score: float,
    previous_score: float | None,
    components: list[dict],
) -> str:
    """Generate a human-readable explanation of a score and its change."""
    parts = []

    # Score level description
    level = _score_level(score)
    parts.append(f"{_dimension_label(dimension)} is {level} at {score:.0f}/100.")

    # Score change
    if previous_score is not None:
        delta = score - previous_score
        if abs(delta) < 1.0:
            parts.append("No significant change from previous score.")
        else:
            direction = "increased" if delta > 0 else "decreased"
            parts.append(
                f"Score {direction} from {previous_score:.0f} → {score:.0f} "
                f"(Δ{delta:+.0f})."
            )

    # Top contributing signals
    if components:
        sorted_components = sorted(components, key=lambda c: c["weight"], reverse=True)
        top = sorted_components[:3]
        contributors = []
        for comp in top:
            key_label = comp["key"].replace(".", ": ").replace("_", " ")
            contributors.append(
                f"{key_label}={comp['value']:.0f} ({comp['days_ago']:.0f}d ago)"
            )
        parts.append("Key signals: " + "; ".join(contributors) + ".")

    return " ".join(parts)


def _score_level(score: float) -> str:
    if score >= 80:
        return "high"
    if score >= 60:
        return "moderate-high"
    if score >= 40:
        return "moderate"
    if score >= 20:
        return "moderate-low"
    return "low"


def _dimension_label(dimension: str) -> str:
    labels = {
        "responsiveness": "Responsiveness",
        "escalation_risk": "Escalation risk",
        "engagement_quality": "Engagement quality",
        "cooperation_level": "Cooperation level",
        "expertise_level": "Expertise level",
    }
    return labels.get(dimension, dimension.replace("_", " ").title())
