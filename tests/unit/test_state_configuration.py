"""Explicit current conventions and duration-based phase classification."""
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal, assert_series_equal

from pbdp import states


def frame(times, current, voltage=None):
    return pd.DataFrame({
        'Time [s]': times, 'Current [A]': current,
        'Voltage [V]': voltage if voltage is not None else [4.0] * len(times),
    })


@pytest.mark.parametrize('epsilon', [-1, float('nan'), float('inf'), True, '0.1'])
def test_invalid_current_threshold_rejected(epsilon):
    with pytest.raises(ValueError, match='current_epsilon'):
        states.add_state_label(frame([0], [0]), current_epsilon=epsilon)


@pytest.mark.parametrize('epsilon', [0, .2])
def test_rest_threshold_is_inclusive(epsilon):
    current = [-epsilon - .1, -epsilon, 0, epsilon, epsilon + .1]
    result = states.add_state_label(frame(range(5), current), epsilon)
    assert result['Battery State'].tolist() == [
        'discharging', 'rest', 'rest', 'rest', 'charging']


def test_phase_detection_propagates_implicit_state_threshold():
    result = states.find_cc_and_cv(
        frame([0, 10, 20], [.1] * 3), current_epsilon=.2)
    assert result['Battery State'].tolist() == ['rest'] * 3
    assert result['CCCV'].tolist() == ['N/A'] * 3


def test_explicit_modes_preserve_measured_current_and_source_frame():
    data = frame([0, 5, 10, 15, 20], [1.0, 2.0, -.5, .001, -.001])
    data['Mode'] = ['C', 'D', 'C', 'R', 'R']
    data['Battery State'] = ['charging'] * len(data)
    data['CCCV'] = ['CC'] * len(data)
    data.index = ['sample'] * len(data)
    original = data.copy(deep=True)
    result = states.normalize_current_direction(
        data, 'Mode', {'C': 'charging', 'D': 'discharging', 'R': 'rest'})
    assert_frame_equal(data, original)
    assert_series_equal(result['Source current [A]'], original['Current [A]'],
                        check_names=False)
    assert result['Current [A]'].tolist() == [1, -2, .5, .001, -.001]
    assert result['Battery State'].tolist() == [
        'charging', 'discharging', 'charging', 'rest', 'rest']
    assert 'CCCV' not in result
    assert result['Mode'].tolist() == original['Mode'].tolist()


@pytest.mark.parametrize('column,mapping', [
    ('Mode', None), (None, {'C': 'charging'}), ('', {'C': 'charging'}),
    ('Mode', {}), ('Mode', {'C': 'charge'}), ('Mode', []),
])
def test_invalid_current_configuration_rejected(column, mapping):
    with pytest.raises(ValueError, match='mode'):
        states.validate_current_configuration(.001, column, mapping)


@pytest.mark.parametrize('mode', ['unknown', None])
def test_unknown_modes_rejected_without_partial_normalization(mode):
    data = frame([0, 10], [1, 2])
    data['Mode'] = ['D', mode]
    original = data.copy(deep=True)
    with pytest.raises(ValueError, match='mode.*row 1'):
        states.normalize_current_direction(data, 'Mode', {'D': 'discharging'})
    assert_frame_equal(data, original)


def test_rest_mode_does_not_silently_zero_real_current():
    data = frame([0], [.02]).assign(Mode='R')
    with pytest.raises(ValueError, match='rest.*current_epsilon'):
        states.normalize_current_direction(data, 'Mode', {'R': 'rest'})
    assert data['Current [A]'].tolist() == [.02]


def test_source_current_provenance_cannot_be_overwritten():
    data = frame([0], [1]).assign(Mode='C', **{'Source current [A]': [2]})
    with pytest.raises(ValueError, match='Source current'):
        states.normalize_current_direction(data, 'Mode', {'C': 'charging'})


@pytest.mark.parametrize('current', [float('nan'), float('inf'), 'invalid'])
def test_nonfinite_current_rejected(current):
    with pytest.raises(ValueError, match='Current'):
        states.add_state_label(frame([0], [current]))


def protocol(times):
    current, voltage, expected = [], [], []
    for time in times:
        if time < 20:
            current.append(0)
            voltage.append(3.5)
            expected.append('N/A')
        elif time <= 60:
            current.append(1)
            voltage.append(3.5 + .7 * (time - 20) / 40)
            expected.append('CC')
        elif time < 100:
            current.append(1 - .02 * (time - 60))
            voltage.append(4.2)
            expected.append('CV')
        else:
            current.append(0)
            voltage.append(4.1)
            expected.append('N/A')
    return frame(times, current, voltage), expected


@pytest.mark.parametrize('times', [
    list(range(0, 121)), list(range(0, 121, 5)), list(range(0, 121, 10)),
    [0, 7, 19, 20, 23, 31, 48, 59, 60, 62, 67, 81, 94, 99, 100, 113, 120],
])
def test_equivalent_sampled_protocol_has_expected_phases(times):
    data, expected = protocol(times)
    data.index = ['sample'] * len(data)
    result = states.find_cc_and_cv(data)
    assert result['CCCV'].tolist() == expected
    assert result.index.tolist() == ['sample'] * len(data)


def test_gradual_adjacent_drift_is_not_a_constant_plateau():
    data = frame([0, 5, 10, 15, 20],
                 [1, 1.0006, 1.0012, 1.0018, 1.0024],
                 [3, 3.0006, 3.0012, 3.0018, 3.0024])
    result = states.find_cc_and_cv(data)
    assert result['CCCV'].tolist() == ['N/A'] * 5


def test_full_plateau_range_can_include_small_measurement_noise():
    data = frame([0, 5, 10, 15], [1, 1.0004, .9997, 1.0002], [3, 3.2, 3.4, 3.6])
    assert states.find_cc_and_cv(data)['CCCV'].tolist() == ['CC'] * 4


@pytest.mark.parametrize('separator', ['rest', 'direction', 'gap', 'duplicate'])
def test_phase_durations_do_not_bridge_separators(separator):
    times = [0, 5, 6, 7, 12]
    current = [1, 1, 0, 1, 1]
    options = {}
    if separator == 'direction':
        current = [1, 1, -1, 1, 1]
    elif separator == 'gap':
        times, current = [0, 5, 30, 35], [1] * 4
        options['max_gap_s'] = 10
    elif separator == 'duplicate':
        times, current = [0, 5, 5, 10], [1] * 4
    result = states.find_cc_and_cv(frame(times, current), **options)
    assert result['CCCV'].tolist() == ['N/A'] * len(times)


def test_decreasing_time_is_rejected():
    with pytest.raises(ValueError, match='Time.*nondecreasing'):
        states.find_cc_and_cv(frame([0, 10, 5], [1] * 3))


@pytest.mark.parametrize('option,value', [
    ('time_t', -1), ('time_t', float('nan')),
    ('voltage_epsilon', -1), ('voltage_epsilon', float('inf')),
    ('max_gap_s', 0), ('max_gap_s', -1), ('max_gap_s', float('inf')),
    ('rest_t', -1), ('cc_t', 1.5),
])
def test_invalid_phase_parameters_rejected(option, value):
    with pytest.raises(ValueError, match=option):
        states.find_cc_and_cv(frame([0, 10], [1, 1]), **{option: value})


def test_explicit_legacy_row_context_is_still_available():
    data = frame([0, 5, 10, 15, 20, 25], [.2, .4, .6, 1, 1, 1],
                 [3, 3.1, 3.2, 3.3, 3.4, 3.5])
    assert states.find_cc_and_cv(data.copy())['CCCV'].tolist() == [
        'N/A', 'N/A', 'N/A', 'CC', 'CC', 'CC']
    result = states.find_cc_and_cv(data.copy(), rest_t=8, cc_t=5)
    assert result['CCCV'].tolist() == ['N/A'] * len(data)


def test_recording_can_begin_during_cv():
    data = frame([0, 5, 10, 15], [1, .8, .5, .2])
    assert states.find_cc_and_cv(data)['CCCV'].tolist() == ['CV'] * 4
