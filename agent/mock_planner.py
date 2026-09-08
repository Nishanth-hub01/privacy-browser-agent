"""Deterministic mock planner implementing the four actions in API_CONTRACT.md."""
import re
from typing import Any, Dict, Optional, Tuple
from agent.base import BasePlanner
from agent.context import AgentContext
from agent.actions import ActionResult


class MockPlanner(BasePlanner):
    """Rule-based deterministic planner for testing and Phase 3 development.

    Parses user instructions and inspects visual elements to return structured
    actions (click, scroll, type, navigate) without calling external AI APIs.
    """

    async def plan(self, context: AgentContext) -> ActionResult:
        """Determines the appropriate browser action based on instruction and context."""
        instruction = context.user_instruction.strip().lower()

        # 1. Check for Navigation intent
        nav_action = self._check_navigate(instruction)
        if nav_action:
            return nav_action

        # 2. Check for Scroll intent
        scroll_action = self._check_scroll(instruction)
        if scroll_action:
            return scroll_action

        # 3. Check for Type / Input intent
        type_action = self._check_type(instruction, context.visual_elements)
        if type_action:
            return type_action

        # 4. Check for Click intent (or default action)
        return self._determine_click(instruction, context.visual_elements)

    def _check_navigate(self, instruction: str) -> Optional[ActionResult]:
        """Detects navigation requests (e.g. 'go to https://example.com')."""
        url_match = re.search(r"https?://[^\s]+", instruction)
        if url_match:
            url = url_match.group(0)
            return ActionResult(
                action={"type": "navigate", "target": {"url": url}},
                confidence=0.96,
                reason=f"Navigating to extracted URL: {url}",
            )

        nav_keywords = ["navigate to", "go to", "visit", "open url"]
        for kw in nav_keywords:
            if kw in instruction:
                remainder = instruction.split(kw, 1)[1].strip()
                url = remainder if remainder.startswith("http") else f"https://{remainder}"
                return ActionResult(
                    action={"type": "navigate", "target": {"url": url}},
                    confidence=0.92,
                    reason=f"Navigating to target URL: {url}",
                )
        return None

    def _check_scroll(self, instruction: str) -> Optional[ActionResult]:
        """Detects scrolling requests (e.g. 'scroll down', 'scroll up')."""
        if "scroll" in instruction or "page down" in instruction or "page up" in instruction:
            direction = "up" if "up" in instruction else "down"
            amount_match = re.search(r"\b(\d+)", instruction)
            amount = int(amount_match.group(1)) if amount_match else 600
            return ActionResult(
                action={"type": "scroll", "target": {"direction": direction, "amount": amount}},
                confidence=0.95,
                reason=f"Scrolling {direction} by {amount}px according to instruction.",
            )
        return None

    def _check_type(self, instruction: str, visual_elements: list) -> Optional[ActionResult]:
        """Detects typing requests (e.g. 'type hello in search', 'enter John')."""
        type_keywords = ["type", "enter", "fill", "write", "search for"]
        matched_kw = next((kw for kw in type_keywords if kw in instruction), None)
        if not matched_kw:
            return None

        # Extract text: prioritize quoted text, otherwise text following the keyword
        quote_match = re.search(r"['\"]([^'\"]+)['\"]", instruction)
        if quote_match:
            text = quote_match.group(1)
        else:
            after_kw = instruction.split(matched_kw, 1)[1].strip()
            # Remove filler words like 'into the field', 'in search', etc.
            text = re.sub(r"^(in|into|the|field|input|box)\s+", "", after_kw).strip()
            text = text.split(" in ")[0].split(" into ")[0].strip() or "test input"

        # Find best matching input element
        target = self._find_input_target(visual_elements)
        return ActionResult(
            action={"type": "type", "target": target, "text": text},
            confidence=0.94,
            reason=f"Typing '{text}' into matching input element.",
        )

    def _determine_click(self, instruction: str, visual_elements: list) -> ActionResult:
        """Determines target element for click action based on instruction."""
        if visual_elements:
            best_el, score = self._find_best_matching_element(instruction, visual_elements)
            if best_el:
                target = {
                    k: v for k, v in {
                        "id": best_el.get("id"),
                        "selector": best_el.get("selector") or (f"#{best_el.get('id')}" if best_el.get("id") else None),
                        "x": best_el.get("x"),
                        "y": best_el.get("y"),
                    }.items() if v is not None
                }
                label = best_el.get("label") or best_el.get("id") or best_el.get("type", "element")
                return ActionResult(
                    action={"type": "click", "target": target},
                    confidence=score,
                    reason=f"The '{label}' element matches the user's instruction.",
                )

        # Fallback when no visual elements or matches found
        return ActionResult(
            action={"type": "click", "target": {"id": "submit-btn", "selector": "#submit-btn"}},
            confidence=0.70,
            reason="No visual elements matched instruction; returning fallback action with low confidence.",
        )

    def _find_input_target(self, visual_elements: list) -> Dict[str, Any]:
        """Finds an input or textarea element from visual elements."""
        for el in visual_elements:
            el_type = str(el.get("type", "")).lower()
            if el_type in ("input", "textarea", "textbox", "search"):
                return {
                    k: v for k, v in {
                        "id": el.get("id"),
                        "selector": el.get("selector") or (f"#{el.get('id')}" if el.get("id") else None),
                    }.items() if v is not None
                }
        return {"id": "input-field", "selector": "input"}

    def _find_best_matching_element(self, instruction: str, visual_elements: list) -> Tuple[Optional[dict], float]:
        """Finds element with highest token match against user instruction."""
        words = set(re.findall(r"\w+", instruction))
        best_match = None
        best_score = 0.0

        for el in visual_elements:
            match_points = 0
            label = str(el.get("label", "")).lower()
            el_id = str(el.get("id", "")).lower()
            el_type = str(el.get("type", "")).lower()

            for w in words:
                if len(w) > 2:
                    if w in label:
                        match_points += 3
                    if w in el_id:
                        match_points += 2
                    if w in el_type:
                        match_points += 1

            if match_points > best_score:
                best_score = match_points
                best_match = el

        if best_match and best_score > 0:
            return best_match, min(0.96, 0.85 + (best_score * 0.03))
        # Default to first element if any exist
        return visual_elements[0], 0.88
