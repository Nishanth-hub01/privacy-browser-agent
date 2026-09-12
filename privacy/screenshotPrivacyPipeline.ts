import { redactScreenshot } from "./screenshotRedactor";
import { normalizeVisualDetections } from "./visualDetector";
import { verifySanitizedScreenshot } from "./screenshotPrivacyVerifier";
import {
  RasterImage,
  ScreenshotPrivacyPipelineOptions,
  ScreenshotPrivacyPipelineResult,
  VisualPrivacyDetector,
} from "./types";

export async function processScreenshotPrivacy(
  detector: VisualPrivacyDetector,
  image: RasterImage,
  options: ScreenshotPrivacyPipelineOptions = {}
): Promise<ScreenshotPrivacyPipelineResult> {
  try {
    const minimumConfidence = Math.max(
      0,
      Math.min(1, options.minimumConfidence ?? 0)
    );
    const rawDetections = await detector.detect(image);
    const detections = normalizeVisualDetections(image, rawDetections).filter(
      (detection) => detection.confidence >= minimumConfidence
    );
    const redaction = redactScreenshot(image, detections, options.redaction);
    const verification = verifySanitizedScreenshot(
      image,
      redaction.image,
      detections,
      redaction.redactedRegions
    );

    if (!verification.privacyPassed) {
      throw new Error("Screenshot privacy verification failed.");
    }

    return {
      sanitizedImage: redaction.image,
      detections,
      redactedRegions: redaction.redactedRegions,
      verification,
      privacyPassed: true,
    };
  } catch {
    throw new Error("Screenshot privacy processing failed.");
  }
}