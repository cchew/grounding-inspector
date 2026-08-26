from __future__ import annotations

from pathlib import Path

import modal

REPO_ROOT = Path(__file__).resolve().parent  # engine/

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "fastapi>=0.115",
        "python-multipart>=0.0.9",
        "anthropic>=0.30.0",
        "pypdf>=5.0",
        "python-docx>=1.1",
        "psycopg[binary]>=3.2",
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
    import os

    import anthropic
    import psycopg

    from grounding.api import create_app

    client = anthropic.Anthropic()
    database_url = os.environ["DATABASE_URL"]
    device_token_secret = os.environ["DEVICE_TOKEN_SECRET"].encode("utf-8")

    return create_app(
        client=client,
        db_conn_factory=lambda: psycopg.connect(database_url),
        device_token_secret=device_token_secret,
    )
