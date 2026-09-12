import { createSyntheticVisualDetector } from "./syntheticVisualDetector";
import { processScreenshotPrivacy } from "./screenshotPrivacyPipeline";
import { RasterImage, VisualPrivacyRegion } from "./types";

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message);
  }
}

function pixelOffset(x: number, y: number, width: number): number {
  return (y * width + x) * 4;
}

async function main(): Promise<void> {
  const image: RasterImage = {
    width: 8,
    height: 8,
    data: new Uint8ClampedArray(8 * 8 * 4).fill(200),
  };

  for (let index = 3; index < image.data.length; index += 4) {
    image.data[index] = 255;
  }

  const originalData = new Uint8ClampedArray(image.data);
  const detections: VisualPrivacyRegion[] = [
    { type: "FACE", x: 1, y: 1, width: 2, height: 2, confidence: 0.95 },
    { type: "FACE", x: 5, y: 5, width: 4, height: 4, confidence: 0.9 },
    { type: "FACE", x: 2, y: 2, width: 2, height: 2, confidence: 0.2 },
    { type: "FACE", x: 0, y: 0, width: 0, height: 2, confidence: 1 },
  ];

  const result = await processScreenshotPrivacy(
    createSyntheticVisualDetector(detections),
    image,
    { minimumConfidence: 0.5 }
  );

  assert(result.privacyPassed, "Expected screenshot privacy verification to pass.");
  assert(result.detections.length === 2, "Expected two accepted face detections.");
  assert(result.redactedRegions.length === 2, "Expected two redacted regions.");
  assert(result.sanitizedImage.data !== image.data, "Expected an immutable output buffer.");
  assert(image.data.every((value, index) => value === originalData[index]), "Original image was modified.");
  assert(result.sanitizedImage.data[pixelOffset(1, 1, image.width)] === 0, "First face was not redacted.");
  assert(result.sanitizedImage.data[pixelOffset(7, 7, image.width)] === 0, "Clamped face was not redacted.");
  assert(result.sanitizedImage.data[pixelOffset(0, 7, image.width)] === 200, "Non-redacted area changed.");

  const emptyResult = await processScreenshotPrivacy(
    createSyntheticVisualDetector([]),
    image
  );
  assert(emptyResult.privacyPassed, "Empty detection result should pass.");
  assert(emptyResult.sanitizedImage.data.every((value, index) => value === originalData[index]), "Empty detection changed image.");

  const logs: unknown[] = [];
  const originalLog = console.log;
  console.log = (...args: unknown[]) => logs.push(args);
  await processScreenshotPrivacy(
    createSyntheticVisualDetector([
      { type: "FACE", x: 1, y: 1, width: 2, height: 2, confidence: 1 },
    ]),
    image
  );
  console.log = originalLog;
  assert(logs.length === 0, "Screenshot pipeline wrote to console.");

  console.log("Screenshot privacy pipeline tests passed");
}

void main();