import hashlib
import pathlib
import subprocess

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def pipeline_commit() -> str:
    """Short git SHA of the current commit, or 'unknown' if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True, cwd=_REPO_ROOT,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def source_sha256(sections: list[dict]) -> str:
    """SHA256 of the concatenated section texts, in order — a stable
    identifier for a fixture's source document content."""
    text = "".join(s["text"] for s in sections)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
