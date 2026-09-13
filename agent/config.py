"""Configuration management for VLM/LLM providers.

Reads provider settings, API keys, and model parameters from environment variables.
Never hardcodes secrets.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentConfig:
    """Configuration settings for LLM/VLM planning agents.

    Attributes:
        provider: Provider identifier ('openai', 'generic', etc.).
        api_key: Secret API key loaded from environment variables.
        model: Model identifier (e.g., 'gpt-4o', 'gpt-4o-mini').
        base_url: Optional custom API endpoint (for Ollama, vLLM, Azure, OpenRouter).
        timeout: Timeout in seconds for remote API calls.
        temperature: Sampling temperature for model generation (lower = more deterministic).
        fallback_to_mock: Whether to fall back to deterministic planner if API key is absent.
    """
    provider: str = "openai"
    api_key: Optional[str] = None
    model: str = "gpt-4o"
    base_url: Optional[str] = None
    timeout: float = 30.0
    temperature: float = 0.1
    fallback_to_mock: bool = False

    @property
    def is_ollama(self) -> bool:
        """Returns True if configured for Ollama or local endpoint."""
        return self.provider.lower() in ("ollama", "local") or ("localhost:11434" in (self.base_url or ""))

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Builds configuration from environment variables.

        Supported environment variables:
            LLM_PROVIDER / AGENT_PROVIDER: Name of the provider ('openai', 'ollama', etc.)
            OLLAMA_BASE_URL / OPENAI_BASE_URL / AGENT_BASE_URL: Custom endpoint URL
            OLLAMA_MODEL / OPENAI_MODEL / AGENT_MODEL: Model name (default: 'gpt-4o' or 'llava')
            OPENAI_API_KEY / AGENT_API_KEY: Provider API key (auto-set to 'ollama' for Ollama)
            AGENT_TIMEOUT: Request timeout in seconds (default: 30.0)
            AGENT_TEMPERATURE: Generation temperature (default: 0.1)
            AGENT_FALLBACK_TO_MOCK: 'true'/'false' (default: False for Ollama, True if no API key for OpenAI)
        """
        provider = (
            os.getenv("LLM_PROVIDER")
            or os.getenv("AGENT_PROVIDER")
            or ("ollama" if os.getenv("OLLAMA_MODEL") or os.getenv("OLLAMA_BASE_URL") else "openai")
        ).lower()

        # Endpoint resolution (default to http://localhost:11434/v1 for Ollama)
        base_url = os.getenv("OLLAMA_BASE_URL") or os.getenv("OPENAI_BASE_URL") or os.getenv("AGENT_BASE_URL")
        if not base_url and provider in ("ollama", "local"):
            base_url = "http://localhost:11434/v1"

        # Model resolution (default to 'llava' for Ollama, 'gpt-4o' for OpenAI)
        default_model = "llava" if provider in ("ollama", "local") else "gpt-4o"
        model = (
            os.getenv("OLLAMA_MODEL")
            or os.getenv("OPENAI_MODEL")
            or os.getenv("AGENT_MODEL")
            or default_model
        )

        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AGENT_API_KEY")
        # Ollama local VLM doesn't require an external API key; provide dummy key for AsyncOpenAI client
        if not api_key and provider in ("ollama", "local"):
            api_key = "ollama"

        # Fallback to mock: if Ollama or explicit API key, default fallback is False unless overridden
        fallback_env = os.getenv("AGENT_FALLBACK_TO_MOCK")
        if fallback_env is not None:
            fallback_to_mock = fallback_env.strip().lower() in ("true", "1", "yes")
        else:
            if provider in ("ollama", "local"):
                fallback_to_mock = False
            else:
                fallback_to_mock = not bool(api_key)

        timeout_str = os.getenv("AGENT_TIMEOUT", "30.0")
        try:
            timeout = float(timeout_str)
        except ValueError:
            timeout = 30.0

        temp_str = os.getenv("AGENT_TEMPERATURE", "0.1")
        try:
            temperature = float(temp_str)
        except ValueError:
            temperature = 0.1

        return cls(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout=timeout,
            temperature=temperature,
            fallback_to_mock=fallback_to_mock,
        )

    def masked_api_key(self) -> str:
        """Returns a masked version of the API key for safe logging.

        Example:
            sk-proj-abc123456789xyz -> sk-...9xyz
            ollama -> <LOCAL OLLAMA>
            None -> <NOT SET>
        """
        if self.is_ollama and (not self.api_key or self.api_key == "ollama"):
            return "<LOCAL OLLAMA>"
        if not self.api_key:
            return "<NOT SET>"
        clean = self.api_key.strip()
        if len(clean) <= 8:
            return "***"
        return f"{clean[:3]}...{clean[-4:]}"

    @property
    def has_api_key(self) -> bool:
        """Returns True if a non-empty API key is configured or provider is local Ollama."""
        if self.is_ollama:
            return True
        return bool(self.api_key and self.api_key.strip())
