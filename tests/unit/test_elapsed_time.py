"""Elapsed-time regressions using invented measurements, never archive data."""
import csv

import numpy as np
import pandas as pd
import pytest

from pbdp import Parser
from pbdp.segment import segment_data


@pytest.mark.parametrize('values', [
    [0, 13, 93785],
    [0.0, 12.75, 93784.625],
    [0, 12.75, 93784.625],
    ['0', '12.75', '93784.625'],
    ['0', ' 12.75 ', '9.3784625e4'],
])
def test_declared_numeric_seconds_are_preserved(values):
    data = pd.DataFrame({'TestTime': values}, index=[2, 2, 8])
    result = Parser(time_units={'TestTime': 's'}).change_units(data)
    assert result['TestTime'].tolist() == pytest.approx([float(v) for v in values])
    assert result.index.tolist() == [2, 2, 8]


@pytest.mark.parametrize('column', ['TestTime', 'Total Time, (h:m:s)'])
@pytest.mark.parametrize('values', [
    ['00:00:00', '00:00:12.75', '26:03:04.625'],
    ['00:00:00', '00:00:12.75', '1 days 02:03:04.625'],
    [0, '00:00:12.75', 93784.625],
    ['0', 12.75, '26:03:04.625'],
])
def test_duration_and_numeric_elapsed_values_can_be_mixed(column, values):
    parser = Parser(time_units={column: 's'})
    result = parser.change_units(pd.DataFrame({column: values}, index=[3, 3, 9]))
    assert result[column].tolist() == pytest.approx([0, 12.75, 93784.625])
    assert result.index.tolist() == [3, 3, 9]


def test_existing_timedelta_values_remain_durations():
    values = pd.to_timedelta([0, 12.75, 93784.625], unit='s')
    result = Parser().change_units(pd.DataFrame({'TestTime': values}))
    assert result['TestTime'].tolist() == pytest.approx([0, 12.75, 93784.625])


@pytest.mark.parametrize('column', ['TestTime', 'Total Time, (h:m:s)'])
@pytest.mark.parametrize('values', [
    [0, 2.5], ['0', '2.5'], [0], ['00:00:00', 2.5],
])
def test_ambiguous_numeric_elapsed_time_requires_a_unit(column, values):
    with pytest.raises(ValueError, match='time_units'):
        Parser().change_units(pd.DataFrame({column: values}))


@pytest.mark.parametrize('column', ['TestTime', 'Total Time, (h:m:s)'])
def test_duration_strings_need_no_numeric_unit(column):
    values = ['00:00:00', '00:00:12.75', '1 days 02:03:04.625']
    result = Parser().change_units(pd.DataFrame({column: values}))
    assert result[column].tolist() == pytest.approx([0, 12.75, 93784.625])


@pytest.mark.parametrize('unit,factor', [
    ('s', 1), ('min', 60), ('h', 3600), ('ms', .001),
    ('us', .000001), ('ns', .000000001), ('d', 86400),
])
def test_declared_numeric_units_convert_to_seconds(unit, factor):
    values = ['0', 2.5, '00:00:08.5']
    parser = Parser(time_units={'TestTime': unit})
    result = parser.change_units(pd.DataFrame({'TestTime': values}))
    assert result['TestTime'].tolist() == pytest.approx([0, 2.5 * factor, 8.5])


@pytest.mark.parametrize('column', ['TestTime(s)', 'time/s', 'Time [s]'])
def test_explicit_second_headers_keep_their_units(column):
    result = Parser().change_units(pd.DataFrame({column: ['0', '2.5']}))
    assert result[column].tolist() == [0, 2.5]


@pytest.mark.parametrize('config', [
    [], 'min', {'TestTime': 'm'}, {'TestTime': 60}, {'TestTime': None},
    {'TestTime': 'seconds'}, {'': 's'}, {3: 's'}, {'Current': 's'},
    {'TestTime': 's', ' TestTime ': 'min'},
])
def test_invalid_time_unit_configuration_fails_early(config):
    with pytest.raises(ValueError, match='time_units'):
        Parser(time_units=config)


@pytest.mark.parametrize('config', [
    {'time_units': {'TestTime(s)': 'min'}},
    {'time_units': {'Run Time (h)': 's'}},
    {'standard_units': {'TestTime(s)': 60}},
    {'standard_units': {'Run Time (h)': 1}},
    {'time_units': {'TestTime': 's'}, 'standard_units': {'TestTime': 60}},
])
def test_conflicting_elapsed_time_units_fail_early(config):
    with pytest.raises(ValueError, match='Conflicting'):
        Parser(**config)


@pytest.mark.parametrize('factor', [
    0, -1, float('nan'), float('inf'), '60', True, np.complex128(1 + 0j),
])
def test_invalid_standard_time_factor_is_rejected(factor):
    with pytest.raises(ValueError, match='standard_units'):
        Parser(standard_units={'TestTime': factor})


@pytest.mark.parametrize('units', [None, {'TestTime': 'min'}])
def test_existing_explicit_factor_remains_supported(units):
    parser = Parser(standard_units={'TestTime': 60}, time_units=units)
    result = parser.change_units(pd.DataFrame({'TestTime': [0, 2.5, '00:00:08']}))
    assert result['TestTime'].tolist() == [0, 150, 8]


def test_custom_elapsed_column_accepts_explicit_units():
    parser = Parser(standard_time=['Elapsed'], time_units={'Elapsed': 'min'})
    result = parser.change_units(pd.DataFrame({'Elapsed': [0, 2.5]}))
    assert result['Elapsed'].tolist() == [0, 150]


def test_legacy_numeric_alias_keeps_default_and_allows_explicit_unit():
    data = pd.DataFrame({'Total Time': [0, 2.5]})
    assert Parser().change_units(data)['Total Time'].tolist() == [0, 2.5]
    parser = Parser(time_units={'Total Time': 'min'})
    assert parser.change_units(data)['Total Time'].tolist() == [0, 150]


@pytest.mark.parametrize('marker', ['s', '[h]'])
def test_conflicting_leading_unit_is_rejected(marker):
    parser = Parser(time_units={'TestTime': 'min'})
    with pytest.raises(ValueError, match='Conflicting leading'):
        parser.change_units(pd.DataFrame({'TestTime': [marker, '0', '2.5']}))


@pytest.mark.parametrize('values', [
    pd.Series([False, True]), pd.Series([0, True], dtype=object),
    pd.Series([0j, 1 + 2j]),
])
def test_boolean_and_complex_values_are_not_elapsed_measurements(values):
    with pytest.raises(ValueError, match='elapsed time'):
        Parser(time_units={'TestTime': 's'}).change_units(
            pd.DataFrame({'TestTime': values}))


@pytest.mark.parametrize('column,marker,expected', [
    ('TestTime(s)', 'sec', 2.5), ('TestTime(s)', '[seconds]', 2.5),
    ('Run Time (h)', 'hours', 9000),
])
def test_common_leading_unit_labels_are_not_measurements(column, marker, expected):
    result = Parser().change_units(pd.DataFrame({column: [marker, '0', '2.5']}))
    assert pd.isna(result[column].iloc[0])
    assert result[column].iloc[1:].tolist() == [0, expected]


@pytest.mark.parametrize('column', ['TestTime', 'TestTime(s)', 'Run Time (h)'])
@pytest.mark.parametrize('tz', [None, 'UTC'])
def test_calendar_datetimes_are_not_elapsed_time(column, tz):
    values = pd.date_range('2024-02-03', periods=2, tz=tz)
    with pytest.raises(ValueError, match='datetime'):
        Parser(time_units={'TestTime': 's'}).change_units(
            pd.DataFrame({column: values}))


@pytest.mark.parametrize('values', [[0, .25, 27.5], ['0', '0.25', '27.5']])
def test_explicit_hour_header_still_converts_hours_to_seconds(values):
    result = Parser().change_units(pd.DataFrame({'Run Time (h)': values}))
    assert result['Run Time (h)'].tolist() == pytest.approx([0, 900, 99000])


def write_export(path, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        stream.write('Technique started on : 03/02/2024 04:05:06\n')
        writer = csv.writer(stream)
        writer.writerow(['TestTime', 'Current [A]', 'Voltage [V]', 'Cell ID'])
        writer.writerows(rows)


def test_minutes_import_has_expected_seconds_and_absolute_times(tmp_path):
    source = tmp_path / 'minutes.csv'
    write_export(source, [[0, 1, 3.5, 'sample'], [2.5, 1, 3.6, 'sample']])
    with pytest.raises(ValueError, match='time_units'):
        Parser().data_importer(source, save_option='save')
    data = Parser(time_units={'TestTime': 'min'}).data_importer(
        source, save_option='none', dtype={'TestTime': 'string'})
    assert data['Time [s]'].tolist() == [0, 150]
    assert data['Absolute Time [s]'].tolist() == [
        pd.Timestamp('2024-02-03 04:05:06'), pd.Timestamp('2024-02-03 04:07:36')]
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize('dtype', [None, {'TestTime': str}, {'TestTime': 'string'}])
@pytest.mark.parametrize('times', [
    [0, 12.75, 93784.625],
    ['00:00:00', '00:00:12.75', '26:03:04.625'],
    [0, '00:00:12.75', 93784.625],
])
def test_import_retains_seconds_and_absolute_timestamps(tmp_path, dtype, times):
    source = tmp_path / 'elapsed.csv'
    write_export(source, [[value, 1, 3.5, 'sample'] for value in times])
    original = source.read_bytes()
    data = Parser(time_units={'TestTime': 's'}).data_importer(
        source, save_option='none', dtype=dtype)
    assert len(data) == 3
    assert data['Time [s]'].tolist() == pytest.approx([0, 12.75, 93784.625])
    assert data['Absolute Time [s]'].tolist() == [
        pd.Timestamp('2024-02-03 04:05:06'),
        pd.Timestamp('2024-02-03 04:05:18.750'),
        pd.Timestamp('2024-02-04 06:08:10.625'),
    ]
    assert source.read_bytes() == original
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize('marker', ['s', '[s]', 'h:m:s', '[h:m:s]', ''])
@pytest.mark.parametrize('dtype', [None, {'TestTime': 'string'}])
def test_leading_units_row_is_not_a_measurement(tmp_path, marker, dtype):
    source = tmp_path / 'units.csv'
    write_export(source, [[marker, 'A', 'V', 'units'],
                          [0, 1, 3.5, 'sample'], [12.75, 1, 3.6, 'sample']])
    result = Parser(time_units={'TestTime': 's'}).data_importer(
        source, save_option='none', dtype=dtype)
    assert len(result) == 2
    assert result['Time [s]'].tolist() == pytest.approx([0, 12.75])


@pytest.mark.parametrize('bad_time', ['', 'invalid', 's', 'h:m:s', 'nan', 'inf'])
@pytest.mark.parametrize('all_fields_invalid', [False, True])
def test_interior_invalid_time_cannot_disappear_in_cleanup(
    tmp_path, bad_time, all_fields_invalid
):
    source = tmp_path / 'invalid.csv'
    invalid = [bad_time, '', '', ''] if all_fields_invalid else [bad_time, 1, 3.5, 'x']
    write_export(source, [[0, 1, 3.5, 'sample'], invalid, [24, 1, 3.6, 'sample']])
    original = source.read_bytes()
    # pandas treats an empty field and the NA marker "nan" as missing values.
    # Entirely missing rows may be dropped; partially populated rows may not.
    if all_fields_invalid and bad_time in {'', 'nan'}:
        data = Parser(time_units={'TestTime': 's'}).data_importer(
            source, save_option='none', dtype={'TestTime': 'string'})
        assert data['Time [s]'].tolist() == [0, 24]
    else:
        with pytest.raises(ValueError):
            Parser(time_units={'TestTime': 's'}).data_importer(
                source, save_option='save', dtype={'TestTime': 'string'})
    assert source.read_bytes() == original
    assert list(tmp_path.iterdir()) == [source]


def test_missing_initial_time_with_real_measurements_is_rejected(tmp_path):
    source = tmp_path / 'missing.csv'
    write_export(source, [['', 1, 3.5, 'sample'], [12, 1, 3.6, 'sample']])
    with pytest.raises(ValueError):
        Parser(time_units={'TestTime': 's'}).data_importer(source, save_option='save')
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize('dtype', [None, {'TestTime': 'string'}])
def test_numeric_seconds_enable_real_duration_cc_and_cv_selection(tmp_path, dtype):
    source = tmp_path / 'phases.csv'
    times = [0, 7, 14, 21, 28, 35, 42]
    currents = [1, 1, 1, 1, .7, .4, .2]
    voltages = [3.5, 3.7, 3.9, 4.2, 4.2, 4.2, 4.2]
    write_export(source, [[t, i, v, 'sample'] for t, i, v in
                          zip(times, currents, voltages)])
    data = Parser(time_units={'TestTime': 's'}).data_importer(
        source, save_option='none', state_option='yes', dtype=dtype)
    for query, expected in [('cc', times[:4]), ('cv', times[4:]), ('cccv', times)]:
        result = segment_data(data, [query])
        assert len(result) == 1
        assert result[0]['Time [s]'].tolist() == expected
