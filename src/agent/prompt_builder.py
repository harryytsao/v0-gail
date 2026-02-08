from src.agent.adaptation_rules import generate_adaptation_rules
from src.models import UserProfile

BASE_PROMPT = """You are Gail, an adaptive conversational agent. You adapt your communication style, depth, and tone based on the user's behavioral profile.

Your core traits:
- You are helpful, honest, and attentive
- You adapt naturally without being obvious about it
- You never mention the profile system or scoring to the user
- You treat each conversation as a genuine interaction"""


def build_system_prompt(profile: UserProfile, scores: dict) -> str:
    """Build a dynamic system prompt tailored to a specific user's profile."""
    parts = [BASE_PROMPT]

    # Add profile context
    profile_context = _build_profile_context(profile, scores)
    if profile_context:
        parts.append(profile_context)

    # Add adaptation rules
    rules = generate_adaptation_rules(profile, scores)
    parts.append(rules)

    return "\n\n".join(parts)


def build_default_prompt() -> str:
    """Build a default system prompt for users without profiles."""
    return (
        BASE_PROMPT
        + "\n\n## Adaptation Rules\n"
        "- Use a balanced, helpful communication style.\n"
        "- Ask clarifying questions when needed.\n"
        "- Be concise but thorough."
    )


def _build_profile_context(profile: UserProfile, scores: dict) -> str:
    """Build the profile context section of the system prompt."""
    lines = [f"## User Profile for {profile.user_id}"]

    # Temperament
    temp = profile.temperament or {}
    if temp:
        lines.append(
            f"- Temperament: {temp.get('label', 'unknown')} "
            f"({temp.get('score', '?')}/10, {temp.get('volatility', 'unknown')} volatility)"
        )

    # Communication style
    style = profile.communication_style or {}
    if style:
        summary = style.get("summary", "unknown")
        lines.append(f"- Communication style: {summary}")

    # Scores
    score_lines = []
    for dim in ("expertise_level", "escalation_risk", "cooperation_level", "engagement_quality"):
        score_obj = scores.get(dim)
        if score_obj:
            val = score_obj.score if hasattr(score_obj, "score") else score_obj.get("score", "?")
            label = dim.replace("_", " ").title()
            score_lines.append(f"{label}: {val}/100")
    if score_lines:
        lines.append("- Scores: " + ", ".join(score_lines))

    # Sentiment
    sentiment = profile.sentiment_trend or {}
    if sentiment:
        direction = sentiment.get("direction", "unknown")
        lines.append(f"- Recent sentiment trend: {direction}")

    # Arc
    if profile.current_arc:
        lines.append(f"- Behavioral arc: {profile.current_arc}")

    # Topics
    topics = profile.topic_interests or {}
    if topics.get("primary"):
        lines.append(f"- Interests: {', '.join(topics['primary'])}")

    # Language
    if profile.primary_language and profile.primary_language.lower() not in ("english", "en"):
        lines.append(f"- Primary language: {profile.primary_language}")

    return "\n".join(lines)
