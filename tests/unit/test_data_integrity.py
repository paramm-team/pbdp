"""Expected-value regressions using synthetic, non-confidential measurements."""
from pathlib import Path

import openpyxl
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from pbdp import Parser
from pbdp.save import save_file
from pbdp.segment import segment_data
from pbdp.states import find_cc_and_cv


@pytest.mark.parametrize('column,values,expected', [
    ('<I>/mA', [1000, -500, 0], [1, -0.5, 0]),
    ('I/mA', [1000, -500, 0], [1, -0.5, 0]),
    ('(Q-Qo)/mA.h', [1000, 500, 0], [1, 0.5, 0]),
    ('Charge (C)', [3600, 1800, 0], [1, 0.5, 0]),
])
def test_units_preserve_physical_quantities(column, values, expected):
    result = Parser().change_units(pd.DataFrame({column: values}))
    assert result[column].tolist() == pytest.approx(expected)


def test_units_row_and_numeric_strings():
    data = pd.DataFrame({'<I>/mA': ['mA', '1000', '-500']})
    result = Parser().change_units(data)
    assert pd.isna(result.iloc[0, 0])
    assert result.iloc[1:, 0].tolist() == pytest.approx([1, -0.5])


def test_elapsed_seconds_are_not_accumulated_again():
    data = pd.DataFrame({'Time [s]': [0, 10, 20.5]}, index=[2, 4, 6])
    result = Parser().absolute_time(
        b'Technique started on : 21/10/2026 09:00:00', data, 'utf-8'
    )
    expected = pd.to_datetime([
        '2026-10-21 09:00:00', '2026-10-21 09:00:10',
        '2026-10-21 09:00:20.500',
    ], format='mixed')
    assert result['Absolute Time [s]'].tolist() == expected.tolist()
    assert result.index.tolist() == [2, 4, 6]


@pytest.mark.parametrize('extension,delimiter', [
    ('.csv', ','), ('.xlsx', ','), ('.txt', '\t'), ('.mpt', '\t'),
    ('.DTA', '\t'),
])
def test_byte_reader_preserves_existing_files(tmp_path, extension, delimiter):
    sentinel = tmp_path / 'new_file_name'
    sentinel.write_bytes(b'keep this file')
    payload = f'time/s{delimiter}<I>/mA\n0{delimiter}1000\n'.encode()
    result = Parser().read_data_to_pandas(
        payload, tmp_path / ('sample' + extension), 'utf-8'
    )
    assert result.to_dict('list') == {'time/s': [0], '<I>/mA': [1000]}
    assert sentinel.read_bytes() == b'keep this file'
    assert list(tmp_path.iterdir()) == [sentinel]


def test_reader_failure_preserves_existing_files(tmp_path):
    sentinel = tmp_path / 'new_file_name'
    sentinel.write_bytes(b'keep this file')
    with pytest.raises(ValueError, match='Invalid file format'):
        Parser().read_data_to_pandas(b'a,b\n1,2', tmp_path / 'bad.bin', 'utf-8')
    assert sentinel.read_bytes() == b'keep this file'
    assert list(tmp_path.iterdir()) == [sentinel]


@pytest.fixture
def workbook(tmp_path):
    path = tmp_path / 'sample.xlsx'
    book = openpyxl.Workbook()
    book.active.append(['time/s', '<I>/mA', 'Ecell/V'])
    book.active.append([0, 1000, 3.5])
    book.active.append([10, 500, 4.2])
    book.save(path)
    book.close()
    return path


def test_excel_import_does_not_create_or_delete_temporary_neighbors(workbook):
    sentinel = workbook.parent / 'converted_temporary.csv'
    sentinel.write_bytes(b'keep this file')
    before = {p.name: p.read_bytes() for p in workbook.parent.iterdir()}
    parser = Parser()
    result = parser.data_importer(workbook, save_option='none')
    assert result['Current [A]'].tolist() == pytest.approx([1, 0.5])
    assert result['Time [s]'].tolist() == [0, 10]
    assert {p.name: p.read_bytes() for p in workbook.parent.iterdir()} == before


def test_excel_conversion_uses_distinct_paths(workbook):
    parser = Parser()
    first = parser.convert_xlsx_to_csv(workbook)
    second = parser.convert_xlsx_to_csv(workbook)
    try:
        assert first != second
        assert first.read_bytes() == second.read_bytes()
        assert pd.read_csv(first)['<I>/mA'].tolist() == [1000, 500]
    finally:
        first.unlink(missing_ok=True)
        second.unlink(missing_ok=True)


def test_legitimate_temporary_named_input_survives(tmp_path):
    source = tmp_path / 'converted_temporary.csv'
    source.write_bytes(b'a,b\n1,2')
    assert Parser().split_file(0, source, 'none')[1] == b'a,b\n1,2'
    assert source.read_bytes() == b'a,b\n1,2'


@pytest.fixture
def charging_cycle():
    return pd.DataFrame({
        'Time [s]': [0, 10, 20, 30, 40],
        'Current [A]': [0, 1, 1, 0.5, 0.2],
        'Voltage [V]': [3.5, 3.6, 4.0, 4.2, 4.2],
        'Battery State': ['rest'] + ['charging'] * 4,
        'CCCV': ['N/A', 'CC', 'CC', 'CV', 'CV'],
    })


@pytest.mark.parametrize('query', ['cccv', 'cccv 1A 4.2V', 'cccv 4.2V'])
def test_cccv_includes_both_phases_at_end_of_recording(charging_cycle, query):
    result = segment_data(charging_cycle, [query])
    assert len(result) == 1
    assert_frame_equal(result[0], charging_cycle.iloc[1:])


@pytest.mark.parametrize('query', ['cccv 2A 4.2V', 'cccv 1A 4.1V'])
def test_cccv_respects_current_and_voltage(charging_cycle, query):
    assert segment_data(charging_cycle, [query]) == []


def test_cc_and_cv_remain_separate(charging_cycle):
    assert_frame_equal(segment_data(charging_cycle, ['cc'])[0],
                       charging_cycle.iloc[1:3])
    assert_frame_equal(segment_data(charging_cycle, ['cv'])[0],
                       charging_cycle.iloc[3:])


def test_whole_time_request_returns_a_dataframe(charging_cycle):
    result = segment_data(charging_cycle, ['time'], reset=True)
    assert len(result) == 1
    assert result[0]['Time [s]'].tolist() == charging_cycle['Time [s]'].tolist()


@pytest.mark.parametrize('index', [range(4), [100, 105, 110, 115]])
def test_cc_interval_at_start_of_recording(index):
    data = pd.DataFrame({
        'Time [s]': [0, 5, 10, 15], 'Current [A]': [1.0] * 4,
        'Voltage [V]': [3.5, 3.6, 3.7, 3.8],
    }, index=index)
    result = find_cc_and_cv(data)
    assert result['CCCV'].tolist() == ['CC'] * 4


def test_parquet_roundtrip_preserves_labels_and_types(tmp_path):
    data = pd.DataFrame({
        'Time [s]': [0.0, 1.5, 3.0],
        'Current [A]': [0.0, 1.0, -1.0],
        'Battery State': ['rest', 'charging', 'discharging'],
        'CCCV': ['N/A', 'CC', 'CV'],
        'Optional': pd.Series([1, None, 3], dtype='Int64'),
    })
    original = data.copy(deep=True)
    result = save_file(data, 'parquet', Path(tmp_path / 'sample.csv'))
    assert_frame_equal(pd.read_parquet(result), original)
    assert_frame_equal(data, original)
