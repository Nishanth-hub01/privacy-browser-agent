import {
  RasterImage,
  ScreenshotPrivacyVerificationResult,
  VisualPrivacyRegion,
} from "./types";

export function verifySanitizedScreenshot(
  original: RasterImage,
  sanitized: RasterImage,
  detections: VisualPrivacyRegion[],
  redactedRegions: VisualPrivacyRegion[]
): ScreenshotPrivacyVerificationResult {
  const sameDimensions =
    original.width === sanitized.width && original.height === sanitized.height;
  const sameBuffer = original.data === sanitized.data;
  const countsMatch = detections.length === redactedRegions.length;
  const imageWasCopied = !sameBuffer;

  return {
    privacyPassed:
      sameDimensions && countsMatch && imageWasCopied,
    detectedRegionCount: detections.length,
    redactedRegionCount: redactedRegions.length,
  };
}