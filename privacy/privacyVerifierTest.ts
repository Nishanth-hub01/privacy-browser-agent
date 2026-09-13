import { sanitizeText } from "./index";
import { verifySanitizedText } from "./privacyVerifier";

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message);
  }
}

function main(): void {
  for (const token of [
    "[REDACTED]",
    "[EMAIL]",
    "[PHONE]",
    "[ADDRESS]",
    "[PERSON]",
  ]) {
    const sanitized = sanitizeText(`password: ${token}`);
    assert(sanitized.matches.length === 0, `${token} was detected as PII.`);
    assert(sanitized.privacyPassed, `${token} failed sanitization.`);
    assert(
      verifySanitizedText(sanitized.sanitizedText).privacyPassed,
      `${token} failed verification.`
    );
  }

  const realPassword = sanitizeText("password: RealSecret123!");
  assert(
    realPassword.matches.some((match) => match.type === "PASSWORD"),
    "Real password was not detected."
  );
  assert(
    !realPassword.sanitizedText.includes("RealSecret123!"),
    "Real password was not redacted."
  );

  console.log("Privacy verification tests passed");
}

main();