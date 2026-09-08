from enum import Enum
from typing import Annotated, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_CONTEXT = "INVALID_CONTEXT"
    PRIVACY_CHECK_FAILED = "PRIVACY_CHECK_FAILED"
    MODEL_ERROR = "MODEL_ERROR"
    ACTION_NOT_FOUND = "ACTION_NOT_FOUND"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    SERVER_ERROR = "SERVER_ERROR"


class VisualElement(BaseModel):
    type: str = Field(..., description="Element type (e.g. button, input, link)")
    label: Optional[str] = Field(None, description="Element text label")
    id: Optional[str] = Field(None, description="DOM ID attribute")
    selector: Optional[str] = Field(None, description="CSS selector")
    x: Optional[float] = Field(None, description="X coordinate")
    y: Optional[float] = Field(None, description="Y coordinate")
    width: Optional[float] = Field(None, description="Element width")
    height: Optional[float] = Field(None, description="Element height")


class AnalyzeRequest(BaseModel):
    request_id: str = Field(..., description="Unique request ID")
    user_instruction: str = Field(..., description="User instruction string")
    sanitized_screenshot: str = Field(..., description="Sanitized screenshot (base64 encoded)")
    sanitized_dom: str = Field(..., description="Sanitized DOM string")
    visual_elements: List[VisualElement] = Field(
        default_factory=list,
        description="List of detected visual elements"
    )


class ActionTarget(BaseModel):
    id: Optional[str] = None
    selector: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None


class ClickAction(BaseModel):
    type: Literal["click"] = "click"
    target: ActionTarget


class ScrollTarget(BaseModel):
    direction: Literal["up", "down"]
    amount: int


class ScrollAction(BaseModel):
    type: Literal["scroll"] = "scroll"
    target: ScrollTarget


class TypeAction(BaseModel):
    type: Literal["type"] = "type"
    target: ActionTarget
    text: str


class NavigateTarget(BaseModel):
    url: str


class NavigateAction(BaseModel):
    type: Literal["navigate"] = "navigate"
    target: NavigateTarget


BrowserAction = Annotated[
    Union[ClickAction, ScrollAction, TypeAction, NavigateAction],
    Field(discriminator="type")
]


class ServerSuccessResponse(BaseModel):
    request_id: str
    status: Literal["success"] = "success"
    action: BrowserAction
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str


class ErrorResponse(BaseModel):
    request_id: str
    status: Literal["error"] = "error"
    error: ErrorDetail


ServerResponse = Union[ServerSuccessResponse, ErrorResponse]
