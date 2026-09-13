"""Unit tests for Google Gemini integration in agent and server."""
import importlib
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
from agent.provider import OpenAIProvider, MockLLMProvider, ProviderRateLimitError


class TestGeminiConfig(unittest.TestCase):
    """Tests for Gemini configuration resolution."""

    def test_gemini_config_defaults(self):
        env = {
            "GEMINI_API_KEY": "AIzaSyTestKey1234567890",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = AgentConfig.from_env()
            self.assertEqual(cfg.provider, "gemini")
            self.assertEqual(cfg.model, "gemini-2.0-flash")
            self.assertEqual(cfg.base_url, "https://generativelanguage.googleapis.com/v1beta/openai/")
            self.assertTrue(cfg.is_gemini)
            self.assertFalse(cfg.is_ollama)
            self.assertTrue(cfg.has_api_key)
            self.assertFalse(cfg.fallback_to_mock)

    def test_gemini_custom_model_and_url(self):
        env = {
            "LLM_PROVIDER": "gemini",
            "GEMINI_API_KEY": "AIzaSyCustomKey",
            "GEMINI_MODEL": "gemini-1.5-flash",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = AgentConfig.from_env()
            self.assertEqual(cfg.provider, "gemini")
            self.assertEqual(cfg.model, "gemini-1.5-flash")
            self.assertEqual(cfg.base_url, "https://generativelanguage.googleapis.com/v1beta/openai/")

    @patch("dotenv.load_dotenv")
    def test_server_env_file_overrides_shell_provider(self, mock_load_dotenv):
        sys.modules.pop("server.main", None)
        import server.main
        importlib.reload(server.main)

        self.assertTrue(mock_load_dotenv.called)
        self.assertTrue(mock_load_dotenv.call_args.kwargs.get("override"))


class TestGeminiProviderAndPlanner(unittest.IsolatedAsyncioTestCase):
    """Tests that Gemini provider and planner correctly format and parse responses."""

    def setUp(self):
        self.context = AgentContext(
            user_instruction="Click on Login",
            sanitized_screenshot="data:image/png;base64,mock",
            sanitized_dom="<button id='btn-login'>Login</button>",
            visual_elements=[{"type": "button", "id": "btn-login", "label": "Login"}],
        )

    async def test_gemini_planner_valid_response(self):
        gemini_response = json.dumps({
            "action": {
                "type": "click",
                "target": {"id": "btn-login"}
            },
            "confidence": 0.98,
            "reason": "Gemini matched the login button directly."
        })
        planner = LLMPlanner(provider=MockLLMProvider(gemini_response))
        result = await planner.plan(self.context)
        self.assertEqual(result.action["type"], "click")
        self.assertEqual(result.action["target"]["id"], "btn-login")
        self.assertEqual(result.confidence, 0.98)
        self.assertTrue(result.is_high_confidence)

    def test_gemini_quota_rate_limit_error(self):
        error = ProviderRateLimitError("Gemini quota exhausted", retry_after=12.0)
        self.assertEqual(error.retry_after, 12.0)
        self.assertIn("quota exhausted", str(error).lower())
