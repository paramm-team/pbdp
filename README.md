# PBDP Python Battery Data Processing

[![Tests](https://github.com/paramm-team/pbdp/actions/workflows/test_on_push.yml/badge.svg)](https://github.com/paramm-team/pbdp/actions/workflows/test_on_push.yml/badge.svg)
[![codecov](https://codecov.io/gh/paramm-team/data_processing/graph/badge.svg?token=7Xmov38bCi)](https://codecov.io/gh/paramm-team/data_processing)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

This package provides tools to process and handle battery cycler experimental data. Examples on how to run this package can be found in the [examples folder](./examples)

## 🚀 Installing python-battery-data-processing

```bash
pip install virtualenv
```

The module dependencies are listed in `pyproject.toml`, the dependancies which are non optional which are installed with the package.

The optional dependencies are split into `dev` and `docs`. `dev` are used for testing and linting, `docs` are used for building the sphinx documentation.

### Linux & MacOS

1. Create a virtual environment (this is strongly recommended to avoid clashes with the dependencies)

    ```bash
    virtualenv --python="<path to python 3.11>" env
    ```

2. Activate the virtual environment

    ```bash
    source env/bin/activate
    ```

    The virtual environment can later be deactivated (if needed) by running

    ```bash
    deactivate
    ```

3. Install packages into the virtual environment

    ```bash
    pip install -e ./[dev,docs]
    ```

### Windows

1. Create a virtual environment (this is strongly recommended to avoid clashes with the dependencies)

    ```bash
    python -m virtualenv env
    ```

2. Activate the virtual environment

    ```bash
    env\Scripts\activate.bat
    ```

    The virtual environment can later be deactivated (if needed) by running

    ```bash
    deactivate
    ```

3. Install package

    ```bash
    pip install -e .\\[dev,docs]
    ```

## Provenance

PBDP is a collaborative battery-data processing project maintained under
[paramm-team/pbdp](https://github.com/paramm-team/pbdp). Its contributors include
Alexandru Pascu, Ferran Brosa Planella, W. Dhammika Widanage and Philip Grylls.
The original cycler preprocessing notebook and subsequent parser refactor were
contributed by Alexandru Pascu; the package includes later work by the team.
See the Git history and BSD-3-Clause license for attribution.

## Data integrity and regression checks

The regression suite uses synthetic measurements with known physical values.
Run it from an editable development installation:

```bash
python -m pip install -e '.[dev]'
python -m pytest tests
python -m flake8 pbdp tests
python -m coverage run --source=pbdp -m pytest tests
python -m coverage report -m
```

The suite checks mA-to-A, mAh-to-Ah and coulomb-to-Ah conversion, elapsed-time
handling, CC/CV selection, source-file preservation, and Parquet round trips
that retain state labels and nullable data. Synthetic end-to-end cases exercise
CSV, tab-delimited TXT/MPT/DTA and Excel imports. These fixtures validate the
covered paths; they do not establish support for every vendor export variant.

Behavior to account for when upgrading:

- `<I>/mA` and `I/mA` are multiplied by `0.001`; `(Q-Qo)/mA.h` by `0.001`;
  `Charge (C)` by `1/3600`. Reprocess affected exports from older versions.
- `Time [s]` is elapsed time since the experiment start, not per-row increments.
  Absolute timestamps add that duration directly to the parsed start time.
- `cccv` requests include an adjacent charging CC phase and CV phase, and apply
  the requested current/voltage filters. A recording may end during CV.
- Imports parse data in memory and do not create fixed temporary files beside
  the input. The standalone `convert_xlsx_to_csv()` helper returns a unique
  temporary path; its caller must remove that file after use.
- With `save_option="save all"`, Excel's extracted tabular data is saved as CSV.
  Explicit saves still write to `pre_processed/` and/or `processed/` and can
  replace earlier output files with the same names.

The package remains under development. State classification uses heuristics;
review its thresholds for your experiment. Metadata/date parsing and vendor
format coverage still have limitations, and importer warnings should be
reviewed before relying on a result.

The historical `MSM_Faraday_Battery_Data_Importer.ipynb` notebook downloads from
an archived, private WMG precursor repository and requires authorized access.
The automated synthetic tests do not depend on that repository or its data.
