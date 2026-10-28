"""The documented offline quickstart must work as an actual command."""
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "examples" / "scripts" / "quickstart.py"


def test_quickstart_cli_roundtrip_and_refuses_overwrite(tmp_path):
    output = tmp_path / "quickstart output"
    command = [sys.executable, str(SCRIPT), "--output-dir", str(output)]
    # Ensure subprocesses use this checkout even if another copy is installed.
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        command, cwd=tmp_path, env=environment, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Verified 11 samples" in result.stdout
    source = output / "synthetic_cycle.csv"
    cleaned = output / "processed" / "synthetic_cycle_cleaned_data.csv"
    cccv = output / "processed" / "synthetic_cccv_cleaned_data.csv"
    assert set(path for path in output.rglob("*") if path.is_file()) == {
        source, cleaned, cccv,
    }
    data = pd.read_csv(cleaned, keep_default_na=False)
    assert data["Current [A]"].tolist() == pytest.approx(
        [1, 1, 1, 1, .7, .4, .2, 0, 0, -.5, -.5]
    )
    assert data["AmpHrs [Ah]"].iloc[-1] == pytest.approx(.005625)
    assert data["Battery State"].tolist() == (
        ["charging"] * 7 + ["rest"] * 2 + ["discharging"] * 2
    )
    period = pd.read_csv(cccv, keep_default_na=False)
    assert period["Time [s]"].tolist() == [0, 5, 10, 15, 20, 25, 30]
    assert period["CCCV"].tolist() == ["CC"] * 4 + ["CV"] * 3
    before = {path: path.read_bytes() for path in (source, cleaned, cccv)}
    second = subprocess.run(
        command, cwd=tmp_path, env=environment, text=True, capture_output=True,
    )
    assert second.returncode != 0
    assert "already exists" in second.stderr
    assert before == {path: path.read_bytes() for path in before}
