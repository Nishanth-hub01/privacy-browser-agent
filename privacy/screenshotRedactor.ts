import {
  RasterImage,
  ScreenshotRedactionMethod,
  ScreenshotRedactionOptions,
  ScreenshotRedactionResult,
  VisualPrivacyRegion,
} from "./types";

const CHANNELS_PER_PIXEL = 4;

function assertImage(image: RasterImage): void {
  if (
    !Number.isInteger(image.width) ||
    !Number.isInteger(image.height) ||
    image.width <= 0 ||
    image.height <= 0
  ) {
    throw new RangeError("Raster image dimensions must be positive integers.");
  }

  const expectedLength = image.width * image.height * CHANNELS_PER_PIXEL;

  if (image.data.length !== expectedLength) {
    throw new RangeError("Raster image data length does not match dimensions.");
  }
}

function clampRegion(
  region: VisualPrivacyRegion,
  image: RasterImage
): VisualPrivacyRegion | undefined {
  if (
    !Number.isFinite(region.x) ||
    !Number.isFinite(region.y) ||
    !Number.isFinite(region.width) ||
    !Number.isFinite(region.height) ||
    !Number.isFinite(region.confidence) ||
    region.width <= 0 ||
    region.height <= 0
  ) {
    return undefined;
  }

  const right = region.x + region.width;
  const bottom = region.y + region.height;

  if (!Number.isFinite(right) || !Number.isFinite(bottom)) {
    return undefined;
  }

  const left = Math.max(0, Math.min(image.width, Math.floor(region.x)));
  const top = Math.max(0, Math.min(image.height, Math.floor(region.y)));
  const clampedRight = Math.max(
    0,
    Math.min(image.width, Math.ceil(right))
  );
  const clampedBottom = Math.max(
    0,
    Math.min(image.height, Math.ceil(bottom))
  );

  if (clampedRight <= left || clampedBottom <= top) {
    return undefined;
  }

  return {
    type: region.type,
    x: left,
    y: top,
    width: clampedRight - left,
    height: clampedBottom - top,
    confidence: Math.max(0, Math.min(1, region.confidence)),
  };
}

function pixelOffset(x: number, y: number, width: number): number {
  return (y * width + x) * CHANNELS_PER_PIXEL;
}

function blackout(
  image: RasterImage,
  output: Uint8ClampedArray,
  region: VisualPrivacyRegion
): void {
  const right = region.x + region.width;
  const bottom = region.y + region.height;

  for (let y = region.y; y < bottom; y += 1) {
    for (let x = region.x; x < right; x += 1) {
      const offset = pixelOffset(x, y, image.width);
      output[offset] = 0;
      output[offset + 1] = 0;
      output[offset + 2] = 0;
      output[offset + 3] = 255;
    }
  }
}

function blur(
  image: RasterImage,
  source: Uint8ClampedArray,
  output: Uint8ClampedArray,
  region: VisualPrivacyRegion,
  radius: number
): void {
  const right = region.x + region.width;
  const bottom = region.y + region.height;

  for (let y = region.y; y < bottom; y += 1) {
    for (let x = region.x; x < right; x += 1) {
      const targetOffset = pixelOffset(x, y, image.width);
      let red = 0;
      let green = 0;
      let blue = 0;
      let alpha = 0;
      let samples = 0;

      for (let sampleY = Math.max(0, y - radius); sampleY <= Math.min(image.height - 1, y + radius); sampleY += 1) {
        for (let sampleX = Math.max(0, x - radius); sampleX <= Math.min(image.width - 1, x + radius); sampleX += 1) {
          const sourceOffset = pixelOffset(sampleX, sampleY, image.width);
          red += source[sourceOffset];
          green += source[sourceOffset + 1];
          blue += source[sourceOffset + 2];
          alpha += source[sourceOffset + 3];
          samples += 1;
        }
      }

      output[targetOffset] = red / samples;
      output[targetOffset + 1] = green / samples;
      output[targetOffset + 2] = blue / samples;
      output[targetOffset + 3] = alpha / samples;
    }
  }
}

export function redactScreenshot(
  image: RasterImage,
  regions: VisualPrivacyRegion[],
  options: ScreenshotRedactionOptions = {}
): ScreenshotRedactionResult {
  assertImage(image);

  const method: ScreenshotRedactionMethod = options.method || "BLACKOUT";
  const blurRadius = Number.isInteger(options.blurRadius)
    ? Math.max(1, Math.min(20, options.blurRadius as number))
    : 2;
  const validRegions = regions
    .map((region) => clampRegion(region, image))
    .filter((region): region is VisualPrivacyRegion => region !== undefined);
  const output = new Uint8ClampedArray(image.data);
  const source = new Uint8ClampedArray(image.data);

  for (const region of validRegions) {
    if (method === "BLUR") {
      blur(image, source, output, region, blurRadius);
    } else {
      blackout(image, output, region);
    }
  }

  return {
    image: {
      width: image.width,
      height: image.height,
      data: output,
    },
    redactedRegions: validRegions,
  };
}