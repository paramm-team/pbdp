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
The source branch also contains an unreleased import-correctness follow-up;
the inspection and configuration examples below require that source version.
They are not included in the published v0.1.1 wheel.

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

For numeric Maccor `TestTime` values, declare the source unit explicitly.
Check the instrument's export settings; the same header can represent different
units:

```python
parser = Parser(time_units={"TestTime": "min"})  # only for a minutes export
data = parser.data_importer(source, save_option="none")
```

Use `"s"` for seconds. Without a declared unit, numeric `TestTime` values
raise an error instead of guessing. Duration strings such as `01:30:00` retain
their own meaning; explicit headers such as `TestTime(s)` and `Run Time (h)`
retain their declared seconds and hours. The normalized output is `Time [s]`.
Supported unit names are `s`, `min`, `h`, `ms`, `us`, `ns` and `d`. Unit mappings
use raw column names and cannot contradict explicit header units or configured
`standard_units` factors.

Version 0.1.1 incorrectly interpreted numeric `TestTime` values as nanoseconds.
Reimport affected recordings from the originals with the correct source unit;
this error also affected generated timestamps and duration-based CC/CV detection.

### Current direction and rest threshold

Positive current means charging and negative current means discharging. For an
export that records unsigned current and a separate mode field, explicitly
declare the instrument's convention:

```python
parser = Parser(
    time_units={"TestTime": "min"},  # only if this export records minutes
    current_mode_column="Md",
    current_mode_map={"C": "charging", "D": "discharging", "R": "rest"},
    current_epsilon=0.001,
)
data = parser.data_importer(source, save_option="none", state_option="yes")
```

These example mode codes are caller-provided, not a universal vendor mapping.
Every observed mode must be mapped; unknown modes and rest modes with current
above the configured threshold raise an error. The original imported current,
after conversion to amperes, is preserved in `Source current [A]`. Only the sign
of `Current [A]` changes for charging/discharging modes; capacity and energy
conventions are unchanged. Without a mode map, imported current stays unchanged.

Rest includes both threshold boundaries: `abs(current) <= current_epsilon`.
The default is 0.001 A. The threshold follows the DataFrame through state
labelling and segmentation in `data.attrs["pbdp_current_epsilon"]`.

### Inspect an import without saving

```python
report = parser.inspect_file(source, state_option="yes")
print(report["status"])        # "ok" or "error"
print(report["columns"])       # column mapping, factor and conversion basis
print(report["errors"])
```

The JSON-compatible report includes the source hash, detected header and metadata,
raw-to-standard column mappings, unit decisions, cleanup counts, normalization
provenance, warnings and validation errors. Offending rows use **1-based parsed
data-record numbers**, not physical file lines; row samples are bounded and include
total counts. Reports contain source paths and metadata, so treat them with the
same care as the input. Inspection reads one file and creates no output files.
An error is returned in the report; normal `data_importer` calls still raise it.

Cleanup distinguishes genuinely empty records, leading units rows and a narrowly
recognized terminal record-count footer. That footer must occupy a single cell
and its declared count must match the preceding parsed records; other nonempty
invalid rows are rejected. Cleanup reasons are included in the report.

The same inspection is available from the terminal:

```bash
python -m pbdp inspect my_experiment.csv --states
python -m pbdp inspect my_experiment.csv --time-unit 'TestTime=min' \
  --mode-column Md --mode C=charging --mode D=discharging --mode R=rest --states
```

JSON goes to stdout, logs to stderr. Exit codes are 0 for a valid import, 1 for
an import error, and 2 for invalid command options. CLI mode keys are strings;
use the Python mapping for numeric mode codes. Inspection validates measurements
and optionally counts battery states; it does not certify CC/CV phase labels.

### Configure CC/CV classification

```python
from pbdp.states import find_cc_and_cv

find_cc_and_cv(data, voltage_epsilon=0.002, time_t=10, max_gap_s=5)
segments = segment_data(data, ["cc", "cv", "cccv", "rest"])

# Explicit options recompute labels on a copy when selecting segments.
segments = segment_data(data, ["cccv"], classification_options={
    "current_epsilon": 0.0001, "voltage_epsilon": 0.002,
    "time_t": 10, "max_gap_s": 5,
})
```

The classifier checks each plateau's full maximum-minus-minimum range and elapsed
duration, with CC taking precedence over CV. It no longer uses row-count lookbacks
by default. Rest, direction changes and repeated timestamps split intervals;
decreasing/nonfinite time is rejected. `max_gap_s` optionally splits recording gaps
and must reflect the experiment's acquisition interval; no gap size is inferred.
Segmentation preserves these boundaries, including when pairing CC/CV or adding
rest. Explicit legacy `rest_t` or `cc_t` arguments retain their historical
row-context gate, with defaults of 8 and 5 for the unspecified argument.

Classification settings are recorded in `data.attrs["pbdp_classification"]`.
Segmentation preserves complete existing labels unless `classification_options`
are supplied; missing labels use the recorded settings. CSV does not preserve
these attributes, so pass the intended options again after reloading CSV.
Observed sampling still limits phase detection. Review the labels against the
protocol; these rules describe measurements and do not infer the instrument's
control mode.

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
- Consistent header matching for conversion and renaming, retaining SI prefix
  case (mA and MA are different units).
- Explicit mode mappings, inclusive rest thresholds, plateau drift, irregular
  sampling, recording gaps, and inspection reports/terminal exit codes.

These fixtures cover particular export layouts, not every vendor format or
firmware version. State classification and pulse detection remain heuristic;
review the thresholds and selected segments against your experiment. Header,
metadata and date recognition are also limited. Missing start-time metadata
produces a warning and leaves relative time usable; missing or nonfinite required
measurements raise an error before processed output is saved. When explicitly
requested, state-labelling errors propagate rather than silently returning
unlabelled data.

Mixed cycling/EIS tables are rejected before cleanup can discard valid cycling
rows that lack impedance measurements. Select separate cycling and EIS tables
explicitly; automatic splitting of combined recordings is not provided.

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
