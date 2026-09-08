"""LLM/VLM Provider abstraction layer.

Keeps LLM/VLM provider implementation separate from agent planning logic.
Uses environment configuration for API keys, model parameters, and base URLs.
Never hardcodes secrets.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union
from agent.config import AgentConfig

logger = logging.getLogger("agent.provider")


class ProviderError(Exception):
    """Raised when an LLM/VLM provider fails or returns an error."""
    pass


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
            if not self.config.has_api_key:
                raise ProviderError(
                    "OPENAI_API_KEY is not configured. Set the OPENAI_API_KEY environment variable."
                )
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:
                raise ProviderError(f"Failed to import openai package: {exc}") from exc

            kwargs: Dict[str, Any] = {
                "api_key": self.config.api_key,
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
            "Calling VLM/LLM provider=%s model=%s (api_key=%s)",
            self.config.provider,
            self.config.model,
            self.config.masked_api_key(),
        )

        try:
            # We request json_object response_format where supported
            completion = await client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                response_format={"type": "json_object"},
            )

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
