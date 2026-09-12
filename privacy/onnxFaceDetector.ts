import * as ort from "onnxruntime-web";
import { preprocessUltraFace } from "./visionPreprocessor";
import { createOnnxSessionFactory } from "./onnxRuntime";
import {
  LocalVisionSession,
  LocalVisionSessionFactory,
  RasterImage,
  UltraFaceDetectorOptions,
  VisualPrivacyDetector,
  VisualPrivacyRegion,
} from "./types";
import {
  ULTRAFACE_BOXES_OUTPUT_NAME,
  ULTRAFACE_INPUT_NAME,
  ULTRAFACE_INPUT_SHAPE,
  ULTRAFACE_PRIOR_COUNT,
  ULTRAFACE_SCORES_OUTPUT_NAME,
} from "./ultrafaceContract";
import { decodeUltraFaceOutputs } from "./ultrafaceDecoder";

export class OnnxUltraFaceDetector implements VisualPrivacyDetector {
  private readonly model: Uint8Array;
  private readonly options: Required<Pick<UltraFaceDetectorOptions, "confidenceThreshold" | "nmsIouThreshold">>;
  private readonly sessionFactory: LocalVisionSessionFactory;
  private session?: LocalVisionSession;

  public constructor(
    model: Uint8Array,
    options: UltraFaceDetectorOptions = {}
  ) {
    this.model = model;
    this.options = {
      confidenceThreshold: options.confidenceThreshold ?? 0.7,
      nmsIouThreshold: options.nmsIouThreshold ?? 0.3,
    };
    this.sessionFactory = options.sessionFactory ?? createOnnxSessionFactory();
  }

  public async detect(image: RasterImage): Promise<VisualPrivacyRegion[]> {
    const session = await this.getSession();
    const prepared = preprocessUltraFace(image);
    const tensor = new ort.Tensor("float32", prepared.data, prepared.shape);
    let outputs: Record<string, unknown> | undefined;

    try {
      outputs = await session.run({ [ULTRAFACE_INPUT_NAME]: tensor });
      return decodeUltraFaceOutputs(
        outputs,
        image.width,
        image.height,
        this.options
      );
    } finally {
      tensor.dispose();
      this.disposeOutputs(outputs);
    }
  }

  public async release(): Promise<void> {
    if (this.session) {
      await this.session.release();
      this.session = undefined;
    }
  }

  private async getSession(): Promise<LocalVisionSession> {
    if (!this.session) {
      this.session = await this.sessionFactory.create(this.model);
      if (
        !this.session.inputNames.includes(ULTRAFACE_INPUT_NAME) ||
        !this.session.outputNames.includes(ULTRAFACE_SCORES_OUTPUT_NAME) ||
        !this.session.outputNames.includes(ULTRAFACE_BOXES_OUTPUT_NAME) ||
        !this.matchesMetadata(
          this.session.inputMetadata,
          ULTRAFACE_INPUT_NAME,
          ULTRAFACE_INPUT_SHAPE
        ) ||
        !this.matchesMetadata(
          this.session.outputMetadata,
          ULTRAFACE_SCORES_OUTPUT_NAME,
          [1, ULTRAFACE_PRIOR_COUNT, 2]
        ) ||
        !this.matchesMetadata(
          this.session.outputMetadata,
          ULTRAFACE_BOXES_OUTPUT_NAME,
          [1, ULTRAFACE_PRIOR_COUNT, 4]
        )
      ) {
        await this.session.release();
        this.session = undefined;
        throw new Error("ONNX model does not match the verified UltraFace contract.");
      }
    }

    return this.session;
  }

  private matchesMetadata(
    metadata: LocalVisionSession["inputMetadata"],
    name: string,
    shape: readonly number[]
  ): boolean {
    const tensor = metadata.find((item) => item.name === name);

    return Boolean(
      tensor &&
        tensor.type === "float32" &&
        tensor.shape.length === shape.length &&
        tensor.shape.every((dimension, index) => dimension === shape[index])
    );
  }

  private disposeOutputs(outputs: Record<string, unknown> | undefined): void {
    if (!outputs) {
      return;
    }

    Object.values(outputs).forEach((output) => {
      if (
        output &&
        typeof output === "object" &&
        "dispose" in output &&
        typeof output.dispose === "function"
      ) {
        output.dispose();
      }
    });
  }
}