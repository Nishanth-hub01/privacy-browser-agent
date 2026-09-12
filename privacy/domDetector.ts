import { DOMFinding, PIIType } from "./types";

export function classifySensitiveElement(element: Element): PIIType | undefined {
  const type = element.getAttribute("type")?.toLowerCase() || "";
  const name = element.getAttribute("name")?.toLowerCase() || "";
  const id = element.getAttribute("id")?.toLowerCase() || "";
  const placeholder =
    element.getAttribute("placeholder")?.toLowerCase() || "";
  const ariaLabel =
    element.getAttribute("aria-label")?.toLowerCase() || "";
  const autocomplete =
    element.getAttribute("autocomplete")?.toLowerCase() || "";

  const allAttributes = [
    type,
    name,
    id,
    placeholder,
    ariaLabel,
    autocomplete,
  ].join(" ");

  if (type === "password" || allAttributes.includes("password")) {
    return "PASSWORD";
  }

  if (type === "email" || allAttributes.includes("email")) {
    return "EMAIL";
  }

  if (name === "phone" || allAttributes.includes("phone") || allAttributes.includes("tel")) {
    return "PHONE";
  }

  if (name === "address" || allAttributes.includes("address") || allAttributes.includes("street")) {
    return "ADDRESS";
  }

  return undefined;
}

export function detectSensitiveDOM(root: Document): DOMFinding[] {
  const findings: DOMFinding[] = [];

  const elements = root.querySelectorAll("input, textarea, select");

  elements.forEach((element) => {
    const tagName = element.tagName.toLowerCase();

    const sensitiveType = classifySensitiveElement(element);

    if (sensitiveType) {
      findings.push({
        type: sensitiveType,
        element: tagName,
        attribute: sensitiveType.toLowerCase(),
        value: sensitiveType === "PASSWORD" ? "[REDACTED]" : `[${sensitiveType}]`,
      });
    }
  });

  return findings;
}