"""Expected-value import diagnostics use invented sources, never private data."""

import hashlib
import json
import logging

import numpy as np
import openpyxl
import pytest

from pbdp import Parser


@pytest.mark.parametrize('dtype', ['string', ['Current [A]'], 7])
def test_invalid_dtype_configuration_returns_an_error_report(tmp_path, dtype):
    source = tmp_path / 'measurements.csv'
    source.write_text('time/s,Current [A],Voltage [V]\n0,1,3.5\n10,1,3.6\n')
    original = source.read_bytes()
    report = Parser().inspect_file(source, dtype=dtype)
    assert report['status'] == 'error'
    assert report['stage'] == 'configuration'
    assert report['errors'][0]['exception_type'] == 'ValueError'
    assert 'dtype' in report['errors'][0]['message']
    assert 'dictionary' in report['errors'][0]['action']
    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert source.read_bytes() == original
    assert list(tmp_path.iterdir()) == [source]


def source_file(tmp_path, text, name="example.csv"):
    path = tmp_path / name
    # Preserve the chosen fixture bytes on every operating system.
    path.write_bytes(text.encode("utf-8"))
    return path


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_inspection_accounts_for_cleanup_and_keeps_source_unchanged(tmp_path, newline):
    source = source_file(
        tmp_path,
        ("Synthetic export\ntime/s,I/mA,Ecell/V,Cell ID\n"
         "s,mA,V,units\n0,1000,3.7,0007\n,,,\n10,-500,3.6,0042\n")
        .replace("\n", newline),
    )
    original = source.read_bytes()
    report = Parser().inspect_file(source, state_option="yes", dtype={"Cell ID": str})

    assert report["status"] == "ok", report["errors"]
    assert report["source"]["sha256"] == hashlib.sha256(original).hexdigest()
    assert report["source"]["bytes"] == len(original)
    assert report["header"]["line"] == 2
    assert report["header"]["detected_vendor"] == "vmp3"
    assert report["metadata"]["text"] == "Synthetic export" + newline
    assert report["metadata"]["absolute_time_available"] is False
    assert report["rows"]["parsed"] == 4
    assert report["rows"]["retained"] == 2
    assert report["rows"]["removed"] == 2
    removals = {
        item["reason"]: item["data_rows"] for item in report["rows"]["removals"]
    }
    assert removals == {"wholly_empty": [3], "leading_non_measurement": [1]}
    assert report["state_counts"] == {"charging": 1, "discharging": 1}
    columns = {item["raw_column"]: item for item in report["columns"]}
    assert columns["I/mA"]["numeric_factor"] == 0.001
    assert columns["I/mA"]["standard_column"] == "Current [A]"
    assert columns["time/s"]["basis"] == "declared_header_unit"
    assert report["warnings"]
    assert any(
        "Absolute time unavailable" in item["message"] for item in report["warnings"]
    )
    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert source.read_bytes() == original
    assert list(tmp_path.iterdir()) == [source]


def test_inspection_distinguishes_units_coerced_to_empty_from_raw_empty(tmp_path):
    source = source_file(
        tmp_path, "time/s,I/mA,Ecell/V\ns,mA,V\n0,1000,3.7\n,,\n10,500,3.6\n"
    )
    report = Parser().inspect_file(source)
    assert report['status'] == 'ok', report['errors']
    reasons = {item['reason']: item['data_rows'] for item in report['rows']['removals']}
    assert reasons == {'wholly_empty': [3], 'leading_non_measurement': [1]}
    assert report['rows']['parsed'] == 4
    assert report['rows']['retained'] == 2
    assert report['rows']['removed'] == 2


def test_inspection_retains_original_row_number_for_all_invalid_measurements(tmp_path):
    source = source_file(
        tmp_path, 'Total Time,Current,Voltage\ns,A,V\n0,1,3.5\n,,\n'
        'invalid,invalid,invalid\n2,1,3.6\n'
    )
    report = Parser().inspect_file(source)
    assert report['status'] == 'error'
    assert report['stage'] == 'cleanup'
    assert report['errors'][0]['data_rows'] == [4]
    assert 'Invalid nonempty' in report['errors'][0]['message']
    assert report['rows']['parsed'] == 5
    assert list(tmp_path.iterdir()) == [source]


def test_inspection_records_verified_footer_and_original_measurement_rows(tmp_path):
    source = source_file(
        tmp_path, 'Total Time,Current,Voltage\ns,A,V\n0,1,3.5\n,,\n1,1,3.6\n'
        'Total Number of Data Lines in the Database: 4\n'
    )
    report = Parser().inspect_file(source)
    assert report['status'] == 'ok', report['errors']
    assert report['rows']['parsed'] == 5
    assert report['rows']['retained'] == 2
    reasons = {item['reason']: item for item in report['rows']['removals']}
    assert reasons['wholly_empty']['data_rows'] == [3]
    assert reasons['leading_non_measurement']['data_rows'] == [1]
    assert reasons['declared_footer']['data_rows'] == [5]
    assert reasons['declared_footer']['verified_counts'] == [
        {'data_row': 5, 'declared_count': 4, 'preceding_parsed_records': 4}]
    json.dumps(report, allow_nan=False)


def test_inspection_reports_invalid_required_column_and_original_row(tmp_path):
    source = source_file(
        tmp_path, "time/s,I/mA,Ecell/V\ns,mA,V\n0,1000,3.7\n10,bad,3.6\n"
    )
    report = Parser().inspect_file(source)

    assert report["status"] == "error"
    assert report["stage"] == "validation"
    error = report["errors"][0]
    assert error["columns"] == ["Current [A]"]
    assert error["measurements"] == [
        {
            "column": "Current [A]",
            "raw_columns": ["I/mA"],
            "reason": "nonfinite_required_measurement",
            "count": 1,
            "data_rows": [3],
            "sample_truncated": False,
        }
    ]
    with pytest.raises(ValueError, match="finite"):
        Parser().data_importer(source, save_option="none")
    assert list(tmp_path.iterdir()) == [source]


def test_inspection_reports_invalid_elapsed_row_before_cleanup(tmp_path):
    source = source_file(tmp_path, "time/s,I/mA,Ecell/V\n0,1000,3.7\ninvalid,500,3.6\n")
    report = Parser().inspect_file(source)
    assert report["status"] == "error"
    assert report["stage"] == "units"
    assert report["errors"][0]["columns"] == ["time/s"]
    assert report["errors"][0]["data_rows"] == [2]


def test_nullable_measurement_diagnostics_remain_json_serializable(tmp_path):
    source = source_file(tmp_path, "time/s,I/mA,Ecell/V\n0,1000,3.7\n10,,3.6\n")
    report = Parser().inspect_file(source, dtype={"I/mA": "string"})
    assert report["status"] == "error"
    assert report["errors"][0]["measurements"][0]["data_rows"] == [2]
    json.dumps(report, allow_nan=False)


def test_inspection_time_configuration_is_explicit_and_reusable(tmp_path):
    source = source_file(tmp_path, "TestTime,Current,Voltage\n0,1,3.7\n2.5,0,3.6\n")
    rejected = Parser().inspect_file(source)
    assert rejected["status"] == "error"
    assert "time_units" in rejected["errors"][0]["message"]

    report = Parser(time_units={"TestTime": "min"}).inspect_file(source)
    assert report["status"] == "ok", report["errors"]
    elapsed = next(
        item for item in report["columns"] if item["raw_column"] == "TestTime"
    )
    assert elapsed["numeric_factor"] == 60
    assert elapsed["basis"] == "explicit_time_units"
    assert elapsed["duration_strings_keep_intrinsic_units"]
    assert report["configuration"]["time_units"] == {"TestTime": "min"}


def test_inspection_records_alias_configuration_and_legacy_unit_assumptions(tmp_path):
    source = source_file(tmp_path, " testTime ,Current,Voltage\n0,1,3.7\n2.5,0,3.6\n")
    report = Parser(time_units={"TESTTIME": "min"}).inspect_file(source)
    assert report["status"] == "ok", report["errors"]
    assert report["columns"][0]["basis"] == "explicit_time_units"
    assert report["columns"][0]["numeric_factor"] == 60

    source.write_text("Total Time,Current,Voltage\n0,1,3.7\n", encoding="utf-8")
    report = Parser().inspect_file(source)
    assert report["status"] == "ok", report["errors"]
    assert report["columns"][0]["basis"] == "legacy_header_assumption"
    assert report["columns"][0]["numeric_factor"] == 1


def test_inspection_records_current_convention_and_actual_states(tmp_path):
    source = source_file(
        tmp_path, "time/s,I/mA,Ecell/V,Mode\n0,2000,3.7,D\n10,1,3.6,R\n"
    )
    parser = Parser(
        current_mode_column="Mode",
        current_mode_map={
            "D": "discharging",
            "R": "rest",
        },
    )
    report = parser.inspect_file(source, state_option="yes")
    assert report["status"] == "ok", report["errors"]
    assert report["state_counts"] == {"discharging": 1, "rest": 1}
    assert report["configuration"]["current_mode_column"] == "Mode"
    assert report["configuration"]["current_epsilon"] == 0.001
    assert "Source current [A]" in report["dtypes"]
    assert report["current_normalization"]["changed_rows"]["data_rows"] == [1]
    assert report["current_normalization"]["source_current_retained"]


def test_inspection_reports_current_mode_conflict(tmp_path):
    source = source_file(tmp_path, "time/s,I/mA,Ecell/V,Mode\n0,2000,3.7,R\n")
    parser = Parser(current_mode_column="Mode", current_mode_map={"R": "rest"})
    report = parser.inspect_file(source)
    assert report["status"] == "error"
    assert report["stage"] == "current_direction"
    assert report["errors"][0]["columns"] == ["Mode", "Current [A]"]
    assert report["errors"][0]["data_rows"] == [1]


def test_numeric_mode_configuration_is_json_safe_without_changing_key_type(tmp_path):
    source = source_file(tmp_path, "time/s,I/mA,Ecell/V,Mode\n0,1000,3.7,2\n")
    report = Parser(
        current_mode_column="Mode", current_mode_map={np.int64(2): "discharging"}
    ).inspect_file(source, state_option="yes")
    assert report["status"] == "ok", report["errors"]
    assert report["configuration"]["current_mode_map"] == [
        {"source_value": 2, "source_type": "int64", "state": "discharging"}
    ]
    assert json.loads(json.dumps(report)) == report


def test_unmatched_nonfinite_mode_key_does_not_break_error_report(tmp_path):
    source = source_file(tmp_path, "time/s,I/mA,Ecell/V,Mode\n0,1000,3.7,2\n")
    report = Parser(
        current_mode_column="Mode", current_mode_map={float("nan"): "rest"}
    ).inspect_file(source)
    assert report["status"] == "error"
    assert report["errors"][0]["stage"] == "current_direction"
    json.dumps(report, allow_nan=False)


def test_inspection_missing_time_reports_validation_not_schema_failure(tmp_path):
    source = source_file(tmp_path, "I/mA,Ewe/V,Ece/V\n1000,3.7,-0.1\n")
    report = Parser().inspect_file(source, cycler="1")
    assert report["status"] == "error"
    assert report["stage"] == "validation"
    assert report["errors"][0]["measurements"][0]["column"] == "Time [s]"
    assert report["errors"][0]["measurements"][0]["reason"] == "missing_column"


def test_inspection_mixed_schema_fails_with_cycling_rows_identified(tmp_path):
    source = source_file(
        tmp_path,
        "time/s,I/mA,Ecell/V,freq/Hz,ReZ [Ohm],ImZ [Ohm]\n"
        "0,1,3.7,1000,0.1,-0.2\n10,2,3.6,,,\n",
    )
    report = Parser().inspect_file(source)
    assert report["status"] == "error"
    assert report["measurement_schema"]["kind"] == "mixed"
    assert report["measurement_schema"]["cycling_only_rows"]["data_rows"] == [2]
    assert "Mixed cycling/EIS" in report["errors"][0]["message"]
    assert list(tmp_path.iterdir()) == [source]


def test_inspection_reports_duplicate_source_headers(tmp_path):
    source = source_file(tmp_path, "time/s,Current,Current,Ecell/V\n0,1,2,3.7\n")
    report = Parser().inspect_file(source)
    assert report["status"] == "error"
    assert report["errors"][0]["columns"] == ["Current"]
    assert "Duplicate raw" in report["errors"][0]["message"]


def test_inspection_reports_both_colliding_measurement_aliases(tmp_path):
    source = source_file(tmp_path, "time/s,Current,Current (A),Ecell/V\n0,1,2,3.7\n")
    report = Parser().inspect_file(source)
    assert report["status"] == "error"
    assert report["errors"][0]["columns"] == ["Current", "Current (A)"]
    assert report["errors"][0]["code"] == "duplicate_columns"


@pytest.mark.parametrize("text", ["", "unknown,fields\n1,2\n"])
def test_inspection_captures_source_and_header_failures(tmp_path, text):
    source = source_file(tmp_path, text)
    report = Parser().inspect_file(source)
    assert report["status"] == "error"
    assert report["source"]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert report["errors"][0]["action"]
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_explicit_header_reports_actual_line_after_blank_prefix(tmp_path, newline):
    source = source_file(
        tmp_path, "\n\ntime/s,I/mA,Ecell/V\n0,1000,3.7\n".replace("\n", newline))
    report = Parser().inspect_file(source, cycler="1")
    assert report["status"] == "ok", report["errors"]
    assert report["header"]["line"] == 3
    assert report["header"]["byte_offset"] == len((newline * 2).encode("utf-8"))
    assert report["header"]["blank_prefix_lines_skipped"] == 2


def test_inspection_of_excel_is_in_memory_and_reads_source_once(tmp_path, monkeypatch):
    source = tmp_path / "table.xlsx"
    workbook = openpyxl.Workbook()
    workbook.active.append(["Synthetic export"])
    workbook.active.append(["time/s", "I/mA", "Ecell/V"])
    workbook.active.append([0, 1000, 3.7])
    workbook.save(source)
    workbook.close()
    original = source.read_bytes()
    reads = []
    from pathlib import Path

    read_bytes = Path.read_bytes

    def counted_read(path):
        reads.append(path)
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", counted_read)
    report = Parser().inspect_file(source)
    assert report["status"] == "ok", report["errors"]
    assert reads == [source]
    assert report["header"]["line"] == 2
    assert report["header"]["coordinate_space"] == "active_sheet_csv"
    assert report["source"]["sha256"] == hashlib.sha256(original).hexdigest()
    assert list(tmp_path.iterdir()) == [source]


def test_inspection_bounds_diagnostics_and_removes_its_logging_handler(tmp_path):
    source = source_file(
        tmp_path,
        "time/s,I/mA,Ecell/V\n" + "".join(f"{index},bad,3.7\n" for index in range(40)),
    )
    logger = logging.getLogger("inspection-test")
    handlers = list(logger.handlers)
    parser = Parser(logger_name=logger.name)
    for _ in range(2):
        report = parser.inspect_file(source)
        issue = report["errors"][0]["measurements"][0]
        assert issue["count"] == 40
        assert issue["data_rows"] == list(range(1, 21))
        assert issue["sample_truncated"]
        assert logger.handlers == handlers
