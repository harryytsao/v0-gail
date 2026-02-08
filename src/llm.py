"""Unified LLM client supporting Gemini, Anthropic, and Ollama backends."""

import asyncio
import json
import logging

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class LLMClient:
    """Async LLM client that works with Gemini, Anthropic, and Ollama."""

    def __init__(self, provider: str | None = None, api_key: str | None = None):
        self.provider = provider or settings.llm_provider
        self._http_client = None

        if self.provider == "anthropic":
            import anthropic
            self.anthropic_client = anthropic.AsyncAnthropic(
                api_key=api_key or settings.anthropic_api_key
            )
        elif self.provider == "gemini":
            self.gemini_api_key = api_key or settings.gemini_api_key
            if not self.gemini_api_key:
                raise ValueError("GAIL_GEMINI_API_KEY is required when using gemini provider")
        elif self.provider == "ollama":
            self.ollama_base_url = settings.ollama_base_url
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client

    async def generate(
        self,
        system: str,
        user_message: str,
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Generate a response from the LLM."""
        if self.provider == "gemini":
            return await self._gemini_generate(system, user_message, model, max_tokens)
        elif self.provider == "anthropic":
            return await self._anthropic_generate(system, user_message, model, max_tokens)
        else:
            return await self._ollama_generate(system, user_message, model, max_tokens)

    async def chat(
        self,
        system: str,
        messages: list[dict],
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Multi-turn chat with the LLM."""
        if self.provider == "gemini":
            return await self._gemini_chat(system, messages, model, max_tokens)
        elif self.provider == "anthropic":
            return await self._anthropic_chat(system, messages, model, max_tokens)
        else:
            return await self._ollama_chat(system, messages, model, max_tokens)

    # --- Gemini ---

    async def _gemini_request(self, payload: dict, model: str) -> dict:
        """Make a Gemini API request with rate-limit retry."""
        client = await self._get_http_client()
        url = f"{GEMINI_API_URL}/{model}:generateContent?key={self.gemini_api_key}"

        for attempt in range(6):
            response = await client.post(url, json=payload)
            if response.status_code == 429:
                wait = min(2 ** attempt * 5, 60)  # 5s, 10s, 20s, 40s, 60s, 60s
                logger.info("Gemini rate limited, waiting %ds (attempt %d)...", wait, attempt + 1)
                await asyncio.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()

        response.raise_for_status()  # raise on final 429
        return {}

    async def _gemini_generate(self, system: str, user_message: str, model: str | None, max_tokens: int) -> str:
        model = model or settings.resolved_extraction_model
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        data = await self._gemini_request(payload, model)
        return self._extract_gemini_text(data)

    async def _gemini_chat(self, system: str, messages: list[dict], model: str | None, max_tokens: int) -> str:
        model = model or settings.resolved_agent_model
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        data = await self._gemini_request(payload, model)
        return self._extract_gemini_text(data)

    def _extract_gemini_text(self, data: dict) -> str:
        """Extract text from Gemini API response."""
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                logger.error("Gemini returned no candidates: %s", data)
                return ""
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError) as e:
            logger.error("Failed to parse Gemini response: %s — %s", e, data)
            return ""

    # --- Anthropic ---

    async def _anthropic_generate(self, system: str, user_message: str, model: str | None, max_tokens: int) -> str:
        model = model or settings.resolved_extraction_model
        response = await self.anthropic_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    async def _anthropic_chat(self, system: str, messages: list[dict], model: str | None, max_tokens: int) -> str:
        model = model or settings.resolved_agent_model
        response = await self.anthropic_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return response.content[0].text

    # --- Ollama ---

    async def _ollama_generate(self, system: str, user_message: str, model: str | None, max_tokens: int) -> str:
        model = model or settings.resolved_extraction_model
        client = await self._get_http_client()

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "options": {"num_predict": max_tokens},
        }

        response = await client.post(
            f"{self.ollama_base_url}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

    async def _ollama_chat(self, system: str, messages: list[dict], model: str | None, max_tokens: int) -> str:
        model = model or settings.resolved_agent_model
        client = await self._get_http_client()

        ollama_messages = [{"role": "system", "content": system}]
        for msg in messages:
            ollama_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }

        response = await client.post(
            f"{self.ollama_base_url}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()


# Shared instance
_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        try:
            _client = LLMClient()
        except ValueError:
            # Fallback: if no API key configured, return None
            # Callers should handle this gracefully
            raise
    return _client
