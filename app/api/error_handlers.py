# app/api/error_handlers.py

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.schemas.common import ErrorResponse, ErrorDetail


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    trace_id = request.headers.get("X-Trace-Id")  # später evtl. per Middleware generieren

    error = ErrorDetail(
        code="http_error",
        message=str(exc.detail),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=error, trace_id=trace_id).dict(),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    trace_id = request.headers.get("X-Trace-Id")

    # FastAPI gibt ein Array an Fehlern – wir picken den ersten für message/field
    first_error = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first_error.get("loc", []))
    message = first_error.get("msg", "Validation error")

    error = ErrorDetail(
        code="validation_error",
        message=message,
        field=field,
        extra={"errors": exc.errors()},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(error=error, trace_id=trace_id).dict(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    trace_id = request.headers.get("X-Trace-Id")
    error = ErrorDetail(
        code="internal_server_error",
        message="An unexpected error occurred.",
    )
    # TODO: Hier Logging mit trace_id + exc ergänzen
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(error=error, trace_id=trace_id).model_dump(),
    )
