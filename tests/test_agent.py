import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agent.adaptation_rules import generate_adaptation_rules, get_adaptation_summary
from src.agent.prompt_builder import build_default_prompt, build_system_prompt
from src.models import UserProfile


class TestAdaptationRules:
    def test_formal_user(self):
        profile = MagicMock(spec=UserProfile)
        profile.communication_style = {"formality": 0.9, "verbosity": 0.5, "technicality": 0.5}
        profile.temperament = {"score": 5, "label": "neutral"}
        profile.sentiment_trend = {"direction": "stable"}
        profile.primary_language = "English"
        profile.current_arc = "stable"

        rules = generate_adaptation_rules(profile, {})
        assert "formal" in rules.lower() or "professional" in rules.lower()

    def test_casual_terse_user(self):
        profile = MagicMock(spec=UserProfile)
        profile.communication_style = {"formality": 0.1, "verbosity": 0.1, "technicality": 0.2}
        profile.temperament = {"score": 5, "label": "neutral"}
        profile.sentiment_trend = {"direction": "stable"}
        profile.primary_language = "English"
        profile.current_arc = None

        rules = generate_adaptation_rules(profile, {})
        assert "casual" in rules.lower() or "concise" in rules.lower()

    def test_high_escalation_risk(self):
        profile = MagicMock(spec=UserProfile)
        profile.communication_style = {"formality": 0.5, "verbosity": 0.5, "technicality": 0.5}
        profile.temperament = {"score": 2, "label": "impatient"}
        profile.sentiment_trend = {"direction": "declining"}
        profile.primary_language = "English"
        profile.current_arc = None

        mock_score = MagicMock()
        mock_score.score = 85.0
        scores = {"escalation_risk": mock_score}

        rules = generate_adaptation_rules(profile, scores)
        assert "escalation" in rules.lower() or "solution" in rules.lower()

    def test_non_english_user(self):
        profile = MagicMock(spec=UserProfile)
        profile.communication_style = {"formality": 0.5, "verbosity": 0.5, "technicality": 0.5}
        profile.temperament = {"score": 5, "label": "neutral"}
        profile.sentiment_trend = {"direction": "stable"}
        profile.primary_language = "Spanish"
        profile.current_arc = None

        rules = generate_adaptation_rules(profile, {})
        assert "Spanish" in rules

    def test_get_adaptation_summary(self):
        profile = MagicMock(spec=UserProfile)
        profile.communication_style = {"formality": 0.1, "verbosity": 0.2, "technicality": 0.5}
        profile.temperament = {"score": 8, "label": "patient"}

        mock_score = MagicMock()
        mock_score.score = 25.0
        scores = {"expertise_level": mock_score}

        summary = get_adaptation_summary(profile, scores)
        assert isinstance(summary, list)
        assert len(summary) > 0


class TestPromptBuilder:
    def test_build_system_prompt(self, sample_profile):
        scores = {}
        prompt = build_system_prompt(sample_profile, scores)

        assert "Gail" in prompt
        assert "patient" in prompt
        assert str(sample_profile.user_id) in prompt

    def test_build_default_prompt(self):
        prompt = build_default_prompt()
        assert "Gail" in prompt
        assert "balanced" in prompt.lower()

    def test_prompt_includes_scores(self, sample_profile):
        mock_score = MagicMock()
        mock_score.score = 72.0
        scores = {"expertise_level": mock_score}

        prompt = build_system_prompt(sample_profile, scores)
        assert "72" in prompt

    def test_prompt_includes_arc(self, sample_profile):
        sample_profile.current_arc = "growth"
        prompt = build_system_prompt(sample_profile, {})
        assert "growth" in prompt
