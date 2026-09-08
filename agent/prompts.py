"""System prompts and multimodal message formatting for VLM/LLM agent.

Per API_CONTRACT.md:
- Only sanitized inputs (screenshot, DOM, visual elements) and user instruction are sent.
- Raw private data is never sent.
- Supported actions: click, scroll, type, navigate.
- Confidence must be in [0.0, 1.0].
"""
import json
from typing import Any, Dict, List
from agent.context import AgentContext


SYSTEM_PROMPT = """You are a privacy-preserving Vision-Language Browser Automation Agent.
Your task is to analyze the user's natural language instruction and the provided SANITIZED browser context to plan the next single browser action.

### STRICT PRIVACY & SAFETY RULES:
1. All data provided to you has been sanitized by an on-device privacy pipeline.
2. Sensitive information (passwords, emails, phone numbers, faces, credit cards) has been redacted with placeholders like [REDACTED], [EMAIL], [PERSON], etc.
3. NEVER attempt to infer, guess, or output real sensitive credentials.

### SUPPORTED ACTIONS (choose exactly ONE action):
1. 'click' - Click an interactive UI element.
   Schema: {"type": "click", "target": {"id": "<optional dom id>", "selector": "<optional css selector>", "x": <optional float>, "y": <optional float>}}
   Provide at least one identifier in target (id, selector, or x/y coordinates).

2. 'scroll' - Scroll the browser viewport up or down.
   Schema: {"type": "scroll", "target": {"direction": "up" | "down", "amount": <integer pixels, e.g. 400>}}

3. 'type' - Enter text into an input field or textarea.
   Schema: {"type": "type", "target": {"id": "<optional id>", "selector": "<optional selector>"}, "text": "<string to type>"}

4. 'navigate' - Navigate to a specific URL.
   Schema: {"type": "navigate", "target": {"url": "<target url>"}}

### CONFIDENCE SCORING:
- Return a float between 0.0 and 1.0.
- Return >= 0.80 if the target element or action is clear and directly matches the user's instruction.
- Return < 0.80 if the target element cannot be found with high certainty, the DOM/screen is ambiguous, or clarification is required.

### RESPONSE FORMAT:
You must respond with ONLY a valid JSON object (no additional conversational text or markdown codeblocks outside JSON) with this exact schema:
{
  "action": {
    "type": "click" | "scroll" | "type" | "navigate",
    "target": { ... }
    // plus "text" if type == "type"
  },
  "confidence": <float between 0.0 and 1.0>,
  "reason": "<clear explanation of why this action was selected based on the sanitized context>"
}
"""


def format_screenshot_data_uri(screenshot: str) -> str:
    """Ensures base64 screenshot is properly formatted as a data URI."""
    screenshot = screenshot.strip()
    if screenshot.startswith("data:image/"):
        return screenshot
    return f"data:image/png;base64,{screenshot}"


def build_multimodal_messages(context: AgentContext, dom_char_limit: int = 25000) -> List[Dict[str, Any]]:
    """Constructs the chat completion messages payload including all 4 required inputs:

    1. user_instruction
    2. sanitized_screenshot (as image_url for vision)
    3. sanitized_dom (formatted text)
    4. visual_elements (structured JSON)

    Args:
        context: Sanitized multimodal context from the browser.
        dom_char_limit: Maximum characters of sanitized DOM to include to protect context window.

    Returns:
        List of message dicts formatted for OpenAI-compatible VLM/LLM APIs.
    """
    # 1. Format visual elements
    elements_json = json.dumps(context.visual_elements, indent=2) if context.visual_elements else "[]"

    # 2. Format sanitized DOM with length safeguard
    dom = context.sanitized_dom or ""
    if len(dom) > dom_char_limit:
        dom_text = dom[:dom_char_limit] + f"\n... [DOM truncated: total {len(dom)} characters] ..."
    else:
        dom_text = dom

    # 3. Assemble text prompt with sanitized inputs
    user_text_prompt = (
        f"USER INSTRUCTION:\n{context.user_instruction}\n\n"
        f"DETECTED VISUAL ELEMENTS (Sanitized):\n{elements_json}\n\n"
        f"SANITIZED DOM HTML:\n{dom_text}\n\n"
        "A redacted, sanitized screenshot of the current page is attached.\n"
        "Analyze the visual elements, DOM, screenshot, and instruction, and plan the next action in JSON."
    )

    content_parts: List[Dict[str, Any]] = [
        {"type": "text", "text": user_text_prompt}
    ]

    # 4. Attach sanitized screenshot if available
    if context.sanitized_screenshot and len(context.sanitized_screenshot.strip()) > 10:
        data_uri = format_screenshot_data_uri(context.sanitized_screenshot)
        content_parts.append({
            "type": "image_url",
            "image_url": {
                "url": data_uri,
                "detail": "auto",
            },
        })

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content_parts},
    ]
