from __future__ import annotations

from pathlib import Path

import modal

REPO_ROOT = Path(__file__).resolve().parent  # engine/

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "fastapi==0.139.2",
        "python-multipart==0.0.32",
        "anthropic==0.109.1",
        "pypdf==6.16.2",
        "python-docx==1.2.0",
        "psycopg[binary]==3.3.4",
        "scipy==1.13.1",
        "prov==3.1.0",
    )
    .add_local_python_source("grounding")
)

app = modal.App("grounding-inspector-live", image=image)


@app.function(
    min_containers=1,
    secrets=[
        modal.Secret.from_name("anthropic-api-key"),      # shared with Act Alike — reuse, don't recreate
        modal.Secret.from_name("gi-neon-db"),              # DATABASE_URL
        modal.Secret.from_name("gi-device-token-secret"),  # DEVICE_TOKEN_SECRET
    ],
)
@modal.asgi_app(label="grounding-inspector-live-api")
def fastapi_app():
    import logging
    import os

    import anthropic
    import psycopg

    from grounding.api import create_app

    # Without a configured handler, Python's logging module silently drops
    # anything below WARNING (the root logger's "handler of last resort" only
    # fires at WARNING+), so grounding_inspector.api's logger.info/.exception
    # calls would otherwise never reach `modal app logs` at all.
    #
    # Scope INFO logging to our own logger only. basicConfig on the root
    # logger would also surface INFO from anthropic / httpx / psycopg, some
    # of which log request and response bodies at that level.
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    app_logger = logging.getLogger("grounding_inspector")
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(handler)
    app_logger.propagate = False

    client = anthropic.Anthropic()
    database_url = os.environ["DATABASE_URL"]
    device_token_secret = os.environ["DEVICE_TOKEN_SECRET"].encode("utf-8")

    return create_app(
        client=client,
        db_conn_factory=lambda: psycopg.connect(database_url),
        device_token_secret=device_token_secret,
    )
