import { detectPII } from "./piiDetector";
import { redactText } from "./redactor";
import { PrivacyResult } from "./types";

export { sanitizeDOM } from "./domSanitizer";
export {
  verifyPrivacy,
  verifySanitizedDOM,
  verifySanitizedText,
} from "./privacyVerifier";
export { redactScreenshot } from "./screenshotRedactor";
export {
  detectAndRedactScreenshot,
  normalizeVisualDetections,
} from "./visualDetector";
export { OnnxUltraFaceDetector } from "./onnxFaceDetector";
export { preprocessUltraFace } from "./visionPreprocessor";
export { decodeUltraFaceOutputs } from "./ultrafaceDecoder";
export { createOnnxSessionFactory } from "./onnxRuntime";
export { processScreenshotPrivacy } from "./screenshotPrivacyPipeline";
export { verifySanitizedScreenshot } from "./screenshotPrivacyVerifier";

export type { DOMSanitizationResult } from "./types";
export type { PrivacyVerificationResult } from "./types";
export type {
  RasterImage,
  ScreenshotRedactionMethod,
  ScreenshotRedactionOptions,
  ScreenshotRedactionResult,
  VisualPrivacyDetector,
  VisualPrivacyRegion,
  VisualPrivacyRegionType,
  VisualDetectionResult,
  VisualRedactionResult,
  LocalVisionSession,
  LocalVisionSessionFactory,
  PreparedVisionInput,
  UltraFaceDetectorOptions,
  VisionExecutionProvider,
  ScreenshotPrivacyPipelineOptions,
  ScreenshotPrivacyPipelineResult,
  ScreenshotPrivacyVerificationResult,
} from "./types";

export function sanitizeText(text: string): PrivacyResult {
  const matches = detectPII(text);
  const sanitizedText = redactText(text, matches);

  const leakedSensitiveData = matches.some((match) => {
    const original = text.slice(match.start, match.end);
    return original.trim().length > 0 && sanitizedText.includes(original);
  });
  const safeMatches = matches.map((match) => ({
    ...match,
    value: match.replacement,
  }));

  return {
    sanitizedText,
    matches: safeMatches,
    domFindings: [],
    privacyPassed: !leakedSensitiveData,
  };
}
