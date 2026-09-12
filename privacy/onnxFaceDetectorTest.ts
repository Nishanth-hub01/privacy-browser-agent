import { redactScreenshot } from "./screenshotRedactor";
import { OnnxUltraFaceDetector } from "./onnxFaceDetector";
import { decodeUltraFaceOutputs } from "./ultrafaceDecoder";
import { preprocessUltraFace } from "./visionPreprocessor";
import { LocalVisionSessionFactory, RasterImage } from "./types";

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message);
  }
}

function assertClose(actual: number, expected: number, message: string): void {
  assert(Math.abs(actual - expected) < 0.0001, message);
}

const image: RasterImage = {
  width: 640,
  height: 480,
  data: new Uint8ClampedArray(640 * 480 * 4).fill(255),
};

const scores = new Float32Array(4420 * 2);
const boxes = new Float32Array(4420 * 4);
scores[1] = 0.95;
boxes[0] = 0.1;
boxes[1] = 0.2;
boxes[2] = 0.4;
boxes[3] = 0.6;

const outputs = {
  scores: { type: "float32", dims: [1, 4420, 2], data: scores },
  boxes: { type: "float32", dims: [1, 4420, 4], data: boxes },
};

const sessionFactory: LocalVisionSessionFactory = {
  async create() {
    return {
      provider: "wasm",
      inputNames: ["input"],
      outputNames: ["scores", "boxes"],
      inputMetadata: [
        { name: "input", type: "float32", shape: [1, 3, 240, 320] },
      ],
      outputMetadata: [
        { name: "scores", type: "float32", shape: [1, 4420, 2] },
        { name: "boxes", type: "float32", shape: [1, 4420, 4] },
      ],
      async run() {
        return outputs;
      },
      async release() {},
    };
  },
};

async function main(): Promise<void> {
  const prepared = preprocessUltraFace(image);
  assert(prepared.shape.join(",") === "1,3,240,320", "Unexpected tensor shape.");
  assert(prepared.data instanceof Float32Array, "Tensor data is not float32.");
  assert(prepared.data.length === 1 * 3 * 240 * 320, "Unexpected tensor length.");
  assertClose(prepared.data[0], 1, "Unexpected tensor normalization.");

  const decoded = decodeUltraFaceOutputs(outputs, image.width, image.height);
  assert(decoded.length === 1, "Expected one decoded face.");
  assert(decoded[0].type === "FACE", "Expected a FACE detection.");
  assertClose(decoded[0].x, 64, "Unexpected face x coordinate.");
  assertClose(decoded[0].y, 96, "Unexpected face y coordinate.");
  assertClose(decoded[0].width, 192, "Unexpected face width.");
  assertClose(decoded[0].height, 192, "Unexpected face height.");
  assertClose(decoded[0].confidence, 0.95, "Unexpected face confidence.");

  const detector = new OnnxUltraFaceDetector(new Uint8Array([1, 2, 3]), {
    sessionFactory,
  });
  const detections = await detector.detect(image);
  assert(detections.length === decoded.length, "Detector result count changed.");
  assertClose(detections[0].x, decoded[0].x, "Detector x coordinate changed.");
  const redacted = redactScreenshot(image, detections);
  assert(redacted.image.data[64 * 4 + 96 * image.width * 4] === 0, "Face pixels were not redacted.");
  await detector.release();

  console.log("ONNX face detector adapter tests passed");
}

void main();