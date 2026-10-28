# PBDP: Python Battery Data Processing

[![Tests](https://github.com/paramm-team/pbdp/actions/workflows/test_on_push.yml/badge.svg)](https://github.com/paramm-team/pbdp/actions/workflows/test_on_push.yml)

PBDP imports battery cycler measurements into pandas, standardizes units and
column names, labels charge/discharge states, and extracts experiment segments.
**Version 0.1.1 is the final planned maintenance release.** Active feature
development is retired. The package remains available for existing experiments,
with corrected imports and reproducible checks. See
[CHANGELOG.md](CHANGELOG.md) for fixes and upgrade considerations, and
[MAINTENANCE.md](MAINTENANCE.md) for support limits and the direction toward
[PyProBE](https://github.com/ImperialCollegeLondon/PyProBE) for future work.

## Installation

Python 3.8 or newer and pandas 2.0 or newer are required. Python 3.11 is the
recommended environment for reproducing the maintenance checks.

From a checkout of this repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

For a regular installation, download the wheel from the
[v0.1.1 release](https://github.com/paramm-team/pbdp/releases/tag/v0.1.1)
and run `python -m pip install /path/to/pbdp-0.1.1-py3-none-any.whl` inside your
virtual environment. Release artifacts are distributed on GitHub; this is not a
claim of a corresponding PyPI release.

On Windows, use `python -m venv .venv` and activate with
`.venv\Scripts\activate.bat` in Command Prompt, or
`.venv\Scripts\Activate.ps1` in PowerShell.

## Run a complete example

From the repository root, with the package installed:

```bash
python examples/scripts/quickstart.py --output-dir pbdp-demo
```

Choose a new output directory. The example creates synthetic measurements,
imports and checks their units, labels states, selects a segment, and exports
and reloads CSV. It requires no external data. See
[examples/README.md](examples/README.md) for expected results and the status of
the historical notebooks.

## Import and inspect

```python
from pathlib import Path
from pbdp import Parser
from pbdp.segment import segment_data
from pbdp.save import save_file

source = Path("my_experiment.csv")
data = Parser().data_importer(source, save_option="none", state_option="yes")
print(data.head())
print(data.dtypes)

# Adjacent charging CC and CV phases, with current and voltage constraints.
segments = segment_data(data, ["cccv 1A 4.2V"], reset=True)

# Explicitly save only after inspecting the imported measurements.
output = save_file(data, "parquet", source)
print(output)
```

`save_option="none"` leaves the source directory unchanged. The importer defaults
to `save_option="save"`, which writes into `processed/`. `save all` also writes
metadata and extracted tabular data into `pre_processed/`. Repeating a save for
the same source and format can overwrite an earlier output. CSV, Parquet, Pickle
and Feather exports are supported; Parquet preserves typed columns and labels.

Use one input file per call when you need every returned DataFrame. The legacy
directory importer processes each supported file but returns only the last one.
More historical examples are in [examples/](examples/).

For optional identifiers or mixed text columns, pass a pandas `dtype` mapping
using the **raw input header**, before PBDP normalizes column names:

```python
data = Parser().data_importer(
    source, save_option="none", dtype={"Cell ID": str}
)
```

Unspecified columns retain type inference. Standard measurement fields are still
converted to numeric values and validated; this option cannot bypass validation.
Pandas' missing-value handling remains in effect. Leading zeroes must exist in
the input as text; Excel display formatting alone cannot restore them.

## What the maintenance checks cover

The suite combines expected-value unit tests and small synthetic end-to-end
imports. It checks:

- Physical unit conversion and elapsed/absolute time calculations.
- CC/CV adjacency using row order, including nonconsecutive, string and date
  indices; terminal pulses and immediately adjacent rest intervals.
- Source-file preservation, optional missing sensor values and step-number jumps.
- Invalid required measurements and duplicate standardized column names.
- CSV, tab-delimited TXT/MPT/DTA and Excel imports, with representative synthetic
  Digatron, Maccor, Gamry, Novonix and BioLogic headers, plus EIS measurements.
- CSV, Parquet, Pickle and Feather export round trips.

These fixtures cover particular export layouts, not every vendor format or
firmware version. State classification and pulse detection remain heuristic;
review the thresholds and selected segments against your experiment. Header,
metadata and date recognition are also limited. Missing start-time metadata
produces a warning and leaves relative time usable; missing or nonfinite required
measurements raise an error before processed output is saved. When explicitly
requested, state-labelling errors propagate rather than silently returning
unlabelled data.

Segment requests use the existing lowercase syntax, for example `cc`, `cv 4.2V`,
`cccv 1A 4.2V`, `rest, cc 1A`, `cv, rest`, `time 50/200` and `step 10:20`.
The legacy combined-request grammar is limited; prefer `cccv` for constrained
CC/CV pairs. Combined requests allow two unqualified states, or `rest` followed
by one state with a current/voltage constraint; unsupported combinations raise
`ValueError`. `power` and `power 4W` select contiguous non-rest intervals lasting
at least 10 seconds, allowing adjacent power changes up to 0.01 W. This is a
heuristic, so gradual drift can still form a run; a signed target is compared to
power rounded to two decimals. `find_rest` requires unique source index labels
and contiguous segments. Plotting and all vendor variants are not
comprehensively tested.

## Development checks

```bash
python -m pip install -e '.[dev,docs]' build
python -m pytest tests -q
python -m flake8 pbdp tests tools examples/scripts/quickstart.py
python -m coverage run --source=pbdp -m pytest tests
python -m coverage report -m
python -m sphinx -b html docs docs/_build/html -W
python -m build
python -m pip check
python tools/strip_notebooks.py --check
```

CI runs tests on Python 3.8–3.12 on Linux and Python 3.11 on Windows and macOS,
plus lint, documentation and package builds. Consult the linked workflow for
actual results; a configured matrix is not a guarantee of support for all
dependency combinations.

The optional local notebook hook strips execution artifacts from fully staged
notebooks and asks you to review and stage the result. It leaves partially staged
files untouched. See [tools/README.md](tools/README.md) for installation; CI also
checks that committed notebooks are clean.

`create_logger()` writes to stderr by default. To save logs, explicitly pass
`log_file="/path/to/pbdp.log"` in an existing writable directory. The helper no
longer creates a log directory beside the installed package.

## Provenance

PBDP is a collaborative battery-data processing project maintained under
[paramm-team/pbdp](https://github.com/paramm-team/pbdp). Its contributors include
Alexandru Pascu, Ferran Brosa Planella, W. Dhammika Widanage and Philip Grylls.
The original cycler preprocessing notebook and subsequent parser refactor were
contributed by Alexandru Pascu; the package includes later work by the team.
See the Git history and BSD-3-Clause license for attribution.

The historical `MSM_Faraday_Battery_Data_Importer.ipynb` notebook downloads from
an archived, private WMG precursor repository and requires authorized access.
The new synthetic regression fixtures do not require that repository or its data.
