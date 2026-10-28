# Changelog

## 0.1.1 (2026-10-28) - final maintenance release

### Data correctness and preservation

- Correct mA-to-A, mAh-to-Ah and coulomb-to-Ah conversion factors. Previously
  affected imports must be reprocessed from the original exports.
- Treat elapsed seconds as elapsed time, without accumulating them a second time
  when constructing absolute timestamps.
- Preserve valid rows after step-number jumps and rows with missing optional
  sensor values. Strip leading units rows, but reject invalid required values.
- Validate required, finite measurements even when start-time metadata is absent;
  check three-electrode voltage using the signed working-minus-counter potential.
- Detect whole header lines, preserve delimiter-prefixed headers, normalize
  surrounding whitespace and reject duplicate raw or standardized columns before
  ambiguous measurements can be renamed by pandas.
- Read imports in memory and remove fixed temporary filenames that could overwrite
  or delete neighbouring files. The standalone Excel-to-CSV helper returns a unique
  temporary path; callers remain responsible for removing that path after use.

### Segmentation and output

- Match complete request names so `cccv` and `discharging` reach the correct branch;
  reject empty/unknown simple requests and normalize whitespace.
- Use row positions for adjacent phases and automatic classification, preserving
  original index labels even when labels repeat.
- Keep terminal CC/CV phases, constrain current/voltage correctly for supported
  requests, and avoid reading past the end of a recording during pulse detection.
- Include only immediately adjacent rest rows, including rest at the recording end.
- Return a DataFrame for whole-time requests and handle resetting empty segments.
- Preserve labels and nullable types in Parquet; repair Feather export and retain
  dotted source stems in output names. Reject unsupported formats before creating
  output directories, including preprocessing artifacts during `save all` imports.

### Validation and compatibility

- Add expected-value regressions and synthetic vendor-header integration fixtures.
- Restore CI with pinned action revisions, Python 3.8–3.12 Linux jobs and Python
  3.11 Windows/macOS jobs; run lint, documentation and package checks separately.
- Replace deprecated in-place header renaming for pandas 3.1 compatibility.
- Declare Python >=3.8 and pandas >=2.0 requirements; clarify installation,
  validation limits, source provenance and output behaviour.

### Final usability and release work

- Add optional raw-header `dtype` mappings to the reader/importer, preserving
  text identifiers without bypassing numeric measurement validation.
- Repair sustained constant-power selection and reject malformed combined
  segment requests explicitly; retain the legacy string API.
- Make logging safe for installed packages: stderr by default, optional explicit
  file output, and no duplicate handlers on repeated setup.
- Add a synthetic import/classify/segment/export/reload quickstart, expected-value
  power and plotting checks, and an audit of the historical notebooks.
- Add a notebook cleanup tool, optional local Git hook and CI cleanliness check.
- Remove obsolete setup.py and the broken in-package demo; use pyproject.toml
  as the sole packaging configuration. Include examples, tools and lint settings
  in the source distribution and exercise the installed wheel in CI.
- Configure Read the Docs to install the package's documentation dependencies.
- Document final-maintenance status, compatibility limits and the direction
  toward PyProBE. A segmentation API redesign is deferred.

### Upgrade considerations

Imports that previously silently dropped invalid measurements or skipped validation
can now raise `ValueError`. Requested state-labelling failures also propagate.
Missing start-time metadata remains recoverable and does not invent timestamps.
Output names retain all dots in the source stem. Explicit saves can still replace
existing outputs. Directory imports still return only the last DataFrame. `create_logger()` no
longer writes a file by default; pass `log_file` to request file logging.

This update does not certify every vendor export or replace heuristic state
classification. Active feature development is retired after this final planned
maintenance release; see [MAINTENANCE.md](MAINTENANCE.md).
