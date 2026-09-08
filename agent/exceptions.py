"""Custom exceptions for LLM/VLM output validation and planning errors."""


class ModelOutputError(ValueError):
    """Base error for model output validation failures."""
    pass


class ModelJSONDecodeError(ModelOutputError):
    """Raised when the model response cannot be parsed as valid JSON."""
    pass


class UnsupportedActionError(ModelOutputError):
    """Raised when the model proposes an unsupported action type."""
    pass


class InvalidActionTargetError(ModelOutputError):
    """Raised when an action target or required field is missing or malformed."""
    pass


class InvalidConfidenceError(ModelOutputError):
    """Raised when confidence is missing, non-numeric, or outside [0.0, 1.0]."""
    pass


class InvalidReasonError(ModelOutputError):
    """Raised when reason is missing, empty, or not a string."""
    pass
