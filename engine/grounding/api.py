from __future__ import annotations

import logging
from datetime import date

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from grounding.ingest import extract_reference_document
from grounding.live import CheckTooComplex, run_live_check
from grounding.quota import (
    check_and_increment,
    decrement,
    mint_device_token,
    release_device_lock,
    try_acquire_device_lock,
    verify_device_token,
)

logger = logging.getLogger("grounding_inspector.api")

# Sized to what the decomposer can actually serve, not to what feels generous.
# decompose_output_claude asks Claude for the whole claim/subclaim JSON in a
# single call capped at max_tokens=1024 -- and the raw input text is itself
# part of that call's context. A longer input produces both a longer prompt
# and a proportionally longer JSON answer, so past a few thousand characters
# the answer gets truncated mid-JSON and the parse fails, surfacing as a 502
# the user did nothing to cause. 3500 chars leaves comfortable headroom under
# that ceiling rather than sitting on the boundary; raising it requires
# raising max_tokens (and re-measuring), not just editing this number.
MAX_AI_OUTPUT_CHARS = 3_500
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
FREE_TIER_DAILY_LIMIT = 3
IP_DAILY_BACKSTOP = 50
DEVICE_TOKEN_COOKIE = "gi_device_token"

UPLOAD_TOO_LARGE_DETAIL = f"Reference document exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)}MB"
# Fixed, generic text. Extraction failures are mapped to this one string so no
# parser exception detail ever reaches the client (see the spec's
# hidden-context-exposure constraint); the real exception is logged instead.
UNREADABLE_DOCUMENT_DETAIL = (
    "Could not read the reference document. Upload an unencrypted PDF, DOCX or TXT file with selectable text."
)
# Fixed, generic text. A CheckTooComplex carries the offending claim/subclaim
# counts in its message; that detail must never reach the client, so the
# handler maps every instance to this one string and logs the real cause.
CHECK_TOO_COMPLEX_DETAIL = (
    "This AI output produced too many separate claims to check in one request. "
    "Try checking a shorter passage."
)

ALLOWED_ORIGINS = [
    "https://grounding-inspector.netlify.app",
    "http://localhost:5173",
]


def create_app(client, db_conn_factory, device_token_secret: bytes) -> FastAPI:
    app = FastAPI(
        title="grounding-inspector-live", version="0.1.0",
        docs_url=None, redoc_url=None, openapi_url=None,
    )

    @app.middleware("http")
    async def reject_oversized_body(request: Request, call_next):
        """Reject an over-cap upload from the Content-Length header alone,
        before Starlette's multipart parser consumes the body. The
        post-parse length check in post_check stays as the fallback for
        chunked requests that send no Content-Length, but by the time that
        one runs FastAPI has already read the whole request -- so this is
        the only check that actually bounds ingress cost."""
        raw = request.headers.get("content-length")
        if raw and raw.isdigit() and int(raw) > MAX_UPLOAD_BYTES:
            return JSONResponse(status_code=400, content={"detail": UPLOAD_TOO_LARGE_DETAIL})
        return await call_next(request)

    # Registered after the body check so CORS ends up the outer layer -- a
    # rejection from the middleware above still gets CORS headers, otherwise
    # the browser can't read the error message.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["POST"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    def _resolve_device_token(request: Request, response: Response) -> str:
        raw = request.cookies.get(DEVICE_TOKEN_COOKIE)
        verified = verify_device_token(raw, device_token_secret) if raw else None
        if verified is not None:
            return raw
        new_token = mint_device_token(device_token_secret)
        response.set_cookie(
            DEVICE_TOKEN_COOKIE, new_token,
            # samesite="none" (not "lax"): the frontend is served from
            # netlify.app and this API from modal.run -- different
            # registrable domains, so every real browser request is
            # cross-site. A Lax cookie is simply not sent on a cross-site
            # fetch(), which would make the per-device quota never bind.
            # Valid only because secure=True is set.
            httponly=True, secure=True, samesite="none", max_age=60 * 60 * 24 * 365,
        )
        return new_token

    @app.post("/check")
    def post_check(
        request: Request,
        response: Response,
        ai_output: str = Form(...),
        reference_file: UploadFile = File(...),
    ) -> dict:
        # Resolved before any validation so every error path below can carry
        # the Set-Cookie header -- a first-time visitor rejected on their
        # very first request must still get a device token, or each retry
        # mints a fresh one and the quota never binds them.
        device_token = _resolve_device_token(request, response)
        cookie_header = response.headers.get("set-cookie")

        def _http_error(status_code: int, detail: str) -> None:
            headers = {"set-cookie": cookie_header} if cookie_header else None
            raise HTTPException(status_code=status_code, detail=detail, headers=headers)

        client_ip = request.client.host if request.client else "unknown"
        # Diagnostic only, no behaviour change: request.client.host may be a
        # constant internal address behind Modal's ingress, which would turn
        # IP_DAILY_BACKSTOP into a global ceiling shared by every visitor.
        # Logging both values lets the real deployment's logs settle whether
        # X-Forwarded-For's leftmost entry should be trusted instead.
        logger.info(
            "check request: client.host=%s x-forwarded-for=%s",
            client_ip, request.headers.get("x-forwarded-for"),
        )

        if len(ai_output) > MAX_AI_OUTPUT_CHARS:
            _http_error(400, f"AI output exceeds {MAX_AI_OUTPUT_CHARS} characters")

        file_bytes = reference_file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            _http_error(400, UPLOAD_TOO_LARGE_DETAIL)

        try:
            sections = extract_reference_document(reference_file.filename or "upload.txt", file_bytes)
        except Exception:
            # Deliberately broad. ingest raises UnsupportedFileType /
            # DocumentTooLarge (both ValueError subclasses), but pypdf and
            # python-docx raise their own unrelated hierarchies on a corrupt
            # or encrypted upload -- PdfReadError, PackageNotFoundError,
            # KeyError from a malformed zip container. Catching only
            # ValueError let those escape as an unhandled 500 that also
            # bypassed _http_error and dropped the Set-Cookie header.
            logger.exception("reference document extraction failed")
            _http_error(400, UNREADABLE_DOCUMENT_DETAIL)

        device_key = f"device:{device_token}"
        conn = db_conn_factory()
        lock_held = False
        try:
            # Lease lock first: it's what makes the concurrent double-spend
            # window closed. Then the IP backstop, so a request the backstop
            # rejects costs the device nothing. The device quota is charged
            # last and refunded on pipeline failure, so a failure the user
            # didn't cause doesn't consume one of their three daily checks.
            lock_held = try_acquire_device_lock(conn, device_token)
            if not lock_held:
                _http_error(429, "A check is already running for this device — please wait for it to finish")
            if not check_and_increment(conn, f"ip:{client_ip}", IP_DAILY_BACKSTOP, date.today()):
                _http_error(429, "Too many checks from this network today. Try again tomorrow.")
            if not check_and_increment(conn, device_key, FREE_TIER_DAILY_LIMIT, date.today()):
                _http_error(429, "Today's free checks are used up. Try again tomorrow.")

            try:
                return run_live_check(ai_output, sections, client)
            except CheckTooComplex:
                # A property of the submitted output, not a server fault --
                # generic 400, and refund the check charged above so a
                # rejected request doesn't cost the user one of their three.
                logger.warning("live check rejected: fan-out over cap")
                try:
                    decrement(conn, device_key, date.today())
                except Exception:
                    logger.exception("device quota refund failed after fan-out rejection")
                _http_error(400, CHECK_TOO_COMPLEX_DETAIL)
            except Exception:
                logger.exception("live check pipeline failed")
                try:
                    decrement(conn, device_key, date.today())
                except Exception:
                    # A failed refund must not turn the generic 502 into an
                    # unhandled 500 that leaks exception text.
                    logger.exception("device quota refund failed after pipeline failure")
                _http_error(502, "The grounding check failed. Please try again.")
        finally:
            if lock_held:
                try:
                    release_device_lock(conn, device_token)
                except Exception:
                    # Lease expires on its own after LOCK_LEASE_SECONDS, so a
                    # failed release costs a short wait, never a stuck device.
                    logger.exception("device lock release failed")
            conn.close()

    return app
