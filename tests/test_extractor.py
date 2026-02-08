import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.profile_engine.extractor import TraitExtractor, _format_conversation


class TestFormatConversation:
    def test_formats_messages(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        result = _format_conversation(messages)
        assert "[USER]: Hello" in result
        assert "[ASSISTANT]: Hi there!" in result

    def test_truncates_long_messages(self):
        messages = [{"role": "user", "content": "x" * 3000}]
        result = _format_conversation(messages)
        assert "... [truncated]" in result
        assert len(result) < 3000

    def test_handles_list_content(self):
        messages = [
            {"role": "user", "content": [{"text": "part1"}, {"text": "part2"}]}
        ]
        result = _format_conversation(messages)
        assert "part1 part2" in result

    def test_handles_empty(self):
        result = _format_conversation([])
        assert result == ""


class TestTraitExtractor:
    @pytest.mark.asyncio
    async def test_extract_signals(self, mock_anthropic, sample_messages):
        extractor = TraitExtractor(llm_client=mock_anthropic)

        signals = await extractor.extract_signals(sample_messages)

        assert "temperament" in signals
        assert "communication_style" in signals
        assert "sentiment" in signals
        assert signals["temperament"]["score"] == 7
        assert signals["temperament"]["label"] == "patient"

    @pytest.mark.asyncio
    async def test_empty_messages(self, mock_anthropic):
        extractor = TraitExtractor(llm_client=mock_anthropic)

        signals = await extractor.extract_signals([])

        assert signals["temperament"]["score"] == 5
        assert signals["temperament"]["label"] == "neutral"

    @pytest.mark.asyncio
    async def test_validates_signal_bounds(self, mock_anthropic):
        # Return out-of-bounds values
        mock_anthropic.generate = AsyncMock(
            return_value='{"temperament":{"score":15,"label":"patient","evidence":""},"communication_style":{"formality":2.0,"verbosity":-1.0,"technicality":0.5,"structured":0.5},"sentiment":{"overall":5.0,"arc":"stable","frustration_detected":false},"life_stage":{"indicators":[],"confidence":0.5,"domain_expertise":[]},"topics":[],"cooperation":{"follows_instructions":0.5,"provides_context":0.5,"politeness":0.5}}'
        )

        extractor = TraitExtractor(llm_client=mock_anthropic)

        signals = await extractor.extract_signals(
            [{"role": "user", "content": "test"}]
        )

        assert signals["temperament"]["score"] == 10  # clamped
        assert signals["communication_style"]["formality"] == 1.0  # clamped
        assert signals["communication_style"]["verbosity"] == 0.0  # clamped
        assert signals["sentiment"]["overall"] == 1.0  # clamped

    @pytest.mark.asyncio
    async def test_handles_markdown_fences(self, mock_anthropic):
        mock_anthropic.generate = AsyncMock(
            return_value='```json\n{"temperament":{"score":5,"label":"neutral","evidence":""},"communication_style":{"formality":0.5,"verbosity":0.5,"technicality":0.5,"structured":0.5},"sentiment":{"overall":0.0,"arc":"stable","frustration_detected":false},"life_stage":{"indicators":[],"confidence":0.5,"domain_expertise":[]},"topics":[],"cooperation":{"follows_instructions":0.5,"provides_context":0.5,"politeness":0.5}}\n```'
        )

        extractor = TraitExtractor(llm_client=mock_anthropic)

        signals = await extractor.extract_signals(
            [{"role": "user", "content": "test"}]
        )

        assert signals["temperament"]["score"] == 5
