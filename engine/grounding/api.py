from __future__ import annotations

import logging
from datetime import date

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from grounding.ingest import DocumentTooLarge, UnsupportedFileType, extract_reference_document
from grounding.live import run_live_check
from grounding.quota import check_and_increment, mint_device_token, try_acquire_device_lock, verify_device_token

logger = logging.getLogger("grounding_inspector.api")

MAX_AI_OUTPUT_CHARS = 20_000
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
FREE_TIER_DAILY_LIMIT = 3
IP_DAILY_BACKSTOP = 50
DEVICE_TOKEN_COOKIE = "gi_device_token"

ALLOWED_ORIGINS = [
    "https://grounding-inspector.netlify.app",
    "http://localhost:5173",
]


def create_app(client, db_conn_factory, device_token_secret: bytes) -> FastAPI:
    app = FastAPI(title="grounding-inspector-live", version="0.1.0")
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
            httponly=True, secure=True, samesite="lax", max_age=60 * 60 * 24 * 365,
        )
        return new_token

    @app.post("/check")
    def post_check(
        request: Request,
        response: Response,
        ai_output: str = Form(...),
        reference_file: UploadFile = File(...),
    ) -> dict:
        if len(ai_output) > MAX_AI_OUTPUT_CHARS:
            raise HTTPException(status_code=400, detail=f"AI output exceeds {MAX_AI_OUTPUT_CHARS} characters")

        file_bytes = reference_file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Reference document exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)}MB",
            )

        try:
            sections = extract_reference_document(reference_file.filename or "upload.txt", file_bytes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        device_token = _resolve_device_token(request, response)
        client_ip = request.client.host if request.client else "unknown"

        conn = db_conn_factory()
        try:
            if not try_acquire_device_lock(conn, device_token):
                raise HTTPException(
                    status_code=429,
                    detail="A check is already running for this device — please wait for it to finish",
                )
            if not check_and_increment(conn, f"device:{device_token}", FREE_TIER_DAILY_LIMIT, date.today()):
                raise HTTPException(status_code=429, detail="Today's free checks are used up. Try again tomorrow.")
            if not check_and_increment(conn, f"ip:{client_ip}", IP_DAILY_BACKSTOP, date.today()):
                raise HTTPException(
                    status_code=429, detail="Too many checks from this network today. Try again tomorrow.",
                )

            try:
                return run_live_check(ai_output, sections, client)
            except Exception:
                logger.exception("live check pipeline failed")
                raise HTTPException(status_code=502, detail="The grounding check failed. Please try again.")
        finally:
            conn.close()

    return app
