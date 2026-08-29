# gateway/app/proxy.py
# --------------------
# Core reverse-proxy logic.
#
# forward_request():
#   - Strips the /api/componentN prefix from the inbound path.
#   - Re-issues the original HTTP method, query parameters, and body
#     to the upstream service.
#   - Removes hop-by-hop headers before forwarding so they do not
#     confuse the upstream (e.g. Transfer-Encoding: chunked).
#   - Returns the upstream status code, response body, and Content-Type
#     unchanged so callers see the real backend response.
#   - Returns 503 on connection failure and 504 on timeout.

import logging
from typing import Optional

import httpx
from fastapi import Request
from fastapi.responses import Response, JSONResponse

logger = logging.getLogger("gateway.proxy")

# Headers that must NOT be forwarded to the upstream (RFC 7230 §6.1)
_HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        # "host" is rebuilt from the upstream URL by httpx
        "host",
        # Content-Length is recalculated by httpx after body inspection
        "content-length",
    }
)


def _forward_headers(request: Request) -> dict:
    """Return a filtered copy of the inbound request headers."""
    return {
        name: value
        for name, value in request.headers.items()
        if name.lower() not in _HOP_BY_HOP
    }


async def forward_request(
    request: Request,
    upstream_base: str,
    upstream_path: str,
    timeout: float = 30.0,
) -> Response:
    """
    Forward *request* to *upstream_base* + *upstream_path*.

    Parameters
    ----------
    request       : The incoming FastAPI Request object.
    upstream_base : e.g. "http://localhost:8001"
    upstream_path : Path after stripping the gateway prefix,
                    e.g. "/health" or "/waste/predict"
    timeout       : Per-request timeout in seconds.

    Returns
    -------
    A FastAPI Response whose status_code, body, and media_type
    mirror the upstream exactly.
    """
    # Normalise: ensure upstream_path starts with /
    if not upstream_path.startswith("/"):
        upstream_path = f"/{upstream_path}"

    target_url = f"{upstream_base.rstrip('/')}{upstream_path}"

    logger.info(
        "%s %s  ->  %s", request.method, request.url.path, target_url
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream_response = await client.request(
                method=request.method,
                url=target_url,
                headers=_forward_headers(request),
                content=await request.body(),
                params=dict(request.query_params),
                follow_redirects=True,
            )

        # Strip hop-by-hop from the response headers too
        response_headers = {
            k: v
            for k, v in upstream_response.headers.items()
            if k.lower() not in _HOP_BY_HOP
        }

        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            headers=response_headers,
            media_type=upstream_response.headers.get("content-type"),
        )

    except httpx.ConnectError as exc:
        logger.warning("Cannot connect to upstream %s: %s", target_url, exc)
        return JSONResponse(
            status_code=503,
            content={
                "error": "service_unavailable",
                "detail": f"Cannot connect to upstream at {upstream_base}. "
                          "Ensure the component backend is running.",
                "upstream": upstream_base,
            },
        )

    except httpx.TimeoutException as exc:
        logger.warning("Timeout reaching upstream %s: %s", target_url, exc)
        return JSONResponse(
            status_code=504,
            content={
                "error": "gateway_timeout",
                "detail": f"Upstream at {upstream_base} did not respond within "
                          f"{timeout} seconds.",
                "upstream": upstream_base,
            },
        )

    except httpx.RequestError as exc:
        logger.error("Unexpected request error forwarding to %s: %s", target_url, exc)
        return JSONResponse(
            status_code=502,
            content={
                "error": "bad_gateway",
                "detail": str(exc),
                "upstream": upstream_base,
            },
        )


async def ping_service(
    name: str,
    base_url: str,
    health_path: str,
    timeout: float = 5.0,
) -> dict:
    """
    Ping one upstream health endpoint.  Always returns a dict — never raises.

    Returns
    -------
    {
        "service"  : "component1",
        "url"      : "http://localhost:8001",
        "status"   : "ok" | "unavailable" | "unhealthy",
        "http_code": 200 | None,
        "detail"   : "..." | None,
    }
    """
    target = f"{base_url.rstrip('/')}{health_path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(target)
        status = "ok" if r.status_code < 400 else "unhealthy"
        return {
            "service": name,
            "url": base_url,
            "status": status,
            "http_code": r.status_code,
            "detail": None,
        }
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
        return {
            "service": name,
            "url": base_url,
            "status": "unavailable",
            "http_code": None,
            "detail": str(exc),
        }
