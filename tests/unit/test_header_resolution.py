"""Header spelling cannot bypass the physical unit conversion policy."""
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from pbdp import Parser


@pytest.mark.parametrize('header', ['Run time (h)', 'RUN TIME(h)', 'Run time[h]'])
def test_hour_header_variants_convert_before_renaming(header):
    parser = Parser()
    raw = pd.DataFrame({header: [0, 1.25]})
    result = parser.change_headers(parser.change_units(raw))
    assert result['Time [s]'].tolist() == [0, 4500]
    assert raw[header].tolist() == [0, 1.25]


@pytest.mark.parametrize('header', ['testtime', 'TEST TIME', ' TestTime '])
def test_ambiguous_time_aliases_cannot_bypass_unit_requirement(header):
    with pytest.raises(ValueError, match='time_units'):
        Parser().change_units(pd.DataFrame({header: [0, 2.5]}))


@pytest.mark.parametrize('header', ['i/mA', 'I [mA]', ' i / mA '])
def test_milliamp_aliases_keep_prefix_and_convert(header):
    parser = Parser()
    output = parser.change_headers(parser.change_units(pd.DataFrame({header: [1250]})))
    assert output['Current [A]'].tolist() == [1.25]


@pytest.mark.parametrize('header', ['I/MA', 'i/ma', 'Run Time (H)', 'time/S'])
def test_si_unit_case_is_not_guessed(header):
    with pytest.raises(ValueError, match='unit spelling'):
        Parser().change_units(pd.DataFrame({header: [1]}))


@pytest.mark.parametrize('config', [
    {'time_units': {'test time': 'min'}},
    {'standard_units': {' TESTTIME ': 60}},
    {'time_units': {'TESTTIME': 'min'}, 'standard_units': {'test time': 60}},
])
def test_configuration_keys_use_the_same_resolution(config):
    parser = Parser(**config)
    output = parser.change_headers(parser.change_units(
        pd.DataFrame({'TestTime': [0, 2.5]})))
    assert output['Time [s]'].tolist() == [0, 150]


@pytest.mark.parametrize('config', [
    {'standard_units': {'testtime': 1, 'TestTime': 60}},
    {'time_units': {'testtime': 's', 'TESTTIME': 'min'}},
    {'time_units': {'testtime': 's'}, 'standard_units': {'TESTTIME': 60}},
    {'standard_units': {'Run time[h]': 1}},
    {'time_units': {'time[s]': 'h'}},
])
def test_conflicting_normalized_configuration_is_rejected(config):
    with pytest.raises(ValueError, match='[Cc]onflicting|Duplicate'):
        Parser(**config)


def test_custom_current_factors_and_aliases_are_resolved_consistently():
    parser = Parser(standard_units={'i [mA]': .001})
    result = parser.change_headers(parser.change_units(pd.DataFrame({'I/mA': [2000]})))
    assert result['Current [A]'].tolist() == [2]


def test_explicit_custom_mega_and_milliamp_aliases_remain_distinct():
    parser = Parser(standard_headers={'Current [A]': ['I/mA', 'I/MA']},
                    standard_units={'I/mA': .001, 'I/MA': 1e6})
    for header, expected in [('i/mA', .001), ('i/MA', 1e6)]:
        result = parser.change_headers(parser.change_units(pd.DataFrame({header: [1]})))
        assert result['Current [A]'].tolist() == [expected]


@pytest.mark.parametrize('operation', ['change_units', 'change_headers'])
def test_alias_collisions_fail_before_data_changes(operation):
    raw = pd.DataFrame({'i/mA': [1000], 'Current [A]': [2]})
    original = raw.copy(deep=True)
    with pytest.raises(ValueError, match='Duplicate standardized'):
        getattr(Parser(), operation)(raw)
    assert_frame_equal(raw, original)


def test_conflicting_custom_alias_targets_are_rejected():
    parser = Parser(standard_headers={'one': ['value'], 'two': ['VALUE']})
    with pytest.raises(ValueError, match='Conflicting header aliases'):
        parser.resolve_columns(['value'])


def test_resolution_report_matches_conversion_without_mutation():
    parser = Parser(time_units={'testtime': 'min'})
    report = parser.resolve_columns(['TestTime', 'i/mA', 'Cell ID'])
    assert report['TestTime']['standard_header'] == 'Time [s]'
    assert report['TestTime']['is_elapsed'] is True
    assert report['TestTime']['numeric_factor'] == 60
    assert report['i/mA']['numeric_factor'] == .001
    assert report['i/mA']['standard_header'] == 'Current [A]'
    assert report['Cell ID']['matched_alias'] is None
    assert report['Cell ID']['numeric_factor'] is None


def test_variant_headers_work_in_the_import_pipeline(tmp_path):
    source = tmp_path / 'synthetic.csv'
    source.write_text('Run time(h),i/mA,Voltage (V)\n0,1000,3.5\n1,500,3.6\n')
    result = Parser().data_importer(source, cycler='1', save_option='none')
    assert result['Time [s]'].tolist() == [0, 3600]
    assert result['Current [A]'].tolist() == [1, .5]


def test_lowercase_time_auto_import_requires_the_declared_unit(tmp_path):
    source = tmp_path / 'synthetic.csv'
    source.write_text('testtime,i/mA,Voltage (V)\n0,1000,3.5\n2.5,500,3.6\n')
    with pytest.raises(ValueError, match='time_units'):
        Parser().data_importer(source, save_option='save')
    result = Parser(time_units={'TESTTIME': 'min'}).data_importer(
        source, save_option='none')
    assert result['Time [s]'].tolist() == [0, 150]
    assert result['Current [A]'].tolist() == [1, .5]
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize('cycler', ['', 'vmp3'])
@pytest.mark.parametrize('extension,separator', [('csv', ','), ('mpt', '\t')])
def test_auto_header_ignores_keywords_in_preamble(
    tmp_path, cycler, extension, separator
):
    source = tmp_path / ('synthetic.' + extension)
    source.write_text('Mode: synthetic test\n'
                      + separator.join(['Description', 'Time (s)']) + '\n'
                      + separator.join(['time/s', 'i/mA', 'Ecell/V']) + '\n'
                      + separator.join(['0', '1000', '3.5']) + '\n')
    result = Parser().data_importer(source, cycler=cycler, save_option='none')
    assert result['Time [s]'].tolist() == [0]
    assert result['Current [A]'].tolist() == [1]


def test_quoted_metadata_keywords_are_not_header_fields(tmp_path):
    source = tmp_path / 'synthetic.csv'
    source.write_text('Description,"TestTime,Current,Voltage"\n'
                      'testtime,Current,Voltage\n00:00:00,1,3.5\n')
    result = Parser().data_importer(source, save_option='none')
    assert result['Time [s]'].tolist() == [0]


@pytest.mark.parametrize('factor', [0, -1, float('nan'), float('inf'), True, 1j, '1'])
def test_all_measurement_unit_factors_are_finite_and_positive(factor):
    with pytest.raises(ValueError, match='standard_units.*finite and positive'):
        Parser(standard_units={'i/mA': factor})


@pytest.mark.parametrize('position', [0, 1, 2])
def test_invalid_nonempty_rows_cannot_become_empty_during_coercion(tmp_path, position):
    rows = ['0,1,3.5', '1,1,3.6', '2,1,3.7']
    rows[position] = 'invalid,invalid,invalid'
    source = tmp_path / 'synthetic.csv'
    source.write_text('Total Time,Current,Voltage\n' + '\n'.join(rows) + '\n')
    original = source.read_bytes()
    with pytest.raises(ValueError, match='Invalid nonempty measurement row'):
        Parser().data_importer(source, save_option='save')
    assert source.read_bytes() == original
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize('time_marker', ['[s]', '[ss.xxx]'])
def test_raw_empty_and_leading_units_rows_still_clean_up(tmp_path, time_marker):
    source = tmp_path / 'synthetic.csv'
    source.write_text('Total Time,Current,Voltage\n'
                      + time_marker + ',[A],[V]\n0,1,3.5\n,,\n1,1,3.6\n')
    result = Parser().data_importer(source, save_option='none')
    assert result['Time [s]'].tolist() == [0, 1]
    assert '_pbdp_raw_rows' not in result.attrs


@pytest.mark.parametrize('time_header', ['Total Time', 'time/s'])
def test_explicit_final_record_count_footer_is_verified(tmp_path, time_header):
    source = tmp_path / 'synthetic.csv'
    source.write_text(time_header + ',Current,Voltage\n0,1,3.5\n1,1,3.6\n'
                      'Total Number of Data Lines in the Database: 2\n,,\n')
    result = Parser().data_importer(source, save_option='none')
    assert result['Time [s]'].tolist() == [0, 1]


@pytest.mark.parametrize('rows,expected_error', [
    ('0,1,3.5\nTotal Number of Data Lines in the Database: 2\n', 'Declared footer'),
    ('0,1,3.5\nTotal Number of Data Lines in the Database: 1\n1,1,3.6\n', 'Invalid'),
    ('0,1,3.5\ninvalid,invalid,invalid\n'
     'Total Number of Data Lines in the Database: 2\n', 'Invalid'),
    ('0,1,3.5\nTotal Number of Data Lines in the Database: 1,note,\n', 'Invalid'),
    ('0,1,3.5\nArbitrary invalid trailer\n', 'Invalid'),
])
def test_footer_rule_never_masks_invalid_records(tmp_path, rows, expected_error):
    source = tmp_path / 'synthetic.csv'
    source.write_text('Total Time,Current,Voltage\n' + rows)
    original = source.read_bytes()
    with pytest.raises(ValueError, match=expected_error):
        Parser().data_importer(source, save_option='save')
    assert source.read_bytes() == original
    assert list(tmp_path.iterdir()) == [source]


def test_footer_count_includes_preceding_parsed_units_and_empty_records(tmp_path):
    source = tmp_path / 'synthetic.csv'
    source.write_text('Total Time,Current,Voltage\ns,A,V\n0,1,3.5\n,,\n1,1,3.6\n'
                      'Total Number of Data Lines in the Database: 4\n')
    result = Parser().data_importer(source, save_option='none')
    assert result['Time [s]'].tolist() == [0, 1]
