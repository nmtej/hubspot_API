# app/api/schemas/common.py

from typing import Any, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(
        None,
        description="Field name for validation errors",
    )
    extra: Optional[dict[str, Any]] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    trace_id: Optional[str] = Field(
        None,
        description="Correlation/Trace ID for debugging",
    )
