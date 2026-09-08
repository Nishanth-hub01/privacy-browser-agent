"""Comprehensive tests for LLM/VLM agent planner, configuration, and multimodal prompt building."""
import unittest
import sys
import json
import os
from pathlib import Path
from unittest.mock import patch

# Ensure root is on path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.context import AgentContext
from agent.config import AgentConfig
from agent.prompts import build_multimodal_messages, format_screenshot_data_uri, SYSTEM_PROMPT
from agent.provider import MockLLMProvider, ProviderError, OpenAIProvider
from agent.llm_planner import LLMPlanner
from agent.actions import ActionResult, CONFIDENCE_THRESHOLD
from agent.agent import BrowserAgent


class TestAgentConfig(unittest.TestCase):
    """Tests for provider configuration and secret handling."""

    def test_default_config(self):
        config = AgentConfig()
        self.assertEqual(config.provider, "openai")
        self.assertEqual(config.model, "gpt-4o")
        self.assertFalse(config.has_api_key)
        self.assertEqual(config.masked_api_key(), "<NOT SET>")

    def test_api_key_masking(self):
        config = AgentConfig(api_key="sk-proj-1234567890abcdef")
        self.assertTrue(config.has_api_key)
        masked = config.masked_api_key()
        self.assertTrue(masked.startswith("sk-"))
        self.assertTrue(masked.endswith("cdef"))
        self.assertNotIn("1234567890", masked)

    def test_short_key_masking(self):
        config = AgentConfig(api_key="secret")
        self.assertEqual(config.masked_api_key(), "***")

    def test_from_env_loading(self):
        env_vars = {
            "OPENAI_API_KEY": "sk-test-key-9999",
            "OPENAI_MODEL": "gpt-4o-mini",
            "OPENAI_BASE_URL": "http://localhost:8080/v1",
            "AGENT_TIMEOUT": "45.0",
            "AGENT_TEMPERATURE": "0.2",
            "AGENT_FALLBACK_TO_MOCK": "false",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            config = AgentConfig.from_env()
            self.assertEqual(config.api_key, "sk-test-key-9999")
            self.assertEqual(config.model, "gpt-4o-mini")
            self.assertEqual(config.base_url, "http://localhost:8080/v1")
            self.assertEqual(config.timeout, 45.0)
            self.assertEqual(config.temperature, 0.2)
            self.assertFalse(config.fallback_to_mock)


class TestPromptAndMultimodalPayload(unittest.TestCase):
    """Tests for prompt assembly verifying that all 4 required inputs are sent."""

    def setUp(self):
        self.context = AgentContext(
            user_instruction="Click the login button",
            sanitized_screenshot="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            sanitized_dom="<button id='login-btn'>Log In</button>",
            visual_elements=[
                {"type": "button", "label": "Log In", "id": "login-btn", "selector": "#login-btn"}
            ],
        )

    def test_all_four_inputs_included(self):
        """The AI model must receive:
        - user_instruction
        - sanitized_screenshot
        - sanitized_dom
        - visual_elements
        """
        messages = build_multimodal_messages(self.context)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("SUPPORTED ACTIONS", messages[0]["content"])

        user_msg = messages[1]
        self.assertEqual(user_msg["role"], "user")
        content = user_msg["content"]

        # Content must contain text part and image part
        text_part = next((p for p in content if p["type"] == "text"), None)
        image_part = next((p for p in content if p["type"] == "image_url"), None)

        self.assertIsNotNone(text_part)
        self.assertIsNotNone(image_part)

        text = text_part["text"]
        # 1. user_instruction
        self.assertIn("Click the login button", text)
        # 2. sanitized_dom
        self.assertIn("<button id='login-btn'>Log In</button>", text)
        # 3. visual_elements
        self.assertIn("login-btn", text)
        # 4. sanitized_screenshot (in image_url)
        self.assertTrue(image_part["image_url"]["url"].startswith("data:image/png;base64,"))

    def test_screenshot_data_uri_formatting(self):
        # When already prefixed
        prefixed = "data:image/jpeg;base64,12345"
        self.assertEqual(format_screenshot_data_uri(prefixed), prefixed)

        # When raw base64
        raw = "abcde12345"
        self.assertEqual(format_screenshot_data_uri(raw), f"data:image/png;base64,{raw}")


class TestLLMPlannerActionConversion(unittest.IsolatedAsyncioTestCase):
    """Tests that model responses are correctly parsed into structured browser actions."""

    async def test_click_action_conversion(self):
        response_json = json.dumps({
            "action": {
                "type": "click",
                "target": {"id": "submit-btn", "selector": "#submit-btn", "x": 100.5, "y": 200.0}
            },
            "confidence": 0.95,
            "reason": "Submit button directly matches instruction."
        })
        provider = MockLLMProvider(response_json)
        planner = LLMPlanner(provider=provider)

        context = AgentContext(
            user_instruction="Submit the form",
            sanitized_screenshot="data:image/png;base64,mock",
            sanitized_dom="<button id='submit-btn'>Submit</button>",
            visual_elements=[{"type": "button", "id": "submit-btn"}]
        )

        result = await planner.plan(context)
        self.assertEqual(result.action["type"], "click")
        self.assertEqual(result.action["target"]["id"], "submit-btn")
        self.assertEqual(result.confidence, 0.95)
        self.assertTrue(result.is_high_confidence)
        self.assertIn("Submit button", result.reason)

    async def test_scroll_action_conversion(self):
        response_json = json.dumps({
            "action": {
                "type": "scroll",
                "target": {"direction": "down", "amount": 500}
            },
            "confidence": 0.92,
            "reason": "Scrolling down to view more content."
        })
        provider = MockLLMProvider(response_json)
        planner = LLMPlanner(provider=provider)

        context = AgentContext(
            user_instruction="Scroll down a bit",
            sanitized_screenshot="data:image/png;base64,mock",
            sanitized_dom="<div>Long page</div>",
            visual_elements=[]
        )

        result = await planner.plan(context)
        self.assertEqual(result.action["type"], "scroll")
        self.assertEqual(result.action["target"]["direction"], "down")
        self.assertEqual(result.action["target"]["amount"], 500)
        self.assertEqual(result.confidence, 0.92)

    async def test_type_action_conversion(self):
        response_json = json.dumps({
            "action": {
                "type": "type",
                "target": {"id": "search-input", "selector": "input#search-input"},
                "text": "privacy preserving agent"
            },
            "confidence": 0.96,
            "reason": "Search input box identified in DOM."
        })
        provider = MockLLMProvider(response_json)
        planner = LLMPlanner(provider=provider)

        context = AgentContext(
            user_instruction="Search for privacy preserving agent",
            sanitized_screenshot="data:image/png;base64,mock",
            sanitized_dom="<input id='search-input' />",
            visual_elements=[{"type": "input", "id": "search-input"}]
        )

        result = await planner.plan(context)
        self.assertEqual(result.action["type"], "type")
        self.assertEqual(result.action["text"], "privacy preserving agent")
        self.assertEqual(result.action["target"]["id"], "search-input")
        self.assertEqual(result.confidence, 0.96)

    async def test_navigate_action_conversion(self):
        response_json = json.dumps({
            "action": {
                "type": "navigate",
                "target": {"url": "https://example.com/login"}
            },
            "confidence": 0.98,
            "reason": "User requested navigation to login page."
        })
        provider = MockLLMProvider(response_json)
        planner = LLMPlanner(provider=provider)

        context = AgentContext(
            user_instruction="Go to https://example.com/login",
            sanitized_screenshot="data:image/png;base64,mock",
            sanitized_dom="",
            visual_elements=[]
        )

        result = await planner.plan(context)
        self.assertEqual(result.action["type"], "navigate")
        self.assertEqual(result.action["target"]["url"], "https://example.com/login")
        self.assertEqual(result.confidence, 0.98)

    async def test_markdown_codeblock_stripping(self):
        """Model may return JSON enclosed in ```json ... ``` blocks."""
        raw = "```json\n{\"action\": {\"type\": \"navigate\", \"target\": {\"url\": \"https://example.com\"}}, \"confidence\": 0.90, \"reason\": \"nav\"}\n```"
        provider = MockLLMProvider(raw)
        planner = LLMPlanner(provider=provider)

        context = AgentContext(
            user_instruction="visit example.com",
            sanitized_screenshot="data:image/png;base64,mock",
            sanitized_dom="",
            visual_elements=[]
        )

        result = await planner.plan(context)
        self.assertEqual(result.action["type"], "navigate")
        self.assertEqual(result.confidence, 0.90)

    async def test_low_confidence_action(self):
        """Action with confidence below 0.80 should be faithfully preserved."""
        response_json = json.dumps({
            "action": {
                "type": "click",
                "target": {"id": "ambiguous-btn"}
            },
            "confidence": 0.65,
            "reason": "Not completely certain which button was requested."
        })
        provider = MockLLMProvider(response_json)
        planner = LLMPlanner(provider=provider)

        context = AgentContext(
            user_instruction="click that thing",
            sanitized_screenshot="data:image/png;base64,mock",
            sanitized_dom="<button id='b1'>1</button><button id='b2'>2</button>",
            visual_elements=[]
        )

        result = await planner.plan(context)
        self.assertEqual(result.confidence, 0.65)
        self.assertFalse(result.is_high_confidence)


class TestLLMPlannerErrorHandling(unittest.IsolatedAsyncioTestCase):
    """Tests error and edge-case handling in LLMPlanner."""

    async def test_malformed_json_raises_value_error(self):
        provider = MockLLMProvider("Not JSON at all")
        planner = LLMPlanner(provider=provider)
        context = AgentContext(
            user_instruction="do something",
            sanitized_screenshot="data:image/png;base64,mock",
            sanitized_dom="",
            visual_elements=[]
        )
        with self.assertRaises(ValueError):
            await planner.plan(context)

    async def test_unsupported_action_type_raises_value_error(self):
        bad_json = json.dumps({
            "action": {"type": "drag_and_drop", "target": {}},
            "confidence": 0.9,
            "reason": "unsupported"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        context = AgentContext(user_instruction="drag", sanitized_screenshot="mock", sanitized_dom="")
        with self.assertRaises(ValueError):
            await planner.plan(context)

    async def test_missing_action_dict_raises_value_error(self):
        bad_json = json.dumps({"confidence": 0.9, "reason": "missing action"})
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        context = AgentContext(user_instruction="click", sanitized_screenshot="mock", sanitized_dom="")
        with self.assertRaises(ValueError):
            await planner.plan(context)

    async def test_confidence_out_of_range_raises_value_error(self):
        bad_json = json.dumps({
            "action": {"type": "click", "target": {"id": "btn"}},
            "confidence": 1.5,
            "reason": "invalid confidence"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        context = AgentContext(user_instruction="click", sanitized_screenshot="mock", sanitized_dom="")
        with self.assertRaises(ValueError):
            await planner.plan(context)

    async def test_provider_failure_without_fallback_raises_provider_error(self):
        class FailingProvider(MockLLMProvider):
            async def call(self, messages):
                raise RuntimeError("API connection timeout")

        config = AgentConfig(api_key="sk-test", fallback_to_mock=False)
        planner = LLMPlanner(config=config, provider=FailingProvider())
        context = AgentContext(user_instruction="click", sanitized_screenshot="mock", sanitized_dom="")
        with self.assertRaises(ProviderError):
            await planner.plan(context)

    async def test_browser_agent_with_llm_planner(self):
        agent = BrowserAgent(planner=LLMPlanner())
        self.assertIsInstance(agent.planner, LLMPlanner)


if __name__ == "__main__":
    unittest.main()
