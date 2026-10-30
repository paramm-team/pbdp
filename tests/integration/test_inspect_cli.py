"""Exercise the installed module entry point with synthetic input only."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pbdp


def run_inspect(source, *arguments):
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(pbdp.__file__).resolve().parent.parent)
    return subprocess.run(
        [sys.executable, '-m', 'pbdp', 'inspect', str(source), *arguments],
        cwd=source.parent, env=env, text=True, capture_output=True, check=False,
    )


def test_inspect_command_is_read_only_and_reports_explicit_conventions(tmp_path):
    source = tmp_path / 'synthetic.csv'
    source.write_text('TestTime,Current [A],Voltage [V],Md\n'
                      '0,1,3.5,C\n1,1,3.6,D\n', encoding='utf-8')
    original = source.read_bytes()
    result = run_inspect(
        source, '--time-unit', 'TestTime=min', '--mode-column', 'Md',
        '--mode', 'C=charging', '--mode', 'D=discharging', '--states',
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert json.loads(result.stdout)['status'] == 'ok'
    assert source.read_bytes() == original
    assert list(tmp_path.iterdir()) == [source]


def test_inspect_command_fails_cleanly_for_ambiguous_time(tmp_path):
    source = tmp_path / 'ambiguous.csv'
    source.write_text('TestTime,Current [A],Voltage [V]\n0,1,3.5\n', encoding='utf-8')
    result = run_inspect(source)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report['status'] == 'error'
    assert 'time_units' in result.stdout
    assert list(tmp_path.iterdir()) == [source]


def test_inspect_command_rejects_duplicate_configuration(tmp_path):
    result = run_inspect(tmp_path / 'not-read.csv', '--time-unit', 'TestTime=s',
                         '--time-unit', 'TestTime=min')
    assert result.returncode == 2
    assert 'Duplicate --time-unit' in result.stderr
    assert not list(tmp_path.iterdir())
