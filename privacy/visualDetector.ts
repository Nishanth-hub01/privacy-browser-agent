import { redactScreenshot } from "./screenshotRedactor";
import {
  RasterImage,
  ScreenshotRedactionOptions,
  VisualPrivacyDetector,
  VisualPrivacyRegion,
  VisualRedactionResult,
} from "./types";

function isSupportedRegionType(
  type: VisualPrivacyRegion["type"]
): boolean {
  return type === "FACE" || type === "SENSITIVE_REGION";
}

function normalizeDetection(
  detection: VisualPrivacyRegion,
  image: RasterImage
): VisualPrivacyRegion | undefined {
  if (
    !isSupportedRegionType(detection.type) ||
    !Number.isFinite(detection.x) ||
    !Number.isFinite(detection.y) ||
    !Number.isFinite(detection.width) ||
    !Number.isFinite(detection.height) ||
    !Number.isFinite(detection.confidence) ||
    detection.width <= 0 ||
    detection.height <= 0
  ) {
    return undefined;
  }

  const right = detection.x + detection.width;
  const bottom = detection.y + detection.height;

  if (!Number.isFinite(right) || !Number.isFinite(bottom)) {
    return undefined;
  }

  const left = Math.max(0, Math.min(image.width, Math.floor(detection.x)));
  const top = Math.max(0, Math.min(image.height, Math.floor(detection.y)));
  const clampedRight = Math.max(0, Math.min(image.width, Math.ceil(right)));
  const clampedBottom = Math.max(
    0,
    Math.min(image.height, Math.ceil(bottom))
  );

  if (clampedRight <= left || clampedBottom <= top) {
    return undefined;
  }

  return {
    type: detection.type,
    x: left,
    y: top,
    width: clampedRight - left,
    height: clampedBottom - top,
    confidence: Math.max(0, Math.min(1, detection.confidence)),
  };
}

export function normalizeVisualDetections(
  image: RasterImage,
  detections: VisualPrivacyRegion[]
): VisualPrivacyRegion[] {
  return detections
    .map((detection) => normalizeDetection(detection, image))
    .filter((detection): detection is VisualPrivacyRegion => detection !== undefined);
}

export async function detectAndRedactScreenshot(
  detector: VisualPrivacyDetector,
  image: RasterImage,
  options: ScreenshotRedactionOptions = {}
): Promise<VisualRedactionResult> {
  const detections = normalizeVisualDetections(image, await detector.detect(image));
  const redaction = redactScreenshot(image, detections, options);

  return {
    image: redaction.image,
    redactedRegions: redaction.redactedRegions,
    detections,
  };
}