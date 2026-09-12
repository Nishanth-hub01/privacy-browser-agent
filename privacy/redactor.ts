import { PIIMatch } from "./types";

export function redactText(text: string, matches: PIIMatch[]): string {
  if (matches.length === 0) {
    return text;
  }

  const sortedMatches = [...matches].sort((a, b) => b.start - a.start);
  let result = text;
  let nextStart = text.length;

  for (const match of sortedMatches) {
    if (
      match.start < 0 ||
      match.end <= match.start ||
      match.end > text.length ||
      match.end > nextStart
    ) {
      continue;
    }

    result =
      result.slice(0, match.start) +
      match.replacement +
      result.slice(match.end);
    nextStart = match.start;
  }

  return result;
}
