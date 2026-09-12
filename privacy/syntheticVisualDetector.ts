import {
  RasterImage,
  VisualPrivacyDetector,
  VisualPrivacyRegion,
} from "./types";

export function createSyntheticVisualDetector(
  detections: VisualPrivacyRegion[]
): VisualPrivacyDetector {
  const syntheticDetections = detections.map((detection) => ({ ...detection }));

  return {
    detect(_image: RasterImage): VisualPrivacyRegion[] {
      return syntheticDetections.map((detection) => ({ ...detection }));
    },
  };
}