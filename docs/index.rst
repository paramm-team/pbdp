PBDP: Python Battery Data Processing
======================================

PBDP imports battery cycler measurements into pandas, standardizes units and
column names, and selects charge/discharge segments. Version 0.1.1 is the final
planned maintenance release. Active feature development is retired; the source
and release artifacts remain available for existing experiments. See the
`maintenance notice <https://github.com/paramm-team/pbdp/blob/main/MAINTENANCE.md>`_
for limits and the direction toward PyProBE for new work.

Installation
------------

Use Python 3.8 or newer (3.11 recommended), create a virtual environment, and
install from a checkout::

    python -m pip install -e .

Alternatively, download the wheel from the
`v0.1.1 GitHub release <https://github.com/paramm-team/pbdp/releases/tag/v0.1.1>`_
and install it with ``python -m pip install /path/to/pbdp-0.1.1-py3-none-any.whl``.
This release is distributed on GitHub; it does not claim a PyPI publication.

Runnable example
----------------

From a checkout with the package installed, run::

    python examples/scripts/quickstart.py --output-dir pbdp-demo

Choose a new output directory. The script creates a synthetic CSV and checks
units, state classification, CC/CV boundaries and CSV export/reload without
external data. The
`examples guide <https://github.com/paramm-team/pbdp/blob/main/examples/README.md>`_
lists expected results and explains which notebooks are historical.

Import and inspect
------------------

.. code-block:: python

    from pathlib import Path
    from pbdp import Parser
    from pbdp.segment import segment_data

    data = Parser().data_importer(
        Path("my_experiment.csv"), save_option="none", state_option="yes"
    )
    segments = segment_data(data, ["cccv 1A 4.2V"], reset=True)

Inspect imported columns, units and selected segments before analysis.
``save_option="none"`` avoids writing output files; the default ``save`` writes
into ``processed/`` and may replace earlier output for the same source.

Use ``dtype={"Cell ID": str}`` in ``data_importer`` or ``read_data_to_pandas`` to
retain optional text identifiers. Keys are raw input headers. Measurement fields
are still normalized and validated numerically; pandas missing-value handling
remains in effect. Unspecified columns retain inferred types.

``create_logger()`` writes to stderr by default. Pass ``log_file`` explicitly to
write to a file in an existing writable directory. It does not write beside the
installed package, and repeated calls do not duplicate its output handlers.

Validation and limits
---------------------

Missing or nonfinite required measurements raise an error. Missing start-time
metadata is reported as a warning and does not prevent relative-time analysis.
State classification, pulse detection, vendor-header and date recognition retain
heuristic or format-specific assumptions. Directory imports return only the last
processed DataFrame; call once per file when every result is needed.

The repository README contains supported query examples, development checks and
provenance. CHANGELOG.md describes the maintenance fixes and upgrade considerations.
The synthetic fixtures exercise representative layouts, not every vendor variant.
