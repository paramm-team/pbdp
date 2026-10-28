"""Notebook cleanup preserves scientific source and checks staged content."""
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "strip_notebooks", ROOT / "tools" / "strip_notebooks.py"
)
cleaner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleaner)


@pytest.fixture
def notebook():
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"name": "python3", "display_name": "Python 3"},
            "language_info": {"name": "python"},
            "authors": [{"name": "Original author"}],
            "colab": {"authorship_tag": "original-tag", "provenance": []},
            "widgets": {"runtime": "state"},
        },
        "cells": [{
            "cell_type": "code", "id": "stable-id", "execution_count": 4,
            "metadata": {
                "id": "stable-colab-id", "tags": ["parameters"],
                "execution": {"start": "timestamp"}, "trusted": True,
                "colab": {"base_uri": "runtime-url"}, "outputId": "volatile",
            },
            "source": ["print('preserve scientific source: μA')\n"],
            "outputs": [{"output_type": "stream", "text": ["output\n"]}],
        }, {
            "cell_type": "markdown", "metadata": {"tags": ["explanation"]},
            "source": ["Original attribution and explanation."],
            "attachments": {"diagram.png": {"image/png": "original-content"}},
        }],
    }


def test_cleanup_preserves_sources_attachments_and_authorship(notebook):
    raw = json.dumps(notebook).encode()
    cleaned = cleaner.cleaned_bytes(raw)
    result = json.loads(cleaned)
    assert result["cells"][0]["source"] == notebook["cells"][0]["source"]
    assert result["cells"][1] == notebook["cells"][1]
    assert result["cells"][0]["id"] == "stable-id"
    assert result["cells"][0]["outputs"] == []
    assert result["cells"][0]["execution_count"] is None
    assert result["cells"][0]["metadata"] == {
        "id": "stable-colab-id", "tags": ["parameters"],
    }
    assert result["metadata"] == {
        key: value for key, value in notebook["metadata"].items()
        if key != "widgets"
    }
    assert cleaner.cleaned_bytes(cleaned) == cleaned
    assert notebook["cells"][0]["execution_count"] == 4


def test_check_does_not_write_and_cleaning_is_idempotent(tmp_path, notebook):
    path = tmp_path / "example.ipynb"
    raw = json.dumps(notebook).encode()
    path.write_bytes(raw)
    assert cleaner.main(["--check", str(path)]) == 1
    assert path.read_bytes() == raw
    assert cleaner.main([str(path)]) == 0
    cleaned = path.read_bytes()
    assert cleaner.main(["--check", str(path)]) == 0
    assert cleaner.main([str(path)]) == 0
    assert path.read_bytes() == cleaned


@pytest.mark.parametrize("partial", [False, True])
@pytest.mark.parametrize("check", [False, True])
def test_staged_cleanup_never_overwrites_partial_changes(
    tmp_path, notebook, monkeypatch, partial, check,
):
    name = "notebook with spaces.ipynb"
    staged = json.dumps(notebook).encode()
    working = staged + (b"\n" if partial else b"")
    path = tmp_path / name
    path.write_bytes(working)
    calls = []

    def fake_git(*args):
        calls.append(args)
        if args[0] == "diff":
            return name.encode() + b"\0"
        assert args == ("show", ":" + name)
        return staged

    monkeypatch.setattr(cleaner, "ROOT", tmp_path)
    monkeypatch.setattr(cleaner, "git_bytes", fake_git)
    assert cleaner.process_staged(check) == 1
    expected = working if partial or check else cleaner.cleaned_bytes(staged)
    assert path.read_bytes() == expected
    assert [call[0] for call in calls] == ["diff", "show"]


def test_existing_notebooks_are_clean():
    assert cleaner.main(["--check", str(ROOT / "examples" / "notebooks")]) == 0
