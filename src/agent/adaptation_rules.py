from src.models import UserProfile


def generate_adaptation_rules(profile: UserProfile, scores: dict) -> str:
    """Generate adaptation rules based on user profile and fit scores."""
    rules = []

    # Communication style adaptations
    style = profile.communication_style or {}
    formality = style.get("formality", 0.5)
    verbosity = style.get("verbosity", 0.5)
    technicality = style.get("technicality", 0.5)

    if formality > 0.7:
        rules.append(
            "- Use professional, formal language. Avoid colloquialisms and slang."
        )
    elif formality < 0.3:
        rules.append(
            "- Use casual, conversational language. Be friendly and approachable."
        )

    if verbosity < 0.3:
        rules.append(
            "- Keep responses concise. Use bullet points. Avoid long explanations."
        )
    elif verbosity > 0.7:
        rules.append(
            "- Provide detailed explanations. Engage with nuance and depth."
        )

    if technicality > 0.7:
        rules.append(
            "- Use domain terminology freely. Skip basic explanations. "
            "Assume strong technical background."
        )
    elif technicality < 0.3:
        rules.append(
            "- Use analogies and step-by-step explanations. Avoid jargon. "
            "Define technical terms when necessary."
        )

    # Temperament adaptations
    temperament = profile.temperament or {}
    temp_score = temperament.get("score", 5)
    if temp_score <= 3:
        rules.append(
            "- User may be impatient or confrontational. Be direct, acknowledge "
            "any frustration early, and offer solutions quickly."
        )
    elif temp_score >= 8:
        rules.append(
            "- User is patient and agreeable. Take time to be thorough and "
            "explore topics fully."
        )

    # Score-based adaptations
    escalation_risk = _get_score(scores, "escalation_risk")
    expertise = _get_score(scores, "expertise_level")
    cooperation = _get_score(scores, "cooperation_level")

    if escalation_risk > 70:
        rules.append(
            "- HIGH ESCALATION RISK: Be concise and solution-focused. "
            "Acknowledge any issues upfront. Avoid asking too many questions."
        )
    elif escalation_risk > 50:
        rules.append(
            "- Moderate escalation risk: Be mindful of tone. Proactively "
            "check if the user is satisfied."
        )

    if expertise > 70:
        rules.append(
            "- High expertise: Engage at an advanced level. Reference "
            "specific concepts and best practices."
        )
    elif expertise < 30:
        rules.append(
            "- Low expertise: Provide foundational context. Use examples "
            "and break down complex ideas."
        )

    if cooperation < 30:
        rules.append(
            "- Low cooperation signal: Be patient. Offer structured options "
            "rather than open-ended questions."
        )

    # Sentiment trend
    sentiment = profile.sentiment_trend or {}
    direction = sentiment.get("direction", "stable")
    if direction == "declining":
        rules.append(
            "- Sentiment is declining: Proactively check in on satisfaction. "
            "Offer to escalate or try a different approach."
        )
    elif direction == "improving":
        rules.append(
            "- Sentiment is improving: Maintain the positive trajectory. "
            "Acknowledge progress."
        )

    # Language adaptation
    if profile.primary_language and profile.primary_language.lower() not in ("english", "en"):
        rules.append(
            f"- User's primary language is {profile.primary_language}. "
            f"Consider responding in their language or offering to switch."
        )

    # Arc-based adaptation
    arc = profile.current_arc
    if arc == "growth":
        rules.append(
            "- User is on a growth arc: Encourage learning, provide "
            "progressively more advanced content."
        )
    elif arc == "churn":
        rules.append(
            "- User may be disengaging: Be especially helpful and engaging. "
            "Show value quickly."
        )
    elif arc == "rehabilitation":
        rules.append(
            "- User is becoming more cooperative: Reinforce positive "
            "interactions."
        )

    if not rules:
        rules.append("- Use a balanced, helpful communication style.")

    return "## Adaptation Rules\n" + "\n".join(rules)


def _get_score(scores: dict, dimension: str) -> float:
    """Extract a score value from the scores dict."""
    score_obj = scores.get(dimension)
    if score_obj is None:
        return 50.0
    if hasattr(score_obj, "score"):
        return score_obj.score
    if isinstance(score_obj, dict):
        return score_obj.get("score", 50.0)
    return 50.0


def get_adaptation_summary(profile: UserProfile, scores: dict) -> list[str]:
    """Get a list of human-readable adaptation descriptions."""
    adaptations = []

    style = profile.communication_style or {}
    formality = style.get("formality", 0.5)
    verbosity = style.get("verbosity", 0.5)

    if formality > 0.7:
        adaptations.append("Using formal, professional language")
    elif formality < 0.3:
        adaptations.append("Using casual, friendly language")

    if verbosity < 0.3:
        adaptations.append("Matching user's concise communication style")
    elif verbosity > 0.7:
        adaptations.append("Providing detailed, in-depth responses")

    expertise = _get_score(scores, "expertise_level")
    if expertise > 70:
        adaptations.append(f"Advanced-level engagement (expertise: {expertise:.0f}/100)")
    elif expertise < 30:
        adaptations.append(f"Accessible language (expertise: {expertise:.0f}/100)")

    temperament = profile.temperament or {}
    temp_label = temperament.get("label", "neutral")
    if temp_label in ("patient", "agreeable"):
        adaptations.append(f"Warm tone — user shows {temp_label} temperament")
    elif temp_label in ("hostile", "impatient"):
        adaptations.append(f"Direct tone — user shows {temp_label} temperament")

    escalation_risk = _get_score(scores, "escalation_risk")
    if escalation_risk > 70:
        adaptations.append(f"Solution-focused approach (escalation risk: {escalation_risk:.0f}/100)")

    if not adaptations:
        adaptations.append("Balanced, standard approach")

    return adaptations
