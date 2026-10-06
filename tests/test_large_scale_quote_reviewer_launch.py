import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("external_entrypoint", [False, True])
def test_actual_script_entrypoint_resolves_the_intended_reviewer(
    tmp_path: Path, external_entrypoint: bool,
) -> None:
    """PYTHONPATH alone cannot supersede a script's sibling frozen reviewer."""
    repository = Path(__file__).resolve().parents[1]
    scripts = repository / "scripts"
    app = tmp_path / "frozen-app-scripts"
    external = tmp_path / "external-review-tools"
    app.mkdir()
    external.mkdir()
    name = "large_scale_resident_quote_repair_queue_v1.py"
    for directory in (app, external):
        shutil.copyfile(scripts / name, directory / name)
    # --help exercises the real module import path without actions or a queue.
    # The app's obsolete reviewer must not be modified to fix an offline launch.
    old = app / "large_scale_quote_repair_ledger_v1.py"
    old.write_text("OBSOLETE_REVIEWER = True\n", encoding="utf-8")
    shutil.copyfile(scripts / old.name, external / old.name)
    before = old.read_bytes()
    process = subprocess.run(
        [sys.executable, "-v", str((external if external_entrypoint else app) / name), "--help"],
        env={**os.environ, "PYTHONPATH": os.pathsep.join(map(str, (
            external, repository / "src", scripts,
        )))}, cwd=tmp_path, capture_output=True, text=True, check=False, timeout=30,
    )
    assert process.returncode == 0, process.stderr[-2000:]
    loaded = "\n".join(line for line in process.stderr.splitlines() if old.name in line)
    expected = external if external_entrypoint else app
    assert str(expected) in loaded
    assert str(app if external_entrypoint else external) not in loaded
    assert old.read_bytes() == before
