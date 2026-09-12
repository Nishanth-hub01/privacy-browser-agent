import { VisualPrivacyRegion } from "./types";
import {
  ULTRAFACE_BOXES_OUTPUT_NAME,
  ULTRAFACE_DEFAULT_CONFIDENCE_THRESHOLD,
  ULTRAFACE_DEFAULT_NMS_IOU_THRESHOLD,
  ULTRAFACE_PRIOR_COUNT,
  ULTRAFACE_SCORES_OUTPUT_NAME,
} from "./ultrafaceContract";

interface CandidateBox {
  x: number;
  y: number;
  right: number;
  bottom: number;
  confidence: number;
}

export interface UltraFaceDecodeOptions {
  confidenceThreshold?: number;
  nmsIouThreshold?: number;
}

function tensorData(
  outputs: Record<string, unknown>,
  name: string
): { data: Float32Array; dims: readonly number[] } {
  const tensor = outputs[name];

  if (!tensor || typeof tensor !== "object") {
    throw new Error(`ONNX output ${name} is unavailable.`);
  }

  const candidate = tensor as {
    data?: unknown;
    dims?: readonly number[];
    type?: string;
  };

  if (!(candidate.data instanceof Float32Array) || !candidate.dims || candidate.type !== "float32") {
    throw new Error(`ONNX output ${name} is not a float32 tensor.`);
  }

  return { data: candidate.data, dims: candidate.dims };
}

function assertShape(
  dims: readonly number[],
  expected: readonly number[],
  name: string
): void {
  if (
    dims.length !== expected.length ||
    dims.some((dimension, index) => dimension !== expected[index])
  ) {
    throw new Error(`ONNX output ${name} has an unexpected shape.`);
  }
}

function intersectionOverUnion(left: CandidateBox, right: CandidateBox): number {
  const intersectionLeft = Math.max(left.x, right.x);
  const intersectionTop = Math.max(left.y, right.y);
  const intersectionRight = Math.min(left.right, right.right);
  const intersectionBottom = Math.min(left.bottom, right.bottom);
  const intersection = Math.max(0, intersectionRight - intersectionLeft) * Math.max(0, intersectionBottom - intersectionTop);
  const leftArea = Math.max(0, left.right - left.x) * Math.max(0, left.bottom - left.y);
  const rightArea = Math.max(0, right.right - right.x) * Math.max(0, right.bottom - right.y);

  return intersection / Math.max(1e-8, leftArea + rightArea - intersection);
}

function applyNms(candidates: CandidateBox[], threshold: number): CandidateBox[] {
  const remaining = [...candidates].sort(
    (left, right) => right.confidence - left.confidence
  );
  const selected: CandidateBox[] = [];

  while (remaining.length > 0) {
    const current = remaining.shift();

    if (!current) {
      break;
    }

    selected.push(current);
    for (let index = remaining.length - 1; index >= 0; index -= 1) {
      if (intersectionOverUnion(current, remaining[index]) > threshold) {
        remaining.splice(index, 1);
      }
    }
  }

  return selected;
}

export function decodeUltraFaceOutputs(
  outputs: Record<string, unknown>,
  imageWidth: number,
  imageHeight: number,
  options: UltraFaceDecodeOptions = {}
): VisualPrivacyRegion[] {
  const scores = tensorData(outputs, ULTRAFACE_SCORES_OUTPUT_NAME);
  const boxes = tensorData(outputs, ULTRAFACE_BOXES_OUTPUT_NAME);
  assertShape(scores.dims, [1, ULTRAFACE_PRIOR_COUNT, 2], ULTRAFACE_SCORES_OUTPUT_NAME);
  assertShape(boxes.dims, [1, ULTRAFACE_PRIOR_COUNT, 4], ULTRAFACE_BOXES_OUTPUT_NAME);

  const confidenceThreshold = Math.max(
    0,
    Math.min(1, options.confidenceThreshold ?? ULTRAFACE_DEFAULT_CONFIDENCE_THRESHOLD)
  );
  const candidates: CandidateBox[] = [];

  for (let index = 0; index < ULTRAFACE_PRIOR_COUNT; index += 1) {
    const confidence = scores.data[index * 2 + 1];
    const boxIndex = index * 4;
    const x = boxes.data[boxIndex] * imageWidth;
    const y = boxes.data[boxIndex + 1] * imageHeight;
    const right = boxes.data[boxIndex + 2] * imageWidth;
    const bottom = boxes.data[boxIndex + 3] * imageHeight;

    if (
      confidence < confidenceThreshold ||
      !Number.isFinite(confidence) ||
      !Number.isFinite(x) ||
      !Number.isFinite(y) ||
      !Number.isFinite(right) ||
      !Number.isFinite(bottom) ||
      right <= x ||
      bottom <= y
    ) {
      continue;
    }

    candidates.push({ x, y, right, bottom, confidence });
  }

  return applyNms(
    candidates,
    Math.max(0, Math.min(1, options.nmsIouThreshold ?? ULTRAFACE_DEFAULT_NMS_IOU_THRESHOLD))
  ).map((candidate): VisualPrivacyRegion => ({
    type: "FACE" as const,
    x: Math.max(0, Math.min(imageWidth, candidate.x)),
    y: Math.max(0, Math.min(imageHeight, candidate.y)),
    width: Math.max(0, Math.min(imageWidth, candidate.right) - Math.max(0, Math.min(imageWidth, candidate.x))),
    height: Math.max(0, Math.min(imageHeight, candidate.bottom) - Math.max(0, Math.min(imageHeight, candidate.y))),
    confidence: Math.max(0, Math.min(1, candidate.confidence)),
  })).filter((region) => region.width > 0 && region.height > 0);
}