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

    @property
    def is_gemini(self) -> bool:
        """Returns True if configured for Gemini / Google endpoint."""
        return self.provider.lower() in ("gemini", "google") or ("generativelanguage.googleapis.com" in (self.base_url or ""))

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Builds configuration from environment variables.

        Supported environment variables:
            LLM_PROVIDER / AGENT_PROVIDER: Name of the provider ('gemini', 'openai', 'ollama', etc.)
            GEMINI_API_KEY / GOOGLE_API_KEY: Google Gemini API key
            GEMINI_MODEL / GOOGLE_MODEL: Model name (default: 'gemini-2.0-flash')
            GEMINI_BASE_URL: Custom endpoint URL (default: 'https://generativelanguage.googleapis.com/v1beta/openai/')
            OLLAMA_BASE_URL / OPENAI_BASE_URL / AGENT_BASE_URL: Custom endpoint URL
            OLLAMA_MODEL / OPENAI_MODEL / AGENT_MODEL: Model name
            OPENAI_API_KEY / AGENT_API_KEY: OpenAI Provider API key
            AGENT_TIMEOUT: Request timeout in seconds (default: 30.0 for Gemini/OpenAI, 120.0 for Ollama)
            AGENT_TEMPERATURE: Generation temperature (default: 0.1)
            AGENT_FALLBACK_TO_MOCK: 'true'/'false' (default: False if key/ollama present, True otherwise)
        """
        gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AGENT_API_KEY")
        openai_model = os.getenv("OPENAI_MODEL")
        ollama_model = os.getenv("OLLAMA_MODEL")
        gemini_model = os.getenv("GEMINI_MODEL") or os.getenv("GOOGLE_MODEL")
        provider_env = os.getenv("LLM_PROVIDER") or os.getenv("AGENT_PROVIDER")
        timeout_seconds_raw = os.getenv("AGENT_TIMEOUT_SECONDS") or os.getenv("AGENT_TIMEOUT") or "120"

        if provider_env:
            provider = provider_env.strip().lower()
            # Prefer explicit Gemini configuration over stale shell-level Ollama values.
            if provider in ("ollama", "local") and gemini_api_key:
                provider = "gemini"
            # If provider was set to ollama in shell, but active context explicitly provides
            # an OpenAI sk- key and OPENAI_MODEL, prioritize openai
            if provider in ("ollama", "local") and openai_api_key and openai_api_key.startswith("sk-") and openai_model:
                provider = "openai"
        elif gemini_api_key:
            provider = "gemini"
        elif ollama_model or os.getenv("OLLAMA_BASE_URL"):
            provider = "ollama"
        else:
            provider = "openai"

        # Endpoint, model, and api_key resolution based on provider
        if provider in ("gemini", "google"):
            api_key = gemini_api_key or openai_api_key
            base_url = (
                os.getenv("GEMINI_BASE_URL")
                or os.getenv("GOOGLE_BASE_URL")
                or "https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            model = gemini_model or os.getenv("AGENT_MODEL") or "gemini-2.0-flash"
            default_timeout = 30.0
        elif provider in ("ollama", "local"):
            api_key = openai_api_key or "ollama"
            base_url = (
                os.getenv("OLLAMA_BASE_URL")
                or os.getenv("OPENAI_BASE_URL")
                or os.getenv("AGENT_BASE_URL")
                or "http://localhost:11434/v1"
            )
            model = (
                ollama_model
                or openai_model
                or os.getenv("AGENT_MODEL")
                or "llava"
            )
            default_timeout = 120.0
        else:
            api_key = openai_api_key
            base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("AGENT_BASE_URL")
            model = openai_model or os.getenv("AGENT_MODEL") or "gpt-4o"
            default_timeout = 30.0

        # Fallback to mock: if Ollama or explicit API key, default fallback is False unless overridden
        fallback_env = os.getenv("AGENT_FALLBACK_TO_MOCK")
        if fallback_env is not None:
            fallback_to_mock = fallback_env.strip().lower() in ("true", "1", "yes")
        else:
            if provider in ("ollama", "local"):
                fallback_to_mock = False
            else:
                fallback_to_mock = not bool(api_key)

        try:
            timeout = float(timeout_seconds_raw)
        except ValueError:
            timeout = 120.0
        if timeout <= 0:
            timeout = 120.0

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
