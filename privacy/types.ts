export type PIIType =
  | "PERSON"
  | "EMAIL"
  | "PHONE"
  | "GOVERNMENT_ID"
  | "CREDIT_CARD"
  | "PASSWORD"
  | "ADDRESS";

export interface PIIMatch {
  type: PIIType;
  start: number;
  end: number;
  value: string;
  replacement: string;
}

export interface SanitizedText {
  original: string;
  sanitized: string;
  matches: PIIMatch[];
}

export interface DOMFinding {
  type: PIIType;
  element: string;
  attribute?: string;
  value?: string;
}

export interface PrivacyResult {
  sanitizedText: string;
  matches: PIIMatch[];
  domFindings: DOMFinding[];
  privacyPassed: boolean;
}

export interface DOMSanitizationResult {
  sanitizedDOM: string;
  findings: DOMFinding[];
  privacyPassed: boolean;
}

export interface PrivacyVerificationResult {
  privacyPassed: boolean;
  remainingTextTypes: PIIType[];
  remainingDOMTypes: PIIType[];
}

export type VisualPrivacyRegionType = "FACE" | "SENSITIVE_REGION";

export interface VisualPrivacyRegion {
  type: VisualPrivacyRegionType;
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
}

export type ScreenshotRedactionMethod = "BLACKOUT" | "BLUR";

export interface RasterImage {
  width: number;
  height: number;
  data: Uint8ClampedArray;
}

export interface ScreenshotRedactionOptions {
  method?: ScreenshotRedactionMethod;
  blurRadius?: number;
}

export interface ScreenshotRedactionResult {
  image: RasterImage;
  redactedRegions: VisualPrivacyRegion[];
}

export interface VisualPrivacyDetector {
  detect(
    image: RasterImage
  ): VisualPrivacyRegion[] | Promise<VisualPrivacyRegion[]>;
}

export interface VisualDetectionResult {
  detections: VisualPrivacyRegion[];
}

export interface VisualRedactionResult extends ScreenshotRedactionResult {
  detections: VisualPrivacyRegion[];
}

export type VisionExecutionProvider = "webgpu" | "wasm";

export interface PreparedVisionInput {
  data: Float32Array;
  shape: readonly [1, 3, 240, 320];
}

export interface LocalVisionSession {
  readonly provider: VisionExecutionProvider;
  readonly inputNames: readonly string[];
  readonly outputNames: readonly string[];
  readonly inputMetadata: readonly LocalVisionTensorMetadata[];
  readonly outputMetadata: readonly LocalVisionTensorMetadata[];
  run(feeds: Record<string, unknown>): Promise<Record<string, unknown>>;
  release(): Promise<void>;
}

export interface LocalVisionTensorMetadata {
  readonly name: string;
  readonly type: string;
  readonly shape: readonly (number | string)[];
}

export interface LocalVisionSessionFactory {
  create(model: Uint8Array): Promise<LocalVisionSession>;
}

export interface UltraFaceDetectorOptions {
  confidenceThreshold?: number;
  nmsIouThreshold?: number;
  sessionFactory?: LocalVisionSessionFactory;
}

export interface ScreenshotPrivacyVerificationResult {
  privacyPassed: boolean;
  detectedRegionCount: number;
  redactedRegionCount: number;
}

export interface ScreenshotPrivacyPipelineOptions {
  minimumConfidence?: number;
  redaction?: ScreenshotRedactionOptions;
}

export interface ScreenshotPrivacyPipelineResult {
  sanitizedImage: RasterImage;
  detections: VisualPrivacyRegion[];
  redactedRegions: VisualPrivacyRegion[];
  verification: ScreenshotPrivacyVerificationResult;
  privacyPassed: boolean;
}