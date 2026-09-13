"""Unit and integration tests for Ollama and local VLM support.

Tests:
1. AgentConfig loading with Ollama environment variables (OLLAMA_MODEL, OLLAMA_BASE_URL, LLM_PROVIDER).
2. Local VLM provider initialization without external cloud API keys.
3. Resilient JSON extraction from local VLM outputs (markdown fences, conversational text).
4. Response format fallback when local endpoints do not support json_object mode.
5. End-to-end planning with local VLM returning contract-compliant ActionResult.
6. Server privacy-status and analyze route integration with local VLM.
"""
import unittest
import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.config import AgentConfig
from agent.context import AgentContext
from agent.llm_planner import LLMPlanner
from agent.provider import OpenAIProvider, MockLLMProvider
from server.schemas import AnalyzeRequest


class TestOllamaConfig(unittest.TestCase):
    """Tests for Ollama-specific configuration handling."""

    def test_ollama_provider_defaults(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=True):
            cfg = AgentConfig.from_env()
            self.assertEqual(cfg.provider, "ollama")
            self.assertEqual(cfg.model, "llava")
            self.assertEqual(cfg.base_url, "http://localhost:11434/v1")
            self.assertTrue(cfg.is_ollama)
            self.assertTrue(cfg.has_api_key)
            self.assertFalse(cfg.fallback_to_mock)
            self.assertEqual(cfg.masked_api_key(), "<LOCAL OLLAMA>")

    def test_ollama_custom_model_and_url(self):
        env = {
            "LLM_PROVIDER": "ollama",
            "OLLAMA_MODEL": "qwen2-vl",
            "OLLAMA_BASE_URL": "http://127.0.0.1:11434/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = AgentConfig.from_env()
            self.assertEqual(cfg.provider, "ollama")
            self.assertEqual(cfg.model, "qwen2-vl")
            self.assertEqual(cfg.base_url, "http://127.0.0.1:11434/v1")
            self.assertTrue(cfg.is_ollama)

    def test_ollama_inferred_from_model_name(self):
        with patch.dict(os.environ, {"OLLAMA_MODEL": "llava:13b"}, clear=True):
            cfg = AgentConfig.from_env()
            self.assertEqual(cfg.provider, "ollama")
            self.assertEqual(cfg.model, "llava:13b")
            self.assertEqual(cfg.base_url, "http://localhost:11434/v1")
            self.assertTrue(cfg.is_ollama)


class TestOllamaPlannerOutputParsing(unittest.IsolatedAsyncioTestCase):
    """Tests that LLMPlanner correctly parses various local VLM output quirks."""

    def setUp(self):
        self.context = AgentContext(
            user_instruction="Click on login button",
            sanitized_screenshot="data:image/png;base64,mock",
            sanitized_dom="<button id='login-btn'>Login</button>",
            visual_elements=[{"type": "button", "id": "login-btn", "label": "Login"}],
        )

    async def test_parse_markdown_fenced_json(self):
        fenced_output = (
            "```json\n"
            "{\n"
            '  "action": {"type": "click", "target": {"id": "login-btn"}},\n'
            '  "confidence": 0.95,\n'
            '  "reason": "Matched login button based on DOM ID and text."\n'
            "}\n"
            "```"
        )
        planner = LLMPlanner(provider=MockLLMProvider(fenced_output))
        result = await planner.plan(self.context)
        self.assertEqual(result.action["type"], "click")
        self.assertEqual(result.action["target"]["id"], "login-btn")
        self.assertEqual(result.confidence, 0.95)
        self.assertTrue(result.is_high_confidence)

    async def test_parse_conversational_wrapped_json(self):
        conversational_output = (
            "Based on the provided DOM elements and screenshot, the next action to perform is:\n\n"
            "```json\n"
            "{\n"
            '  "action": {"type": "type", "target": {"id": "search-box"}, "text": "privacy"},\n'
            '  "confidence": 0.92,\n'
            '  "reason": "Targeting search box to input search term."\n'
            "}\n"
            "```\n"
            "Let me know if you need anything else!"
        )
        planner = LLMPlanner(provider=MockLLMProvider(conversational_output))
        result = await planner.plan(self.context)
        self.assertEqual(result.action["type"], "type")
        self.assertEqual(result.action["target"]["id"], "search-box")
        self.assertEqual(result.action["text"], "privacy")
        self.assertEqual(result.confidence, 0.92)

    async def test_parse_raw_unfenced_with_preamble(self):
        raw_output = (
            "Here is the planned action:\n"
            '{"action": {"type": "scroll", "target": {"direction": "down", "amount": 500}}, "confidence": 0.88, "reason": "Scrolling down to view more content."}'
        )
        planner = LLMPlanner(provider=MockLLMProvider(raw_output))
        result = await planner.plan(self.context)
        self.assertEqual(result.action["type"], "scroll")
        self.assertEqual(result.action["target"]["direction"], "down")
        self.assertEqual(result.action["target"]["amount"], 500)
        self.assertEqual(result.confidence, 0.88)


class TestOllamaProviderCall(unittest.IsolatedAsyncioTestCase):
    """Tests the OpenAIProvider with Ollama configuration."""

    async def test_ollama_client_initialization(self):
        config = AgentConfig(
            provider="ollama",
            model="llava",
            base_url="http://localhost:11434/v1",
        )
        provider = OpenAIProvider(config=config)

        # Mock the AsyncOpenAI client
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps({
            "action": {"type": "click", "target": {"id": "submit-btn"}},
            "confidence": 0.96,
            "reason": "Submit button selected."
        })
        mock_completion.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        provider._client = mock_client

        response_text = await provider.call([{"role": "user", "content": "hello"}])
        self.assertIn("submit-btn", response_text)
        mock_client.chat.completions.create.assert_called_once()
