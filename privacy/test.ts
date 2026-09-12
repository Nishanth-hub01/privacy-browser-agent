import { sanitizeText } from "./index";

const input = `
Name: John Smith
Email: john@example.com
Phone: 9876543210
`;

const result = sanitizeText(input);

console.log("Sanitized:");
console.log(result.sanitizedText);

console.log("Detected PII types:");
console.log(result.matches.map((match) => match.type));