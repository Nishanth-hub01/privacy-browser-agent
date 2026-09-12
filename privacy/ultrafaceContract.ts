export const ULTRAFACE_INPUT_NAME = "input";
export const ULTRAFACE_SCORES_OUTPUT_NAME = "scores";
export const ULTRAFACE_BOXES_OUTPUT_NAME = "boxes";
export const ULTRAFACE_INPUT_WIDTH = 320;
export const ULTRAFACE_INPUT_HEIGHT = 240;
export const ULTRAFACE_PRIOR_COUNT = 4420;
export const ULTRAFACE_DEFAULT_CONFIDENCE_THRESHOLD = 0.7;
export const ULTRAFACE_DEFAULT_NMS_IOU_THRESHOLD = 0.3;

export const ULTRAFACE_MODEL_FILENAME = "version-RFB-320.onnx";

export const ULTRAFACE_INPUT_SHAPE = [1, 3, 240, 320] as const;