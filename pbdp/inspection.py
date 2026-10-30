"""Read-only import diagnostics; reports contain JSON values, never frames."""

from collections import Counter
import csv
import hashlib
from io import StringIO
import json
import logging
from pathlib import Path
import re
import warnings

import numpy as np
import pandas as pd

from .states import add_state_label

_ROW_SAMPLE_LIMIT = 20


def _rows(positions):
    positions = [int(value) for value in positions]
    return {
        "count": len(positions),
        "data_rows": positions[:_ROW_SAMPLE_LIMIT],
        "sample_truncated": len(positions) > _ROW_SAMPLE_LIMIT,
    }


def _json_value(value):
    if isinstance(value, np.generic):
        return value.item()
    return str(value)


def _mode_value(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return repr(value)
    return value


class _CaptureWarnings(logging.Handler):
    def __init__(self, report):
        super().__init__(logging.WARNING)
        self.report = report

    def emit(self, record):
        self.report["warnings"].append(
            {
                "stage": self.report["stage"],
                "code": "logger_warning",
                "message": record.getMessage(),
                "level": record.levelname,
            }
        )


def _conversion_report(parser, mapping):
    conversions = []
    for raw, resolved in mapping.items():
        alias = resolved.get("matched_alias")
        factor = resolved.get("numeric_factor")
        if parser._configured_value(parser.time_units, raw, "time_units") is not None:
            basis = "explicit_time_units"
        elif (
            parser._configured_value(
                parser._HEADER_TIME_SECONDS, raw, "declared time units", True
            )
            is not None
        ):
            basis = "declared_header_unit"
        elif (
            parser._configured_value(parser.standard_units, raw, "standard_units")
            is not None
        ):
            basis = "configured_standard_units"
        elif resolved["standard_header"] == "Time [s]" and not resolved["is_elapsed"]:
            basis = "legacy_header_assumption"
            factor = 1
        else:
            basis = "intrinsic_duration_or_no_conversion"
        conversions.append(
            {
                "raw_column": raw,
                "standard_column": resolved["standard_header"],
                "matched_alias": alias,
                "numeric_factor": factor,
                "basis": basis,
                "is_elapsed": bool(resolved.get("is_elapsed")),
                "duration_strings_keep_intrinsic_units": bool(
                    resolved.get("is_elapsed")
                ),
            }
        )
    return conversions


def _cleanup_report(before, after):
    unnamed = before.columns.str.contains("^Unnamed:")
    named = before.loc[:, ~unnamed]
    empty = named.isna().all(axis=1).to_numpy()
    provenance = before.attrs.get('_pbdp_raw_rows')
    footer_rows = np.zeros(len(before), dtype=bool)
    footers = [] if provenance is None else provenance.get('declared_footers', [])
    for footer in footers:
        footer_rows[footer['position']] = True
    available = np.flatnonzero(~empty & ~footer_rows)
    prefix = max(0, len(available) - len(after))
    retained = available[prefix:]
    removed = np.ones(len(before), dtype=bool)
    removed[retained] = False
    raw_empty = (np.asarray(provenance['empty'], dtype=bool)
                 if provenance is not None else before.isna().all(axis=1).to_numpy())
    reasons = []
    for reason, indices in [
        ("wholly_empty", np.flatnonzero(removed & raw_empty)),
        ("leading_non_measurement",
         np.flatnonzero(removed & ~raw_empty & ~footer_rows)),
        ("declared_footer", np.flatnonzero(removed & footer_rows)),
    ]:
        if len(indices):
            item = {"reason": reason, **_rows(indices + 1)}
            if reason == 'declared_footer':
                item['verified_counts'] = [
                    {'data_row': footer['position'] + 1,
                     'declared_count': footer['declared_count'],
                     'preceding_parsed_records': footer['preceding_parsed_records']}
                    for footer in footers[:_ROW_SAMPLE_LIMIT]
                ]
            reasons.append(item)
    return {
        "parsed": len(before),
        "retained": len(after),
        "removed": len(before) - len(after),
        "removals": reasons,
        "removed_columns": before.columns[unnamed].tolist(),
    }, (retained + 1).tolist()


def _measurement_issues(frame, mapping, source_rows):
    if frame is None:
        return []
    eis = ["freq [Hz]", "ReZ [Ohm]", "ImZ [Ohm]"]
    voltages = [
        "Voltage [V]",
        "Working electrode potential [V]",
        "Counter electrode potential [V]",
    ]
    if any(name in frame for name in eis):
        required = eis
    else:
        required = ["Time [s]", "Current [A]"]
        required += [name for name in voltages if name in frame] or ["Voltage [V]"]
    issues = []
    for name in required:
        raw = [key for key, item in mapping.items() if item["standard_header"] == name]
        if name not in frame:
            issues.append(
                {
                    "column": name,
                    "raw_columns": raw,
                    "reason": "missing_column",
                    "count": len(frame),
                    "data_rows": [],
                }
            )
            continue
        values = pd.to_numeric(frame[name], errors="coerce")
        bad = np.flatnonzero(
            ~np.isfinite(values.to_numpy(dtype=float, na_value=np.nan))
        )
        if len(bad):
            rows = [source_rows[index] for index in bad]
            issues.append(
                {
                    "column": name,
                    "raw_columns": raw,
                    "reason": "nonfinite_required_measurement",
                    **_rows(rows),
                }
            )
    return issues


def _failure(report, exc, frame, mapping, source_rows):
    message = str(exc)
    stage = report["stage"]
    issue = {
        "stage": stage,
        "code": "import_failed_at_" + stage,
        "exception_type": type(exc).__name__,
        "message": message,
        "columns": [],
        "data_rows": [],
    }
    actions = {
        "configuration": "Provide dtype as a dictionary of raw column names to dtypes.",
        "source": "Choose one existing, nonempty measurement file.",
        "header": "Check the format or provide the 1-based header line using cycler.",
        "read": "Check delimiters, raw headers, and requested pandas dtypes.",
        "columns": "Choose unambiguous source columns and header/unit mappings.",
        "units": "Check elapsed values and declare ambiguous numeric time units.",
        "current_direction": (
            "Check the configured mode column, mode map, and current threshold."
        ),
        "cleanup": "Check the measurement schema and leading non-measurement rows.",
        "validation": "Review the listed required columns and source data rows.",
        "states": "Check required state-label columns and the current threshold.",
    }
    issue["action"] = actions.get(stage, "Review the input and import configuration.")
    issue["columns"] = [
        name for name in report.get("raw_columns", []) if repr(name.strip()) in message
    ]
    row = re.search(r"(?:at |invalid |measurement )row (\d+)", message)
    if row:
        index = int(row.group(1))
        issue["data_rows"] = [
            source_rows[index] if index < len(source_rows) else index + 1
        ]
    if "Duplicate" in message:
        issue["code"] = "duplicate_columns"
        counts = Counter(
            name.strip() for name in report.get("raw_columns", []) if name.strip()
        )
        duplicates = [name for name, count in counts.items() if count > 1]
        if not duplicates:
            targets = Counter(item["standard_header"] for item in mapping.values())
            duplicates = [
                name
                for name, item in mapping.items()
                if targets[item["standard_header"]] > 1
            ]
        issue["columns"] = duplicates or issue["columns"]
    if stage in {"validation", "cleanup"}:
        issue["measurements"] = _measurement_issues(frame, mapping, source_rows)
        issue["columns"] = [item["column"] for item in issue["measurements"]]
    if stage == "current_direction":
        issue["columns"] = [
            report["configuration"]["current_mode_column"],
            "Current [A]",
        ]
    if report.get("measurement_schema", {}).get("kind") == "mixed":
        issue["code"] = "mixed_measurement_schema"
        issue["action"] = "Select separate cycling and EIS tables before import."
    report["errors"].append(issue)
    report["status"] = "error"


def inspect_file(parser, source, cycler="", state_option="", dtype=None):
    """Inspect one file without saving; capture failures instead of raising them.

    Data-row references are 1-based parsed records after the header, including
    leading units rows. They are not physical line numbers for multiline CSV.
    Offending row lists are bounded samples with complete counts. Source paths,
    metadata, and diagnostics can be sensitive; the caller controls persistence.
    """
    report = {
        "schema_version": 1,
        "status": "error",
        "stage": "source",
        "source": {},
        "header": {},
        "metadata": {},
        "raw_columns": [],
        "columns": [],
        "rows": {"parsed": None, "retained": None, "removed": None, "removals": []},
        "row_numbering": (
            "1-based parsed data records; blank lines skipped by pandas are not records"
        ),
        "configuration": {
            "cycler": cycler,
            "state_option": state_option,
            "dtype": (
                {str(key): str(value) for key, value in dtype.items()}
                if isinstance(dtype, dict) else {} if dtype is None else str(dtype)
            ),
            "time_units": dict(parser.time_units),
            "current_epsilon": parser.current_epsilon,
            "current_mode_column": parser.current_mode_column,
            "current_mode_map": (
                None
                if parser.current_mode_map is None
                else [
                    {
                        "source_value": _mode_value(key),
                        "source_type": type(key).__name__,
                        "state": value,
                    }
                    for key, value in parser.current_mode_map.items()
                ]
            ),
        },
        "warnings": [],
        "errors": [],
    }
    frame, mapping, source_rows = None, {}, []
    capture = _CaptureWarnings(report)
    parser.logger.addHandler(capture)
    try:
        with warnings.catch_warnings(record=True) as emitted:
            warnings.simplefilter("always")
            try:
                report["stage"] = "configuration"
                if dtype is not None and not isinstance(dtype, dict):
                    raise ValueError("dtype must be a dictionary of raw column dtypes")
                report["stage"] = "source"
                path = Path(source)
                report["source"] = {"path": str(path), "name": path.name}
                if not path.is_file():
                    raise ValueError("Inspection requires a single existing file")
                raw = path.read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                report["source"].update(
                    {"sha256": digest, "id": "sha256:" + digest, "bytes": len(raw)}
                )
                if not raw:
                    raise ValueError("Cannot inspect an empty input file")
                table = parser._table_bytes(path, raw)
                report["stage"] = "header"
                pointer, encoding, vendor = parser._find_words_bytes(
                    path, table, cycler
                )
                header_pointer = pointer
                blank_prefix = 0
                for line in table[pointer:].splitlines(keepends=True):
                    if line.strip():
                        break
                    header_pointer += len(line)
                    blank_prefix += 1
                report["header"] = {
                    "line": table[:header_pointer].count(b"\n") + 1,
                    "byte_offset": header_pointer,
                    "blank_prefix_lines_skipped": blank_prefix,
                    "encoding": encoding,
                    "detected_vendor": vendor,
                    "coordinate_space": (
                        "active_sheet_csv"
                        if path.suffix.lower() == ".xlsx"
                        else "source_text"
                    ),
                }
                metadata, data = parser._split_file_bytes(pointer, path, "none", table)
                text = metadata.decode(encoding)
                report["metadata"] = {
                    "bytes": len(metadata),
                    "line_count": len(text.splitlines()),
                    "text": text,
                    "absolute_time_available": False,
                }
                delimiter = "," if path.suffix.lower() in {".csv", ".xlsx"} else "\t"
                reader = csv.reader(
                    StringIO(data.decode(encoding)), delimiter=delimiter
                )
                report["raw_columns"] = next((row for row in reader if row), [])
                report["stage"] = "read"
                frame = parser.read_data_to_pandas(data, path, encoding, dtype=dtype)
                report["rows"]["parsed"] = len(frame)
                source_rows = list(range(1, len(frame) + 1))
                report["stage"] = "columns"
                try:
                    mapping = parser.resolve_columns(frame.columns)
                except ValueError:
                    # Keep successful individual resolutions for collision context.
                    for column in frame.columns:
                        try:
                            mapping.update(parser.resolve_columns([column]))
                        except ValueError:
                            pass
                    raise
                report["columns"] = _conversion_report(parser, mapping)
                report["stage"] = "units"
                frame = parser.change_units(frame)
                report["stage"] = "columns"
                frame = parser.change_headers(frame)
                report["stage"] = "cleanup"
                schema = parser.inspect_measurement_schema(frame)
                report["measurement_schema"] = {
                    "kind": schema["kind"],
                    "cycling_only_rows": _rows(
                        [source_rows[index] for index in schema["cycling_only_rows"]]
                    ),
                }
                cleaned = parser.remove_unwanted(frame)
                report["rows"], source_rows = _cleanup_report(frame, cleaned)
                frame = cleaned
                report["stage"] = "current_direction"
                previous_current = frame.get("Current [A]")
                frame = parser.apply_current_direction(frame)
                if parser.current_mode_column is not None:
                    changed = np.flatnonzero(
                        frame["Current [A]"].ne(previous_current).to_numpy()
                    )
                    report["current_normalization"] = {
                        "basis": "caller_declared_mode_mapping",
                        "source_current_retained": "Source current [A]" in frame,
                        "changed_rows": _rows(
                            [source_rows[index] for index in changed]
                        ),
                    }
                report["stage"] = "validation"
                parser.sanity_check(frame)
                if "Time [s]" in frame:
                    report["stage"] = "absolute_time"
                    try:
                        frame = parser.absolute_time(metadata, frame, encoding)
                        report["metadata"]["absolute_time_available"] = (
                            "Absolute Time [s]" in frame
                        )
                    except ValueError as exc:
                        parser.logger.warning(
                            "Absolute time unavailable for %s: %s", path, exc
                        )
                if state_option == "yes":
                    report["stage"] = "states"
                    frame = add_state_label(
                        frame, parser.current_epsilon, parser.logger.name
                    )
                    report["state_counts"] = (
                        frame["Battery State"].value_counts().to_dict()
                    )
                report["dtypes"] = {
                    name: str(value) for name, value in frame.dtypes.items()
                }
                report["status"], report["stage"] = "ok", "complete"
            except Exception as exc:
                _failure(report, exc, frame, mapping, source_rows)
            for warning in emitted:
                report["warnings"].append(
                    {
                        "code": "python_warning",
                        "message": str(warning.message),
                        "category": warning.category.__name__,
                    }
                )
    finally:
        parser.logger.removeHandler(capture)
    return json.loads(json.dumps(report, default=_json_value, allow_nan=False))
