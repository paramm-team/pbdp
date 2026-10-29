"""Mixed time-domain and EIS records must never disappear during cleanup."""
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from pbdp import Parser


def measurement_rows():
    return pd.DataFrame({
        'Time [s]': [0., 1., 2.], 'Current [A]': [1., 1., 1.],
        'Voltage [V]': [3.5, 3.6, 3.7], 'freq [Hz]': [100., 10., 1.],
        'ReZ [Ohm]': [.1, .2, .3], 'ImZ [Ohm]': [-.01, -.02, -.03],
    }, index=['a', 'b', 'c'])


@pytest.mark.parametrize('position', [0, 1, 2])
def test_mixed_rows_rejected_before_cleanup_at_any_position(position):
    data = measurement_rows()
    data.iloc[position, 3:] = float('nan')
    original = data.copy(deep=True)
    parser = Parser()
    report = parser.inspect_measurement_schema(data)
    assert report['kind'] == 'mixed'
    assert report['cycling_only_rows'] == [position]
    with pytest.raises(ValueError, match=f'Mixed cycling/EIS.*row {position}'):
        parser.remove_unwanted(data)
    assert_frame_equal(data, original)


def test_pure_eis_with_auxiliary_cycling_columns_is_preserved():
    data = measurement_rows()
    parser = Parser()
    assert parser.inspect_measurement_schema(data)['kind'] == 'eis'
    result = parser.remove_unwanted(data)
    assert_frame_equal(result, data.reset_index(drop=True))
    assert parser.sanity_check(result) == 0


def test_units_row_is_not_a_cycling_measurement():
    data = measurement_rows().reset_index(drop=True)
    units = pd.DataFrame([['s', 'A', 'V', 'Hz', 'Ohm', 'Ohm']], columns=data.columns)
    normalized = Parser().change_headers(pd.concat([units, data], ignore_index=True))
    assert Parser().inspect_measurement_schema(normalized)['cycling_only_rows'] == []
    assert len(Parser().remove_unwanted(normalized)) == 3


def test_missing_time_does_not_make_auxiliary_voltage_columns_cycling():
    data = measurement_rows().drop(columns='Time [s]')
    data['Working electrode potential [V]'] = [3.5, 3.6, 3.7]
    assert Parser().inspect_measurement_schema(data)['kind'] == 'eis'


def test_working_electrode_only_rows_are_also_preserved_by_rejection():
    data = measurement_rows().rename(columns={
        'Voltage [V]': 'Working electrode potential [V]'})
    data.iloc[0, 3:] = float('nan')
    with pytest.raises(ValueError, match='Mixed cycling/EIS'):
        Parser().remove_unwanted(data)


def test_partial_impedance_record_still_fails_validation():
    data = measurement_rows()
    data.loc['b', 'ImZ [Ohm]'] = float('nan')
    result = Parser().remove_unwanted(data)
    with pytest.raises(ValueError, match='finite'):
        Parser().sanity_check(result)


@pytest.mark.parametrize('position', [0, 1, 2])
def test_mixed_import_fails_without_processed_output(tmp_path, position):
    data = measurement_rows()
    data.iloc[position, 3:] = float('nan')
    source = tmp_path / 'mixed.csv'
    data.to_csv(source, index=False)
    original = source.read_bytes()
    with pytest.raises(ValueError, match='Mixed cycling/EIS'):
        Parser().data_importer(source, cycler='1', save_option='save')
    assert source.read_bytes() == original
    assert list(tmp_path.iterdir()) == [source]
