EXTRACTION_SYSTEM_PROMPT = """You are a behavioral analysis system. You extract structured behavioral signals from conversations between a user and an AI assistant.

You MUST return valid JSON and nothing else. No markdown, no explanation, just the JSON object."""

EXTRACTION_USER_PROMPT = """Analyze this conversation and extract behavioral signals about the user (not the assistant).

## Conversation
{conversation}

## Instructions
Extract the following signals. For each, provide your assessment based ONLY on evidence in the conversation.

Return this exact JSON structure:
{{
  "temperament": {{
    "score": <1-10, where 1=very impatient/hostile, 10=very patient/agreeable>,
    "label": "<one of: hostile, impatient, neutral, patient, agreeable>",
    "evidence": "<brief quote or description from conversation>"
  }},
  "communication_style": {{
    "formality": <0.0-1.0, where 0=very casual, 1=very formal>,
    "verbosity": <0.0-1.0, where 0=very terse, 1=very verbose>,
    "technicality": <0.0-1.0, where 0=layperson, 1=highly technical>,
    "structured": <0.0-1.0, where 0=freeform, 1=highly structured>
  }},
  "sentiment": {{
    "overall": <-1.0 to 1.0, where -1=very negative, 1=very positive>,
    "arc": "<one of: stable, improving, declining, volatile>",
    "frustration_detected": <true/false>
  }},
  "life_stage": {{
    "indicators": ["<list of detected indicators, e.g. 'student', 'professional', 'parent'>"],
    "confidence": <0.0-1.0>,
    "domain_expertise": ["<detected domains, e.g. 'software engineering', 'law'>"]
  }},
  "topics": ["<list of topic categories discussed, e.g. 'technology', 'legal', 'math'>"],
  "cooperation": {{
    "follows_instructions": <0.0-1.0>,
    "provides_context": <0.0-1.0>,
    "politeness": <0.0-1.0>
  }}
}}"""

AGGREGATION_PROMPT = """Given these behavioral signals extracted from multiple conversations by the same user, produce a unified user profile summary.

## Signals
{signals_json}

## Instructions
Synthesize the signals into a coherent profile. Where signals conflict, note the volatility. Weight recent signals more heavily.

Return this JSON structure:
{{
  "temperament": {{
    "score": <weighted average 1-10>,
    "label": "<dominant label>",
    "volatility": "<low/medium/high>",
    "summary": "<1-2 sentence description>"
  }},
  "communication_style": {{
    "formality": <weighted average 0-1>,
    "verbosity": <weighted average 0-1>,
    "technicality": <weighted average 0-1>,
    "structured": <weighted average 0-1>,
    "summary": "<1-2 sentence description>"
  }},
  "sentiment_trend": {{
    "direction": "<improving/stable/declining/volatile>",
    "recent_avg": <-1 to 1>,
    "summary": "<1-2 sentence description>"
  }},
  "life_stage": {{
    "stage": "<most likely life stage>",
    "confidence": <0-1>,
    "domain_expertise": ["<aggregated domains>"]
  }},
  "topic_interests": {{
    "primary": ["<top 3 topics>"],
    "secondary": ["<other topics>"]
  }}
}}"""
