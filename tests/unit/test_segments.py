"""Expected selections for notebook examples and bounded request validation."""
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from pbdp.segment import segment_data


@pytest.fixture
def power_runs():
    current = [0, 1, 1, 1, 0, 1, 1, 1, -1, -1, -1, 2, 2]
    return pd.DataFrame({
        'Time [s]': [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 59],
        'Current [A]': current,
        'Voltage [V]': [4.0] * len(current),
        'Battery State': ['rest' if i == 0 else 'charging' if i > 0
                          else 'discharging' for i in current],
        'CCCV': ['N/A' if i == 0 else 'CC' for i in current],
    }, index=['sample'] * len(current))


@pytest.mark.parametrize('query,bounds', [
    ('power', [(1, 4), (5, 8), (8, 11)]),
    ('power 4W', [(1, 4), (5, 8)]),
    ('power -4W', [(8, 11)]),
    ('power 8W', []),
    ('power 0W', []),
])
def test_power_selects_contiguous_nonrest_runs_of_at_least_ten_seconds(
    power_runs, query, bounds
):
    original = power_runs.copy(deep=True)
    result = segment_data(power_runs, [query])
    expected = power_runs.assign(**{'Power [W]': power_runs['Current [A]'] * 4.0})
    assert len(result) == len(bounds)
    for actual, (start, stop) in zip(result, bounds):
        assert_frame_equal(actual, expected.iloc[start:stop])
    assert_frame_equal(power_runs, original)


def test_power_tolerance_and_rounded_target_do_not_bridge_excluded_rows():
    frame = pd.DataFrame({
        'Time [s]': [0, 5, 10, 15, 20, 25, 30, 35, 40],
        'Current [A]': [1.0] * 9,
        'Voltage [V]': [4, 4.004, 4.004, 4.008, 4.004, 4, 4, 4.03, 4.03],
        'Battery State': ['charging'] * 9,
        'CCCV': ['CC'] * 9,
    })
    result = segment_data(frame, ['power 4W'])
    assert len(result) == 2
    assert result[0]['Time [s]'].tolist() == [0, 5, 10]
    assert result[1]['Time [s]'].tolist() == [20, 25, 30]
    unfiltered = segment_data(frame, ['power'])
    assert len(unfiltered) == 1
    assert unfiltered[0]['Time [s]'].tolist() == [0, 5, 10, 15, 20, 25, 30]


@pytest.mark.parametrize('query', [
    'power 4', 'power W', 'power 4A', 'power 4W extra', 'power nanW', 'power infW',
])
def test_invalid_power_queries_fail_clearly(power_runs, query):
    with pytest.raises(ValueError, match='power request'):
        segment_data(power_runs, [query])


@pytest.fixture
def cycle():
    return pd.DataFrame({
        'Time [s]': [0, 10, 20, 30, 40, 50],
        'Current [A]': [0, 1, 1, .5, .2, 0],
        'Voltage [V]': [3.5, 3.6, 4, 4.2, 4.2, 4.2],
        'Battery State': ['rest'] + ['charging'] * 4 + ['rest'],
        'CCCV': ['N/A', 'CC', 'CC', 'CV', 'CV', 'N/A'],
        'Step Number': [1, 2, 2, 3, 3, 4],
    })


@pytest.mark.parametrize('query,start,stop', [
    ('rest,cc 1A', 0, 3), ('cv , rest', 3, 6), ('cc,cv', 1, 5),
    ('time 10/30', 1, 4), ('step 2:3', 1, 5),
])
def test_notebook_selection_values(cycle, query, start, stop):
    result = segment_data(cycle, [query])
    assert len(result) == 1
    assert_frame_equal(result[0], cycle.iloc[start:stop])


@pytest.mark.parametrize('query', [
    'cc 1A, cv 4.2V', 'rest, cc 1A extra', ', cc', 'rest,', 'rest, cc, cv',
    'unknown, rest', 'rest, unknown', 'rest, cc 1V', 'rest, cc nanA',
    'rest, rest 1A', 'pulse, rest', 'cccv, rest', 'cv, cc 1A',
])
def test_unsupported_combined_queries_fail_clearly(cycle, query):
    with pytest.raises(ValueError, match='combined request'):
        segment_data(cycle, [query])
