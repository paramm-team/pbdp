#!/usr/bin/env python3
"""Strip notebook execution artifacts without executing cells or loading kernels.

With no paths, process examples/notebooks. --check reports dirty files without
changing them. --staged is for the Git hook: clean fully staged working copies,
then fail so the author can review and stage the cleanup. Never stage changes.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CELL_TRANSIENT = {
    "collapsed", "scrolled", "trusted", "execution", "ExecuteTime",
    "executionInfo", "execution_count", "outputId", "colab",
}


def stripped_notebook(notebook: dict) -> dict:
    """Preserve sources, attachments, IDs, tags, kernels, and author metadata."""
    cleaned = deepcopy(notebook)
    if cleaned.get("nbformat") != 4 or not isinstance(cleaned.get("cells"), list):
        raise ValueError("expected a version 4 Jupyter notebook")
    metadata = cleaned.setdefault("metadata", {})
    for key in ("widgets", "signature", "execution", "ExecuteTime"):
        metadata.pop(key, None)
    # Colab's authorship_tag and other provenance information are retained.
    for cell in cleaned["cells"]:
        cell_metadata = cell.setdefault("metadata", {})
        for key in CELL_TRANSIENT:
            cell_metadata.pop(key, None)
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
    return cleaned


def cleaned_bytes(raw: bytes) -> bytes:
    notebook = json.loads(raw)
    cleaned = stripped_notebook(notebook)
    if cleaned == notebook:
        return raw  # Do not create formatting-only diffs.
    return (json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def git_bytes(*args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def process_staged(check: bool) -> int:
    names = git_bytes(
        "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z",
        "--", "*.ipynb",
    ).decode("utf-8").split("\0")
    dirty = False
    for name in filter(None, names):
        raw = git_bytes("show", ":" + name)
        cleaned = cleaned_bytes(raw)
        if cleaned == raw:
            continue
        dirty = True
        path = ROOT / name
        if check:
            print(f"Notebook execution artifacts staged: {name}")
        elif path.read_bytes() != raw:
            print(f"Unstaged changes in {name}; leaving the working copy untouched.")
        else:
            path.write_bytes(cleaned)
            print(f"Stripped {name}; review and stage the cleanup before committing.")
    if dirty:
        print("Run python tools/strip_notebooks.py, review, then stage the notebooks.")
    return int(dirty)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--staged", action="store_true")
    args = parser.parse_args(argv)
    if args.staged and args.paths:
        parser.error("--staged cannot be combined with paths")
    try:
        if args.staged:
            return process_staged(args.check)
        paths = args.paths or [ROOT / "examples" / "notebooks"]
        notebooks = set()
        for path in paths:
            if path.is_dir():
                notebooks.update(path.rglob("*.ipynb"))
            elif path.is_file() and path.suffix == ".ipynb":
                notebooks.add(path)
            else:
                raise ValueError(f"not a notebook file or directory: {path}")
        if not notebooks:
            raise ValueError("no notebooks found")
        dirty = False
        for path in sorted(notebooks):
            raw = path.read_bytes()
            cleaned = cleaned_bytes(raw)
            if cleaned != raw:
                dirty = True
                if args.check:
                    print(f"Notebook execution artifacts: {path}")
                else:
                    path.write_bytes(cleaned)
                    print(f"Stripped {path}")
        return int(dirty and args.check)
    except (OSError, ValueError, KeyError, TypeError,
            subprocess.CalledProcessError) as exc:
        print(f"Notebook cleanup failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
