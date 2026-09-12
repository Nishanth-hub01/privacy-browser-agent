import * as ort from "onnxruntime-web";
import {
  LocalVisionSession,
  LocalVisionSessionFactory,
  VisionExecutionProvider,
} from "./types";

function hasWebGpu(): boolean {
  const browserNavigator = (
    globalThis as typeof globalThis & {
      navigator?: { gpu?: unknown };
    }
  ).navigator;

  return Boolean(browserNavigator?.gpu);
}

function wrapSession(
  session: ort.InferenceSession,
  provider: VisionExecutionProvider
): LocalVisionSession {
  return {
    provider,
    inputNames: session.inputNames,
    outputNames: session.outputNames,
    inputMetadata: session.inputMetadata
      .filter((metadata) => metadata.isTensor)
      .map((metadata) => ({
        name: metadata.name,
        type: metadata.type,
        shape: metadata.shape,
      })),
    outputMetadata: session.outputMetadata
      .filter((metadata) => metadata.isTensor)
      .map((metadata) => ({
        name: metadata.name,
        type: metadata.type,
        shape: metadata.shape,
      })),
    async run(feeds) {
      const outputs = await session.run(feeds as ort.InferenceSession.FeedsType);
      return outputs;
    },
    release: () => session.release(),
  };
}

export function createOnnxSessionFactory(
  preferWebGpu = true
): LocalVisionSessionFactory {
  return {
    async create(model: Uint8Array) {
      if (preferWebGpu && hasWebGpu()) {
        try {
          const session = await ort.InferenceSession.create(model, {
            executionProviders: ["webgpu"],
            logSeverityLevel: 3,
          });
          return wrapSession(session, "webgpu");
        } catch {
          // Fall through to the local WASM provider.
        }
      }

      const session = await ort.InferenceSession.create(model, {
        executionProviders: ["wasm"],
        logSeverityLevel: 3,
      });
      return wrapSession(session, "wasm");
    },
  };
}