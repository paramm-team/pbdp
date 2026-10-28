"""Segmentation must follow row order, independently of index labels."""
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from pbdp.segment import find_periods, find_rest, reset_time, segment_data


@pytest.fixture
def cycle():
    return pd.DataFrame({
        'Time [s]': [0, 10, 20, 30, 40],
        'Current [A]': [0, 1, 1, 0.5, 0.2],
        'Voltage [V]': [3.5, 3.6, 4.0, 4.2, 4.2],
        'Battery State': ['rest'] + ['charging'] * 4,
        'CCCV': ['N/A', 'CC', 'CC', 'CV', 'CV'],
    })


@pytest.mark.parametrize('index', [
    [100, 105, 110, 115, 120], [20, 10, 9, 5, 1],
    ['a', 'b', 'c', 'd', 'e'], [0, 0, 1, 1, 1],
    pd.date_range('2026-01-01', periods=5, freq='s'),
])
@pytest.mark.parametrize('query', ['cccv', 'cccv 1A 4.2V', 'rest, cc 1A'])
def test_adjacent_phases_preserve_original_index(cycle, index, query):
    cycle.index = index
    original = cycle.copy(deep=True)
    result = segment_data(cycle, [query])
    expected = cycle.iloc[:3] if query.startswith('rest') else cycle.iloc[1:]
    assert len(result) == 1
    assert_frame_equal(result[0], expected)
    assert_frame_equal(cycle, original)


def test_cccv_does_not_bridge_intervening_rest(cycle):
    cycle.loc[2, ['Battery State', 'CCCV']] = ['rest', 'N/A']
    cycle.index = [10, 15, 999, 16, 17]
    assert segment_data(cycle, ['cccv']) == []


@pytest.mark.parametrize('query', ['', ' ', '\t\n', None, 'not-a-state'])
def test_invalid_requests_fail_clearly(cycle, query):
    with pytest.raises(ValueError, match='request'):
        segment_data(cycle, [query])


def test_whitespace_is_accepted(cycle):
    result = segment_data(cycle, ['  cccv\t1A   4.2V  '])
    assert_frame_equal(result[0], cycle.iloc[1:])


def test_pulse_at_end_does_not_read_past_recording(cycle):
    data = cycle.iloc[1:3].copy()
    data.index = ['start', 'end']
    result = segment_data(data, ['pulse'])
    assert len(result) == 1
    assert_frame_equal(result[0], data)


def test_pulse_excludes_cv_within_lookahead(cycle):
    assert find_periods(cycle, 'pulse', pulse_t=5) == []


def test_reset_empty_segment():
    frame = pd.DataFrame({'Time [s]': pd.Series(dtype=float)})
    result = reset_time([frame])[0]
    assert result.empty
    assert result.columns.tolist() == ['Time [s]', 'Original Time [s]']


def test_rest_only_includes_immediately_adjacent_intervals():
    frame = pd.DataFrame({
        'Current [A]': [0, 2, 0, 1, 1, 0, 0, 3, 0],
        'Time [s]': list(range(9)),
    }, index=['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'])
    result = find_rest(frame, [frame.iloc[3:5]])
    assert_frame_equal(result[0], frame.iloc[2:7])


def test_rest_at_end_of_recording_is_included():
    frame = pd.DataFrame({'Current [A]': [1, 1, 0, 0]}, index=[10, 20, 30, 40])
    result = find_rest(frame, [frame.iloc[:2]])
    assert_frame_equal(result[0], frame)


@pytest.mark.parametrize('index', [
    [0, 0, 1, 1, 1, 2, 2], ['a', 'b', 'a', 'c', 'b', 'c', 'a'],
])
def test_automatic_classification_preserves_duplicate_index(index):
    frame = pd.DataFrame({
        'Time [s]': [0, 5, 10, 15, 20, 25, 30],
        'Current [A]': [1, 1, 1, 1, .7, .4, .2],
        'Voltage [V]': [3.5, 3.7, 3.9, 4.2, 4.2, 4.2, 4.2],
    }, index=index)
    result = segment_data(frame, ['cccv'])
    assert len(result) == 1
    assert result[0].index.tolist() == index
    assert result[0]['CCCV'].tolist() == ['CC'] * 4 + ['CV'] * 3
    assert result[0]['Time [s]'].tolist() == [0, 5, 10, 15, 20, 25, 30]
