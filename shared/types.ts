// ============================================================
// Privacy-Preserving Vision Browser Agent
// Shared Type Definitions
//
// Version: 1.0.0
//
// This file contains common TypeScript interfaces shared
// between the browser extension and privacy modules.
// ============================================================

// COMMON TYPES
export type Status = "success" | "error";

// SENSITIVE DATA TYPES
export type SensitiveDataType =
  | "password"
  | "email"
  | "phone"
  | "government_id"
  | "credit_card"
  | "face"
  | "name"
  | "sensitive_field";

// REDACTION ACTIONS
export type RedactionAction =
  | "masked"
  | "blurred"
  | "blackout"
  | "removed";

// SENSITIVE DATA LOCATION
export type DataLocation =
  | "screenshot"
  | "dom";

// BROWSER ACTION TYPES
export type ActionType =
  | "click"
  | "scroll"
  | "type"
  | "navigate";

// REQUEST: EXTENSION -> PRIVACY
export interface ExtensionPrivacyRequest {
  request_id: string;
  timestamp: string;
  url: string;
  screenshot: string;
  dom: string;
  user_instruction: string;
}

// DETECTED SENSITIVE DATA
export interface DetectedSensitiveData {
  type: SensitiveDataType;
  location: DataLocation;
  action: RedactionAction;
}

// VISUAL ELEMENT
export interface VisualElement {
  type: string;
  label?: string;
  id?: string;
  selector?: string;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
}

// PRIVACY SUCCESS RESPONSE
export interface PrivacySuccessResponse {
  request_id: string;
  status: "success";
  sanitized_screenshot: string;
  sanitized_dom: string;
  detected_sensitive_data: DetectedSensitiveData[];
  visual_elements: VisualElement[];
}

// ERROR CODES
export type ErrorCode =
  | "INVALID_REQUEST"
  | "INVALID_CONTEXT"
  | "PRIVACY_CHECK_FAILED"
  | "MODEL_ERROR"
  | "ACTION_NOT_FOUND"
  | "LOW_CONFIDENCE"
  | "SERVER_ERROR";

// ERROR RESPONSE
export interface ErrorResponse {
  request_id: string;
  status: "error";
  error: {
    code: ErrorCode;
    message: string;
  };
}

// PRIVACY -> SERVER
export interface AnalyzeRequest {
  request_id: string;
  user_instruction: string;
  sanitized_screenshot: string;
  sanitized_dom: string;
  visual_elements: VisualElement[];
}

// ACTION TARGET
export interface ActionTarget {
  id?: string;
  selector?: string;
  x?: number;
  y?: number;
}

// CLICK ACTION
export interface ClickAction {
  type: "click";
  target: ActionTarget;
}

// SCROLL ACTION
export interface ScrollAction {
  type: "scroll";
  target: {
    direction: "up" | "down";
    amount: number;
  };
}

// TYPE ACTION
export interface TypeAction {
  type: "type";
  target: ActionTarget;
  text: string;
}

// NAVIGATE ACTION
export interface NavigateAction {
  type: "navigate";
  target: {
    url: string;
  };
}

// BROWSER ACTION
export type BrowserAction =
  | ClickAction
  | ScrollAction
  | TypeAction
  | NavigateAction;

// SERVER SUCCESS RESPONSE
export interface ServerSuccessResponse {
  request_id: string;
  status: "success";
  action: BrowserAction;
  confidence: number;
  reason: string;
}

// SERVER RESPONSE
export type ServerResponse =
  | ServerSuccessResponse
  | ErrorResponse;

// OPTIONAL API ENVELOPE
export interface ApiResponse<T> {
  request_id: string;
  status: Status;
  data?: T;
  error?: {
    code: ErrorCode;
    message: string;
  };
}
