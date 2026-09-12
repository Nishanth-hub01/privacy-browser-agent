import { classifySensitiveElement } from "./domDetector";
import { detectPII } from "./piiDetector";
import { PIIType, PrivacyVerificationResult } from "./types";

const replacementFor = (type: PIIType): string =>
  type === "PASSWORD" ? "[REDACTED]" : `[${type}]`;

function uniqueTypes(types: PIIType[]): PIIType[] {
  return [...new Set(types)];
}

export function verifySanitizedText(text: string): PrivacyVerificationResult {
  const remainingTextTypes = uniqueTypes(
    detectPII(text).map((match) => match.type)
  );

  return {
    privacyPassed: remainingTextTypes.length === 0,
    remainingTextTypes,
    remainingDOMTypes: [],
  };
}

export function verifySanitizedDOM(root: Document): PrivacyVerificationResult {
  const serializedDOM = root.documentElement?.outerHTML || "";
  const remainingTextTypes = detectPII(serializedDOM).map(
    (match) => match.type
  );
  const remainingDOMTypes: PIIType[] = [];

  root.querySelectorAll("input, textarea, select").forEach((element) => {
    const sensitiveType = classifySensitiveElement(element);

    if (!sensitiveType) {
      return;
    }

    const control = element as HTMLInputElement | HTMLTextAreaElement;
    const value =
      control.value ||
      element.getAttribute("value") ||
      (element.tagName.toLowerCase() === "textarea"
        ? element.textContent || ""
        : "");

    if (value.trim() && value !== replacementFor(sensitiveType)) {
      remainingDOMTypes.push(sensitiveType);
    }
  });

  const uniqueRemainingTextTypes = uniqueTypes(remainingTextTypes);
  const uniqueRemainingDOMTypes = uniqueTypes(remainingDOMTypes);

  return {
    privacyPassed:
      uniqueRemainingTextTypes.length === 0 &&
      uniqueRemainingDOMTypes.length === 0,
    remainingTextTypes: uniqueRemainingTextTypes,
    remainingDOMTypes: uniqueRemainingDOMTypes,
  };
}

export function verifyPrivacy(
  sanitizedText: string,
  sanitizedDOM?: Document
): PrivacyVerificationResult {
  const textResult = verifySanitizedText(sanitizedText);

  if (!sanitizedDOM) {
    return textResult;
  }

  const domResult = verifySanitizedDOM(sanitizedDOM);

  return {
    privacyPassed:
      textResult.privacyPassed && domResult.privacyPassed,
    remainingTextTypes: uniqueTypes([
      ...textResult.remainingTextTypes,
      ...domResult.remainingTextTypes,
    ]),
    remainingDOMTypes: domResult.remainingDOMTypes,
  };
}