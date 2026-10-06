"""Restore archive provenance from verified sources before reserving any cell.

External launch plumbing only: no Agent, Worker, network or ledger mutations.
Do not infer a revision from the development checkout or print inherited secrets.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path

REVISION_VARIABLE = "INFRA_JOINT_CODE_REVISION"


def pinned_environment(
    app: Path,
    freeze_path: Path,
    expected_freeze_file_sha256: str,
    inherited: Mapping[str, str],
) -> dict[str, str]:
    """Fill missing provenance, rejecting conflicts and every bound-source drift."""
    if (app.is_symlink() or not app.is_dir() or freeze_path.is_symlink()
            or re.fullmatch(r"[0-9a-f]{64}", expected_freeze_file_sha256) is None):
        raise RuntimeError("a pinned archive and immutable freeze are required")
    raw = freeze_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_freeze_file_sha256:
        raise RuntimeError("launch execution-freeze file drift")
    value = json.loads(raw)
    revision = value.get("commit_sha")
    sources = value.get("source_sha256")
    if (not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None
            or not isinstance(sources, dict) or not sources):
        raise RuntimeError("launch freeze lacks exact revision/source provenance")
    if REVISION_VARIABLE in inherited and inherited[REVISION_VARIABLE] != revision:
        raise RuntimeError("inherited archive revision conflicts with the execution freeze")
    base = app.resolve()
    for relative, digest in sources.items():
        if (not isinstance(relative, str) or not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None):
            raise RuntimeError("launch source provenance malformed")
        path = Path(relative)
        source = app / path
        if (path.is_absolute() or ".." in path.parts or source.is_symlink()
                or not source.resolve().is_relative_to(base)
                or hashlib.sha256(source.read_bytes()).hexdigest() != digest):
            raise RuntimeError("launch frozen source drift or escaped source path")
    return {**inherited, REVISION_VARIABLE: revision}
