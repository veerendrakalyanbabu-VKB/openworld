"""Structured API error responses."""

import uuid

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger()

_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    429: "rate_limit_exceeded",
    500: "internal_error",
    503: "service_unavailable",
}


def get_request_id(request: Request) -> str:
    """Prefer the gateway-assigned request ID over a newly generated one."""
    state_id = getattr(request.state, "request_id", None)
    if state_id:
        return str(state_id)
    header_id = request.headers.get("X-Request-ID")
    if header_id:
        return header_id
    return str(uuid.uuid4())


def _request_id(request: Request) -> str:
    return get_request_id(request)


def _detail_message(detail: object) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return "; ".join(str(item) for item in detail)
    return str(detail)


def structured_error(
    *,
    status_code: int,
    message: str,
    request_id: str,
    detail: object = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "error": _ERROR_CODES.get(status_code, "error"),
        "message": message,
        "request_id": request_id,
        "detail": detail if detail is not None else message,
    }
    return payload


def register_exception_handlers(app: FastAPI) -> None:
    """Register gateway-level exception handlers for structured errors."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        rid = _request_id(request)
        message = _detail_message(exc.detail)
        logger.warning(
            "HTTP exception",
            status_code=exc.status_code,
            message=message,
            request_id=rid,
        )
        headers = dict(getattr(exc, "headers", None) or {})
        headers.setdefault("X-Request-ID", rid)
        return JSONResponse(
            status_code=exc.status_code,
            content=structured_error(
                status_code=exc.status_code,
                message=message,
                request_id=rid,
                detail=exc.detail,
            ),
            headers=headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
        rid = _request_id(request)
        message = _detail_message(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=structured_error(
                status_code=exc.status_code,
                message=message,
                request_id=rid,
                detail=exc.detail,
            ),
            headers={"X-Request-ID": rid},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        rid = _request_id(request)
        logger.warning("Validation error", errors=exc.errors(), request_id=rid)
        return JSONResponse(
            status_code=422,
            content=structured_error(
                status_code=422,
                message="Request validation failed",
                request_id=rid,
                detail=exc.errors(),
            ),
            headers={"X-Request-ID": rid},
        )
