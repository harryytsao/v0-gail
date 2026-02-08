import json
import logging
import uuid

from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.llm import LLMClient, get_llm_client
from src.profile_engine.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT

logger = logging.getLogger(__name__)


def _format_conversation(messages: list[dict]) -> str:
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content") or ""
        if isinstance(content, list):
            content = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        # Truncate very long messages to keep prompt manageable
        if len(content) > 2000:
            content = content[:2000] + "... [truncated]"
        lines.append(f"[{role}]: {content}")
    return "\n\n".join(lines)


class TraitExtractor:
    def __init__(self, api_key: str | None = None, llm_client: LLMClient | None = None):
        self.llm = llm_client or get_llm_client()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    async def extract_signals(
        self, messages: list[dict], conversation_id: uuid.UUID | None = None
    ) -> dict:
        """Extract behavioral signals from a single conversation."""
        conversation_text = _format_conversation(messages)

        if not conversation_text.strip():
            return self._empty_signals()

        raw_text = await self.llm.generate(
            system=EXTRACTION_SYSTEM_PROMPT,
            user_message=EXTRACTION_USER_PROMPT.format(conversation=conversation_text),
            model=settings.resolved_extraction_model,
            max_tokens=settings.max_extraction_tokens,
        )

        raw_text = raw_text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            lines = lines[1:]  # remove opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw_text = "\n".join(lines)

        try:
            signals = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error(
                "Failed to parse extraction response for conversation %s: %s",
                conversation_id,
                raw_text[:500],
            )
            return self._empty_signals()

        return self._validate_signals(signals)

    def _validate_signals(self, signals: dict) -> dict:
        """Ensure extracted signals have required structure."""
        validated = {}

        # Temperament
        temp = signals.get("temperament", {})
        validated["temperament"] = {
            "score": max(1, min(10, temp.get("score", 5))),
            "label": temp.get("label", "neutral"),
            "evidence": temp.get("evidence", ""),
        }

        # Communication style
        style = signals.get("communication_style", {})
        validated["communication_style"] = {
            "formality": max(0.0, min(1.0, style.get("formality", 0.5))),
            "verbosity": max(0.0, min(1.0, style.get("verbosity", 0.5))),
            "technicality": max(0.0, min(1.0, style.get("technicality", 0.5))),
            "structured": max(0.0, min(1.0, style.get("structured", 0.5))),
        }

        # Sentiment
        sent = signals.get("sentiment", {})
        validated["sentiment"] = {
            "overall": max(-1.0, min(1.0, sent.get("overall", 0.0))),
            "arc": sent.get("arc", "stable"),
            "frustration_detected": bool(sent.get("frustration_detected", False)),
        }

        # Life stage
        ls = signals.get("life_stage", {})
        validated["life_stage"] = {
            "indicators": ls.get("indicators", []),
            "confidence": max(0.0, min(1.0, ls.get("confidence", 0.5))),
            "domain_expertise": ls.get("domain_expertise", []),
        }

        # Topics
        validated["topics"] = signals.get("topics", [])

        # Cooperation
        coop = signals.get("cooperation", {})
        validated["cooperation"] = {
            "follows_instructions": max(0.0, min(1.0, coop.get("follows_instructions", 0.5))),
            "provides_context": max(0.0, min(1.0, coop.get("provides_context", 0.5))),
            "politeness": max(0.0, min(1.0, coop.get("politeness", 0.5))),
        }

        return validated

    def _empty_signals(self) -> dict:
        return {
            "temperament": {"score": 5, "label": "neutral", "evidence": ""},
            "communication_style": {
                "formality": 0.5,
                "verbosity": 0.5,
                "technicality": 0.5,
                "structured": 0.5,
            },
            "sentiment": {
                "overall": 0.0,
                "arc": "stable",
                "frustration_detected": False,
            },
            "life_stage": {
                "indicators": [],
                "confidence": 0.0,
                "domain_expertise": [],
            },
            "topics": [],
            "cooperation": {
                "follows_instructions": 0.5,
                "provides_context": 0.5,
                "politeness": 0.5,
            },
        }
