PBDP: Python Battery Data Processing
======================================

PBDP imports battery cycler measurements into pandas, standardizes units and
column names, and selects charge/discharge segments. The maintenance update
prioritizes data correctness and source-file preservation.

Installation
------------

Use Python 3.8 or newer (3.11 recommended), create a virtual environment, and
install from a checkout::

    python -m pip install -e .

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
