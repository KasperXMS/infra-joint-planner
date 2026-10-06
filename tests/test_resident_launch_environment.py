"""Launch provenance is checked before a controller can reserve a real cell."""

from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
launch = importlib.import_module("large_scale_resident_launch_environment_v1")


def fixture(tmp_path):
    app = tmp_path / "archive"
    source = app / "scripts/atomic.py"
    source.parent.mkdir(parents=True)
    source.write_text("# frozen\n", encoding="utf-8")
    value = {"commit_sha": "a" * 40, "source_sha256": {
        "scripts/atomic.py": hashlib.sha256(source.read_bytes()).hexdigest()}}
    path = tmp_path / "execution-freeze-004.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return app, source, path, value


@pytest.mark.parametrize("present", [False, True])
def test_missing_revision_is_restored_from_actual_freeze_without_changing_other_env(
    tmp_path, present,
):
    app, _, path, _ = fixture(tmp_path)
    inherited = {"PRIVATE_API_SECRET": "do-not-print", "PYTHONPATH": "exact/import/scope"}
    if present:
        inherited[launch.REVISION_VARIABLE] = "a" * 40
    original = dict(inherited)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    result = launch.pinned_environment(app, path, digest, inherited)
    assert result == {**inherited, launch.REVISION_VARIABLE: "a" * 40}
    assert inherited == original
    assert not list(tmp_path.glob("phase1-attempts*"))


@pytest.mark.parametrize("revision", ["b" * 40, "", "main", "a" * 39])
def test_conflicting_inherited_revision_is_not_silently_replaced(tmp_path, revision):
    app, _, path, _ = fixture(tmp_path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(RuntimeError, match="conflicts"):
        launch.pinned_environment(app, path, digest, {launch.REVISION_VARIABLE: revision})


@pytest.mark.parametrize("damage", ["freeze", "source", "digest", "revision", "sources",
                                    "absolute", "escape", "source_digest", "missing_source"])
def test_every_provenance_failure_precedes_any_reservation(tmp_path, damage):
    app, source, path, value = fixture(tmp_path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if damage == "freeze":
        path.write_text("{}")
    elif damage == "source":
        source.write_text("changed")
    elif damage == "digest":
        digest = "invalid"
    else:
        if damage == "revision":
            value["commit_sha"] = "main"
        elif damage == "sources":
            value["source_sha256"] = {}
        elif damage == "absolute":
            value["source_sha256"] = {str(source.resolve()): "b" * 64}
        elif damage == "escape":
            value["source_sha256"] = {"../outside.py": "b" * 64}
        elif damage == "source_digest":
            value["source_sha256"] = {"scripts/atomic.py": "invalid"}
        elif damage == "missing_source":
            value["source_sha256"] = {"missing.py": "b" * 64}
        path.write_text(json.dumps(value))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises((RuntimeError, FileNotFoundError)):
        launch.pinned_environment(app, path, digest, {})
    assert not list(tmp_path.glob("phase1-attempts*"))
