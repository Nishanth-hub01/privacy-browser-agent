import { PIIMatch, PIIType } from "./types";

export function detectPII(text: string): PIIMatch[] {
  const matches: PIIMatch[] = [];

  const patterns: { type: PIIType; regex: RegExp; replacement: string }[] = [
    {
      type: "PERSON",
      regex: /\b(?:Mr|Mrs|Ms|Dr)?[ \t]*[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){1,2}\b/g,
      replacement: "[PERSON]",
    },
    {
      type: "EMAIL",
      regex: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi,
      replacement: "[EMAIL]",
    },
    {
      type: "GOVERNMENT_ID",
      regex: /\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b|\b[A-Z]{2,5}[- ]?ID[- ]?[A-Z0-9-]{4,}\b/gi,
      replacement: "[GOVERNMENT_ID]",
    },
    {
      type: "CREDIT_CARD",
      regex: /(?<!\d)(?:\d[ -]?){13,19}(?!\d)/g,
      replacement: "[CREDIT_CARD]",
    },
    {
      type: "PHONE",
      regex: /\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b/g,
      replacement: "[PHONE]",
    },
    {
      type: "PASSWORD",
      regex: /(?:^|[\s:])(?:password|passwd|pwd)[\s:=]+([A-Za-z0-9!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?`~]{6,})/gi,
      replacement: "[REDACTED]",
    },
    {
      type: "ADDRESS",
      regex: /\b\d+\s+[A-Z][A-Za-z0-9.,\s-]*\b(?:Street|Road|Avenue|Lane|Boulevard|Drive|Way|Court|Parkway)\b/gi,
      replacement: "[ADDRESS]",
    },
  ];

  for (const pattern of patterns) {
    const regex = new RegExp(pattern.regex.source, pattern.regex.flags);
    let match: RegExpExecArray | null;

    while ((match = regex.exec(text)) !== null) {
      const value =
        pattern.type === "PASSWORD" ? match[1] ?? match[0] : match[0];
      const start =
        pattern.type === "PASSWORD"
          ? match.index + match[0].indexOf(value)
          : match.index;

      matches.push({
        type: pattern.type,
        start,
        end: start + value.length,
        value,
        replacement: pattern.replacement,
      });

      if (match[0].length === 0) {
        regex.lastIndex += 1;
      }
    }
  }

  // Keep the first match in source order and discard duplicates or overlaps.
  // Pattern order above is intentional: IDs and cards win over phone matches.
  const accepted: PIIMatch[] = [];

  for (const match of matches.sort((a, b) => {
    if (a.start !== b.start) {
      return a.start - b.start;
    }

    return b.end - b.start - (a.end - a.start);
  })) {
    const previous = accepted[accepted.length - 1];

    if (previous && match.start < previous.end) {
      continue;
    }

    if (
      !accepted.some(
        (acceptedMatch) =>
          acceptedMatch.start === match.start &&
          acceptedMatch.end === match.end &&
          acceptedMatch.type === match.type
      )
    ) {
      accepted.push(match);
    }
  }

  return accepted;
}
