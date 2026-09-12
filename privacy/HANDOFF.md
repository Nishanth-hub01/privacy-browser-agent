# Member 2 Privacy Engine Handoff

## Responsibility

Member 2 owns local privacy processing before any browser context is allowed to proceed toward the server.

The privacy module detects and removes text, DOM, and visual sensitive data locally. It does not send data to the server and does not perform extension messaging.

## Implemented Features

- Text PII detection for email, phone, government ID, credit card, password, address, and supported personal-name patterns.
- Text redaction with replacement tokens.
- Safe text sanitization results that do not expose raw detected PII values.
- Sensitive DOM-field detection.
- DOM sanitization using a cloned document.
- Password, email, phone, and address value replacement.
- Local face detection through the UltraFace RFB-320 ONNX model.
- Visual bounding-box validation and clamping.
- Immutable local screenshot redaction.
- Blackout and blur-style screenshot redaction.
- Screenshot privacy verification.
- Fail-closed screenshot processing errors.
- WebGPU-preferred ONNX execution.
- WASM/CPU fallback when WebGPU is unavailable or fails.
- Synthetic visual detector support for tests.

## Privacy Guarantee

Raw private data must remain local and must never be sent to the server.

The privacy module does not call cloud AI, external vision APIs, or external image-processing APIs. Production privacy code does not log raw screenshots, base64 image data, image pixels, face crops, or raw sensitive values.

## Public Entry Point

The public privacy barrel is [index.ts](index.ts).

The current public functions and classes are:

- `sanitizeText(text)`
- `sanitizeDOM(root)`
- `verifySanitizedText(text)`
- `verifySanitizedDOM(root)`
- `verifyPrivacy(text, dom?)`
- `redactScreenshot(image, regions, options?)`
- `processScreenshotPrivacy(detector, image, options?)`
- `detectAndRedactScreenshot(detector, image, options?)`
- `verifySanitizedScreenshot(original, sanitized, detections, redactedRegions)`
- `preprocessUltraFace(image)`
- `decodeUltraFaceOutputs(outputs, imageWidth, imageHeight, options?)`
- `createOnnxSessionFactory(preferWebGpu?)`
- `OnnxUltraFaceDetector`

`processScreenshotPrivacy()` is the complete visual privacy-side orchestration entry point. Text and DOM processing remain separate because the current architecture exposes those operations independently.

## Input

The privacy module currently accepts already-decoded local data.

### Text

```ts
sanitizeText(text: string)
```

### DOM

```ts
sanitizeDOM(root: Document)
```

The input document must be available in the local browser/privacy context. Sanitization clones the document and does not mutate the source document.

### Screenshot/image

```ts
processScreenshotPrivacy(
  detector: VisualPrivacyDetector,
  image: RasterImage,
  options?: ScreenshotPrivacyPipelineOptions
)
```

`RasterImage` contains local RGBA pixels:

```ts
interface RasterImage {
  width: number;
  height: number;
  data: Uint8ClampedArray;
}
```

Base64 screenshot decoding is not part of the current privacy module. The extension or a future browser-specific privacy adapter must decode the screenshot locally into `RasterImage` before calling the pipeline.

## Processing Pipeline

```text
Screenshot + DOM
      |
      v
Local PII Detection
      |
      v
DOM Sanitization
      |
      v
Local Vision Detection
      |
      v
Bounding Box Validation
      |
      v
Local Redaction
      |
      v
Privacy Verification
      |
      v
Sanitized Context
```

The visual path is implemented as:

```text
RasterImage
      |
      v
VisualPrivacyDetector.detect()
      |
      v
Detection normalization and confidence filtering
      |
      v
redactScreenshot()
      |
      v
verifySanitizedScreenshot()
      |
      v
ScreenshotPrivacyPipelineResult
```

## Output

### Sanitized text

`sanitizeText()` returns:

- `sanitizedText`
- safe `matches` metadata
- `domFindings`
- `privacyPassed`

Returned match values use replacement tokens rather than raw detected PII values.

### Sanitized DOM

`sanitizeDOM()` returns:

- `sanitizedDOM`
- safe DOM findings
- `privacyPassed`

The original document is not modified.

### Sanitized image

`processScreenshotPrivacy()` returns:

- `sanitizedImage`
- accepted `detections`
- `redactedRegions`
- safe verification counts
- `privacyPassed`

The result contains local image data for the future extension adapter to consume. It does not log or transmit the image.

The current privacy module does not extract `visual_elements` or encode `sanitizedImage` into the shared server payload. That adapter work belongs to the extension/integration layer.

## Visual Detection

Visual detections use:

```ts
interface VisualPrivacyRegion {
  type: "FACE" | "SENSITIVE_REGION";
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
}
```

For the current ONNX detector, every model detection uses:

```text
type: FACE
```

Coordinates are converted to original screenshot pixels. Invalid regions are rejected, partially out-of-bounds regions are clamped, and confidence is constrained to the range `0` through `1`.

Raw face images, crops, and pixel contents are never included in detection metadata.

`SENSITIVE_REGION` is an extension type. The current UltraFace model does not automatically detect arbitrary sensitive regions.

## ONNX Runtime

Face detection runs locally using the selected:

```text
version-RFB-320.onnx
```

model.

The verified model contract is:

```text
Input:  input / float32 / [1, 3, 240, 320]
Outputs: scores / float32 / [1, 4420, 2]
         boxes  / float32 / [1, 4420, 4]
```

The local detector performs model preprocessing, confidence filtering, hard NMS, coordinate conversion, bounding-box validation, and resource cleanup.

WebGPU is preferred where supported. If WebGPU is unavailable or session initialization fails, ONNX Runtime Web falls back to WASM/CPU.

WebGPU runtime test: NOT EXECUTED in the current environment.

WASM/CPU execution was tested with the local model using synthetic pixels.

## Redaction

`redactScreenshot()` returns a new image buffer and does not modify the original `RasterImage`.

Supported methods:

- `BLACKOUT`: replaces accepted region pixels with opaque black.
- `BLUR`: applies local blur-style redaction inside accepted regions.

The pipeline redacts all accepted `FACE` regions before screenshot verification.

## Privacy Verification

Text and DOM verification reuse the existing PII and sensitive-field detectors.

Screenshot verification checks that:

- Original and sanitized image dimensions match.
- The sanitized image uses a separate buffer.
- Every accepted detection has a corresponding redacted region.
- The processing result is structurally complete.

Verification metadata contains only status and region counts. It does not contain raw image data or sensitive visual content.

## Failure Handling

The screenshot pipeline fails closed.

If detection, validation, redaction, or verification fails, `processScreenshotPrivacy()` rejects with a generic error:

```text
Screenshot privacy processing failed.
```

The pipeline does not return the raw image as a successful sanitized result.

The extension integration layer must catch this failure and prevent any server request containing the raw screenshot or unsanitized DOM.

Model metadata mismatches, invalid image data, invalid output tensors, runtime failures, and verification failures must all be treated as privacy failures.

## Extension Team Responsibilities

Member 1 still needs to implement:

- Screenshot capture.
- Local screenshot decoding from the browser capture format.
- Passing decoded local image data to `processScreenshotPrivacy()`.
- Passing the local DOM to `sanitizeDOM()`.
- Calling `sanitizeText()` where text context requires it.
- Receiving the sanitized image and sanitized DOM.
- Encoding the sanitized image for the shared payload only after privacy verification passes.
- Building safe `visual_elements` metadata.
- Preventing raw screenshots from being sent to the server.
- Catching privacy failures and blocking the request safely.
- Keeping screenshot and DOM data local until privacy processing completes.

No extension files were changed by Member 2.

## Server Team Responsibilities

The server must receive only sanitized data according to the unchanged shared API contract:

- `sanitized_screenshot`
- `sanitized_dom`
- `visual_elements`
- `request_id`
- `user_instruction`

The server must not receive raw screenshots, raw DOM, passwords, unredacted PII, or raw visual regions.

No server files were changed by Member 2.

## Current Limitations

- WebGPU runtime test was not executed in the current environment.
- End-to-end browser extension integration is not complete.
- Browser-specific screenshot capture and decoding are not implemented inside `privacy/`.
- The privacy module does not currently produce `visual_elements`.
- The shared request envelope is not assembled by `privacy/`.
- Real-world browser performance still needs integration testing.
- No positive real-person image test was used; automated tests use synthetic pixel data.
- The current screenshot verifier validates processing structure and region correspondence, not independent visual identifiability.

## Handoff Status

The privacy module is ready for the extension team to integrate through the existing public functions. Team integration itself is not complete.
