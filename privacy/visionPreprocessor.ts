import { PreparedVisionInput, RasterImage } from "./types";
import {
  ULTRAFACE_INPUT_HEIGHT,
  ULTRAFACE_INPUT_SHAPE,
  ULTRAFACE_INPUT_WIDTH,
} from "./ultrafaceContract";

const CHANNELS_PER_PIXEL = 4;
const MODEL_CHANNELS = 3;

function assertRasterImage(image: RasterImage): void {
  if (
    !Number.isInteger(image.width) ||
    !Number.isInteger(image.height) ||
    image.width <= 0 ||
    image.height <= 0 ||
    image.data.length !== image.width * image.height * CHANNELS_PER_PIXEL
  ) {
    throw new RangeError("Invalid RGBA raster image.");
  }
}

function sourcePixel(
  image: RasterImage,
  x: number,
  y: number,
  channel: number
): number {
  const sourceX = Math.min(image.width - 1, Math.floor(x));
  const sourceY = Math.min(image.height - 1, Math.floor(y));
  return image.data[(sourceY * image.width + sourceX) * CHANNELS_PER_PIXEL + channel];
}

export function preprocessUltraFace(image: RasterImage): PreparedVisionInput {
  assertRasterImage(image);
  const data = new Float32Array(
    MODEL_CHANNELS * ULTRAFACE_INPUT_HEIGHT * ULTRAFACE_INPUT_WIDTH
  );
  const scaleX = image.width / ULTRAFACE_INPUT_WIDTH;
  const scaleY = image.height / ULTRAFACE_INPUT_HEIGHT;

  for (let channel = 0; channel < MODEL_CHANNELS; channel += 1) {
    for (let y = 0; y < ULTRAFACE_INPUT_HEIGHT; y += 1) {
      for (let x = 0; x < ULTRAFACE_INPUT_WIDTH; x += 1) {
        const pixel = sourcePixel(image, x * scaleX, y * scaleY, channel);
        const outputIndex =
          channel * ULTRAFACE_INPUT_HEIGHT * ULTRAFACE_INPUT_WIDTH +
          y * ULTRAFACE_INPUT_WIDTH +
          x;
        data[outputIndex] = (pixel - 127) / 128;
      }
    }
  }

  return { data, shape: ULTRAFACE_INPUT_SHAPE };
}