import { classifySensitiveElement, detectSensitiveDOM } from "./domDetector";
import { detectPII } from "./piiDetector";
import { redactText } from "./redactor";
import { DOMSanitizationResult, PIIType } from "./types";

const replacementFor = (type: PIIType): string =>
  type === "PASSWORD" ? "[REDACTED]" : `[${type}]`;

const textAttributes = new Set([
  "aria-label",
  "placeholder",
  "title",
  "alt",
  "value",
]);

function sanitizeString(value: string): string {
  const domMatches = detectPII(value).filter(
    (match) => match.type !== "PERSON"
  );

  return redactText(value, domMatches);
}

export function sanitizeDOM(root: Document): DOMSanitizationResult {
  const sourceElements = Array.from(
    root.querySelectorAll("input, textarea, select")
  );
  const clone = root.cloneNode(true) as Document;
  const sanitizedElements = Array.from(
    clone.querySelectorAll("input, textarea, select")
  );
  const originalSensitiveValues: string[] = [];

  sourceElements.forEach((sourceElement, index) => {
    const sanitizedElement = sanitizedElements[index];
    const sensitiveType = classifySensitiveElement(sourceElement);

    if (!sanitizedElement || !sensitiveType) {
      return;
    }

    const sourceValue =
      (sourceElement as HTMLInputElement | HTMLTextAreaElement).value ||
      sourceElement.getAttribute("value") ||
      "";

    if (sourceValue) {
      originalSensitiveValues.push(sourceValue);
    }

    const replacement = replacementFor(sensitiveType);

    if (sanitizedElement.tagName.toLowerCase() === "select") {
      sanitizedElement
        .querySelectorAll("option[selected]")
        .forEach((option) => option.setAttribute("value", replacement));
    } else {
      const control = sanitizedElement as HTMLInputElement | HTMLTextAreaElement;
      control.value = replacement;
      control.setAttribute("value", replacement);

      if (sanitizedElement.tagName.toLowerCase() === "textarea") {
        sanitizedElement.textContent = replacement;
      }
    }
  });

  clone.querySelectorAll("*").forEach((element) => {
    Array.from(element.attributes).forEach((attribute) => {
      if (textAttributes.has(attribute.name) || attribute.name.startsWith("data-")) {
        attribute.value = sanitizeString(attribute.value);
      }
    });
  });

  const walker = clone.createTreeWalker(clone, 4);
  const textNodes: Text[] = [];
  let currentNode: Node | null;

  while ((currentNode = walker.nextNode())) {
    textNodes.push(currentNode as Text);
  }

  textNodes.forEach((node) => {
    node.nodeValue = sanitizeString(node.nodeValue || "");
  });

  const findings = detectSensitiveDOM(clone);
  const sanitizedDOM = clone.documentElement?.outerHTML || "";
  const privacyPassed = originalSensitiveValues.every(
    (value) => value.length === 0 || !sanitizedDOM.includes(value)
  );

  return {
    sanitizedDOM,
    findings,
    privacyPassed,
  };
}