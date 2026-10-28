# Final maintenance release and future direction

PBDP 0.1.1 is the final planned maintenance release of this project. It repairs
known data-integrity problems, adds reproducible regression checks and provides a
self-contained example for existing users. Active feature development is retired;
there is no commitment to new vendor formats or future dependency compatibility.
The source, attribution, examples and release artifacts remain available under
the BSD-3-Clause license. This notice does not imply that GitHub has archived the
team repository.

## Existing experiments

Keep the original instrument exports and record the PBDP version and environment
used for analysis. Reprocess affected older imports: the maintenance release
corrects current/capacity unit conversions, elapsed-time handling, silently lost
rows and segment boundaries. See [CHANGELOG.md](CHANGELOG.md) for details.

Start with the [synthetic quickstart](examples/README.md), then inspect columns,
units, timestamps and selected segments against your own experiment before using
the results. Validation covers representative layouts and expected-value cases;
it is not certification of every instrument export. The legacy string query API,
heuristic classification and directory import's last-DataFrame return value are
retained. A redesigned segmentation API is outside this final release.

## New work and migration

For new battery-data processing work, evaluate
[PyProBE](https://github.com/ImperialCollegeLondon/PyProBE) and its
[documentation](https://pyprobe.readthedocs.io/en/latest/). It provides a battery
experiment processing framework using Polars and Parquet. The intent is to
contribute relevant experience and improvements to an active shared project
rather than continue a separate PBDP feature roadmap. No partnership or migration
adapter is implied.

PyProBE is not a drop-in replacement for PBDP. Prefer importing the original
instrument files into the target tool, mapping experiment metadata explicitly,
and comparing units, timestamps, row counts and segment boundaries on a known
experiment. A PBDP Parquet file preserves its columns and types, but that alone
does not make it a PyProBE-compatible dataset. Consult the target project's
supported import formats and schema before converting existing outputs.

Potential contributions should start with a small reproducible issue, expected
scientific results and tests, following the target project's
[contributing guidance](https://github.com/ImperialCollegeLondon/PyProBE/blob/main/CONTRIBUTING.md).
Historical data and private precursor notebooks are not needed to reproduce the
public maintenance tests.

## Release contents

The GitHub release provides a wheel, a source distribution and SHA-256 checksums.
Install the wheel in a virtual environment, or build from the tagged source.
Publishing a GitHub release does not publish a package to PyPI. The README lists
the supported maintenance test matrix and remaining limitations.
