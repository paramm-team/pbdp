# Data processing package (provisional name)

[![Tests](https://github.com/paramm-team/data_processing/actions/workflows/test_on_push.yml/badge.svg)](https://github.com/paramm-team/data_processing/actions/workflows/test_on_push.yml/badge.svg)
[![codecov](https://codecov.io/gh/paramm-team/data_processing/graph/badge.svg?token=7Xmov38bCi)](https://codecov.io/gh/paramm-team/data_processing)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**WARNING:** this package is still under development.

This package is provides parameter optimization for PyBaMM (Python Battery Mathematical Modelling) using different optimization techniques. Examples on how to run this package can be found in the [examples folder](./examples)

## 🚀 Installing pybamm-param

```bash
pip install virtualenv
```

The module dependencies are listed in `pyproject.toml`, the dependancies which are non optional which are installed with the package.

The optional dependancies are split into `dev` and `docs`. `dev` are used for testing and linting, `docs` are used for building the sphinx documentation.

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
