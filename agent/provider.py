"""LLM/VLM Provider abstraction layer.

Keeps LLM/VLM provider implementation separate from agent planning logic.
Uses environment configuration for API keys, model parameters, and base URLs.
Never hardcodes secrets.
"""
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union
from agent.config import AgentConfig

logger = logging.getLogger("agent.provider")


def _extract_retry_after(exc: Exception) -> Optional[int]:
    """Extract a Retry-After value from common provider exception shapes."""
    headers = None

    if hasattr(exc, "headers") and exc.headers:
        headers = exc.headers
    elif hasattr(exc, "response") and getattr(exc.response, "headers", None):
        headers = exc.response.headers

    if headers is not None:
        for key in ("retry-after", "Retry-After"):
            value = headers.get(key)
            if value is not None:
                try:
                    return int(float(str(value).strip()))
                except (TypeError, ValueError):
                    return None

    if hasattr(exc, "status_code") and exc.status_code == 429:
        return 30

    raw = str(exc).lower()
    if "retry-after" in raw:
        match = re.search(r"retry-after[:\s]+(\d+)", raw)
        if match:
            return int(match.group(1))

    return None


def _looks_like_rate_limit(exc: Exception, raw_message: str) -> bool:
    """Check whether the exception represents a quota or rate-limit failure."""
    text = raw_message.lower()
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    if any(token in text for token in ("resource_exhausted", "rate limit", "rate-limit", "quota exceeded", "quota exhausted", "429")):
        return True
    if hasattr(exc, "body"):
        try:
            body = str(exc.body).lower()
            if any(token in body for token in ("resource_exhausted", "rate limit", "quota exceeded", "quota exhausted", "429")):
                return True
        except Exception:
            pass
    return False


class ProviderError(Exception):
    """Raised when an LLM/VLM provider fails or returns an error."""
    pass


class ProviderRateLimitError(ProviderError):
    """Raised for provider quota/rate-limit failures that should return 429 responses."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class BaseLLMProvider(ABC):
    """Abstract interface for LLM/VLM providers."""

    @abstractmethod
    async def call(self, messages: List[Dict[str, Any]]) -> str:
        """Sends multimodal messages to the model and returns the raw string response.

        Args:
            messages: Formatted message payload (system prompt, user text, image url).

        Returns:
            The raw text content returned by the model.

        Raises:
            ProviderError: If the provider call fails.
        """
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI-compatible VLM/LLM provider client.

    Compatible with OpenAI (GPT-4o, GPT-4o-mini) as well as OpenAI-compatible
    endpoints (Ollama, vLLM, Azure OpenAI, OpenRouter).
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig.from_env()
        self._client = None

    def _get_client(self):
        """Lazy-initializes the AsyncOpenAI client."""
        if self._client is None:
            if not self.config.has_api_key and not self.config.is_ollama:
                raise ProviderError(
                    "API key is not configured. Set GEMINI_API_KEY (for Google Gemini), OPENAI_API_KEY (for OpenAI), or set LLM_PROVIDER=ollama."
                )
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:
                raise ProviderError(f"Failed to import openai package: {exc}") from exc

            api_key = self.config.api_key or ("ollama" if self.config.is_ollama else "none")
            kwargs: Dict[str, Any] = {
                "api_key": api_key,
                "timeout": self.config.timeout,
            }
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url

            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def call(self, messages: List[Dict[str, Any]]) -> str:
        """Calls the chat completion endpoint with vision messages and returns the raw text."""
        client = self._get_client()

        logger.info(
            "Calling VLM/LLM provider=%s model=%s base_url=%s (api_key=%s)",
            self.config.provider,
            self.config.model,
            self.config.base_url or "default",
            self.config.masked_api_key(),
        )

        try:
            # We request json_object response_format where supported
            try:
                completion = await client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    response_format={"type": "json_object"},
                )
            except Exception as initial_err:
                err_str = str(initial_err).lower()
                # If local model/endpoint rejects response_format, retry without it
                if any(kw in err_str for kw in ("response_format", "json_object", "format", "400", "422", "unsupported")):
                    logger.warning("Model endpoint rejected json_object response_format (%s); retrying without it.", initial_err)
                    completion = await client.chat.completions.create(
                        model=self.config.model,
                        messages=messages,
                        temperature=self.config.temperature,
                    )
                else:
                    raise initial_err

            choice = completion.choices[0]
            content = choice.message.content
            if not content:
                raise ProviderError("Model returned empty content in choice message.")
            return content.strip()

        except Exception as exc:
            # Mask API key if accidentally contained in exception message
            err_msg = str(exc)
            if self.config.api_key and self.config.api_key in err_msg:
                err_msg = err_msg.replace(self.config.api_key, self.config.masked_api_key())

            if _looks_like_rate_limit(exc, err_msg):
                retry_after = _extract_retry_after(exc)
                logger.warning("VLM/LLM provider rate limit reached: %s (retry_after=%s)", err_msg, retry_after)
                raise ProviderRateLimitError(f"Model provider rate limit exceeded: {err_msg}", retry_after=retry_after) from exc

            logger.error("VLM/LLM provider call failed: %s", err_msg)
            raise ProviderError(f"Model provider request failed: {err_msg}") from exc


class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock provider for unit testing and safe offline testing.

    Can be initialized with a fixed string response or a callable responding to messages.
    """

    def __init__(self, response_factory: Optional[Union[str, Callable[[List[Dict[str, Any]]], str]]] = None):
        self.response_factory = response_factory or '{"action": {"type": "click", "target": {"id": "submit-btn"}}, "confidence": 0.95, "reason": "Target matches instruction"}'
        self.last_messages: Optional[List[Dict[str, Any]]] = None

    async def call(self, messages: List[Dict[str, Any]]) -> str:
        self.last_messages = messages
        if callable(self.response_factory):
            return self.response_factory(messages)
        return str(self.response_factory)
