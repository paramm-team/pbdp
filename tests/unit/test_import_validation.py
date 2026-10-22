"""Regression tests for silent truncation and invalid measurement handling."""
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from pbdp import Parser
from pbdp.save import save_file


@pytest.fixture
def measurements():
    return pd.DataFrame({
        'Time [s]': [0, 1, 2], 'Current [A]': [1, 1, 0],
        'Voltage [V]': [3.5, 3.6, 3.6], 'Step Number': [1, 2, 20],
        'Temperature [degC]': [20, None, 21],
    })


def test_cleanup_preserves_step_jumps_and_optional_missing_values(measurements):
    result = Parser().remove_unwanted(measurements)
    assert_frame_equal(result, measurements)


@pytest.mark.parametrize('field', ['Time [s]', 'Current [A]', 'Voltage [V]'])
@pytest.mark.parametrize('value', [None, float('inf'), float('-inf')])
def test_invalid_required_measurements_are_rejected(measurements, field, value):
    measurements[field] = measurements[field].astype(float)
    measurements.loc[1, field] = value
    with pytest.raises(ValueError, match='finite'):
        Parser().sanity_check(measurements)


def test_empty_measurements_are_rejected(measurements):
    with pytest.raises(ValueError, match='empty'):
        Parser().sanity_check(measurements.iloc[:0])


def test_sanity_check_uses_signed_electrode_potential_difference():
    data = pd.DataFrame({
        'Time [s]': [0], 'Current [A]': [1], 'Voltage [V]': [3.8],
        'Working electrode potential [V]': [3.7],
        'Counter electrode potential [V]': [-0.1],
    })
    assert Parser().sanity_check(data) == 0


def test_invalid_import_is_not_saved_even_without_start_time(tmp_path):
    path = tmp_path / 'missing_voltage.csv'
    path.write_text('time/s,I/mA\n0,1000\n', encoding='utf-8')
    with pytest.raises(ValueError, match='missing'):
        Parser().data_importer(path, save_option='save')
    assert not (tmp_path / 'processed').exists()


def test_missing_header_has_clear_error(tmp_path):
    path = tmp_path / 'unknown.csv'
    path.write_text('unrecognized,header\n1,2', encoding='utf-8')
    with pytest.raises(ValueError, match='header'):
        Parser().data_importer(path, save_option='none')


def test_duplicate_mapped_headers_are_rejected():
    data = pd.DataFrame({'Current': [1], 'Current (A)': [2]})
    with pytest.raises(ValueError, match='Duplicate'):
        Parser().change_headers(data)


def test_prefix_whitespace_does_not_skip_unit_conversion():
    data = pd.DataFrame({' <I>/mA ': [1000]})
    parser = Parser()
    result = parser.change_headers(parser.change_units(data))
    assert result['Current [A]'].tolist() == [1]


@pytest.mark.parametrize('extension', ['csv', 'parquet', 'pickle', 'feather'])
def test_export_roundtrip_and_dotted_filename(tmp_path, extension):
    data = pd.DataFrame({'Current [A]': [1.0, -0.5],
                         'Battery State': ['charging', 'discharging']})
    path = save_file(data, extension, tmp_path / 'cell.run1.csv')
    assert path.name == f'cell.run1_cleaned_data.{extension}'
    reader = getattr(pd, 'read_' + extension)
    assert_frame_equal(reader(path), data)


def test_unsupported_export_creates_no_output(tmp_path):
    with pytest.raises(ValueError, match='Unsupported'):
        save_file(pd.DataFrame({'x': [1]}), 'unknown', tmp_path / 'sample.csv')
    assert not (tmp_path / 'processed').exists()


@pytest.mark.parametrize('header', [
    'time/s,Current,Current,Ecell/V',
    'time/s,Current, Current ,Ecell/V',
    'time/s,"Current","Current",Ecell/V',
])
def test_duplicate_raw_headers_fail_before_pandas_mangles_names(tmp_path, header):
    path = tmp_path / 'duplicate.csv'
    path.write_text(header + '\n0,1,2,3.5\n', encoding='utf-8')
    with pytest.raises(ValueError, match='Duplicate raw'):
        Parser().data_importer(path, save_option='save')
    assert not (tmp_path / 'processed').exists()


def test_leading_empty_header_field_is_preserved(tmp_path):
    path = tmp_path / 'leading_comma.csv'
    path.write_text(',time/s,I/mA,Ecell/V\n,0,1000,3.5\n,10,500,4.2\n',
                    encoding='utf-8')
    result = Parser().data_importer(path, save_option='none')
    assert result['Time [s]'].tolist() == [0, 10]
    assert result['Current [A]'].tolist() == pytest.approx([1, .5])
    assert result['Voltage [V]'].tolist() == pytest.approx([3.5, 4.2])


def test_repeated_unnamed_header_fields_are_allowed(tmp_path):
    path = tmp_path / 'unnamed.csv'
    path.write_text(',,time/s,I/mA,Ecell/V\n,,0,1000,3.5\n', encoding='utf-8')
    result = Parser().data_importer(path, save_option='none')
    assert result['Current [A]'].tolist() == [1]
