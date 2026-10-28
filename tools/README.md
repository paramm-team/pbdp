# Notebook hygiene

`strip_notebooks.py` requires only Python's standard library. It reads Jupyter
version 4 JSON; it does not import notebook code, execute cells, start kernels,
install packages, or download data.

From the repository root:

```sh
python tools/strip_notebooks.py          # clean examples/notebooks
python tools/strip_notebooks.py --check # read-only check for CI
python tools/strip_notebooks.py path/to/notebook.ipynb
```

The cleaner removes outputs, execution counts, runtime cell metadata (including
Colab output IDs, execution timing, trust flags, and output display state), and
notebook widget/signature state. It retains source, Markdown attachments, cell
IDs, tags, kernel/language information, and authorship/provenance metadata. It
does not rewrite formatting when a notebook is already clean.

## Optional local pre-commit hook

To opt into the repository's hook for your checkout, run:

```sh
git config --local core.hooksPath tools/hooks
```

This selects the repository's hooks directory in place of any existing local
hooks path. If you already use another hook manager, invoke
`python tools/strip_notebooks.py --staged` from your existing pre-commit hook
instead. The hook is supplied but not activated by maintenance or the tests.

By default the hook uses `python3`; set `PBDP_PYTHON` to your interpreter path if
needed. It examines staged notebooks, including names with spaces. When outputs
are staged and the working copy exactly matches the staged file, it strips the
working copy and stops the commit so you can review and stage the cleanup. It
never runs `git add` or modifies the index. If a notebook also has unstaged edits,
the hook leaves it untouched and stops the commit; clean it explicitly, review
the result, and stage the intended changes before retrying.

Use `python tools/strip_notebooks.py --staged --check` to inspect staged content
without editing any working files. A dirty notebook exits 1, valid clean input
exits 0, and an input/read error exits 2. Deleted notebooks are ignored.
