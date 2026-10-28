# Examples

## Runnable quickstart

Use [scripts/quickstart.py](scripts/quickstart.py) for the current package API.
From the repository root, with this checkout installed in your Python environment:

```sh
python -m pip install -e .
python examples/scripts/quickstart.py --output-dir /tmp/pbdp-quickstart
```

Choose a new output directory; the script refuses an existing one. On Windows,
use a suitable local path instead of `/tmp/pbdp-quickstart`. Installation needs the
package dependencies; the example itself makes no network requests or downloads.

The script creates an eleven-sample synthetic CSV with current in mA and signed
accumulated charge in mAh. It then:

1. Imports through `pbdp.Parser` without saving or plotting.
2. Checks time, voltage, conversion to A, and the final charge of `0.005625 Ah`.
3. Classifies charging, rest, and discharging, detects CC and CV, and extracts the
   contiguous CC-to-CV charging period (seven samples, from 0 to 30 seconds).
4. Exports the classified trace and charging period through `pbdp.save.save_file`.
5. Reloads both CSVs and checks that values, labels, and timestamps round-trip,
   and that the raw input is unchanged.

The output directory contains:

```text
synthetic_cycle.csv
processed/synthetic_cycle_cleaned_data.csv
processed/synthetic_cccv_cleaned_data.csv
```

CSV readers need `keep_default_na=False` to retain the literal `N/A` phase label
and `parse_dates=["Absolute Time [s]"]` to restore timestamps. See the script for
the complete call. The data is illustrative, not a measured battery experiment;
passing this example does not validate a vendor's full export format or establish
scientific accuracy for a different recording or sampling interval.

The integration test runs the actual command, checks the exported values and
segment boundaries, and verifies that another run cannot overwrite its output:

```sh
python -m pytest tests/integration/test_quickstart.py
```

## Historical examples

These files preserve earlier documentation and the project's development history.
They are not maintained as runnable, offline quickstarts. They were inspected
without execution; their original source and attribution remain intact. They
should not be used as the specification for the current package API or as proof
that its scientific calculations have been tested.

| File | Status and known limitations |
| --- | --- |
| [Data_Importer_Pre_processing_Example.ipynb](notebooks/Data_Importer_Pre_processing_Example.ipynb) | Historical interactive tutorial. Installs from the old `paramm-team/data_processing` URL; download hints use the former `src/input/data` layout. Assumes Jupyter/Colab and bundled vendor files, and writes beside those files. Its whole-directory example includes intentionally invalid fixtures and notes an expected failure. Some text describes an old default export format; `print_option="save"` is not a current plotting option. |
| [Data_Importer_Processing_Example_(Segmenting).ipynb](notebooks/Data_Importer_Processing_Example_%28Segmenting%29.ipynb) | Historical segmentation walkthrough. Uses the same old installation/download setup, Jupyter/Colab detection, bundled Digatron data, and file writes. Its examples have not been rerun as part of maintenance and are not reproducibility checks. Use the synthetic script for the verified current API path. |
| [MSM_Faraday_Battery_Data_Importer.ipynb](notebooks/MSM_Faraday_Battery_Data_Importer.ipynb) | Historical WMG/Faraday workflow. Downloads and unpacks an external repository with shell commands and assumes relative data paths. It retains obsolete requests such as `const curr`/`const voltage`, old helper-function descriptions, and `print_option="all"`; the current plotting option is `"diff"`. Its retained scientific narrative is historical, while executable functionality now lives in `pbdp/`. |
| [scripts/example.py](scripts/example.py) | Legacy function-only demonstration. Running the file directly does nothing because `test_simple()` is never called. Calling it imports bundled Digatron data, writes processed output beside it, and prints a segmentation result without assertions. Use `quickstart.py` instead. |

The notebooks already had empty outputs and null execution counts at the start
of this audit. Remaining transient cell metadata (including Colab output IDs and
runtime display information) has been removed. Source cells, cell IDs, notebook
authorship metadata, kernel information, and narrative history are retained.

## Keep notebook diffs reviewable

The standard-library-only cleaner strips outputs, execution counts, transient
cell metadata, and notebook widget state without executing notebook code:

```sh
python tools/strip_notebooks.py
python tools/strip_notebooks.py --check
```

Both commands default to `examples/notebooks`; explicit notebook files or
directories are also accepted. `--check` exits with status 1 for execution
artifacts and changes nothing, making it suitable for CI. Invalid input exits
with status 2. Already clean files keep their original formatting.

See [tools/README.md](../tools/README.md) for the optional local Git hook, which
checks the staged content and protects partially staged edits.
