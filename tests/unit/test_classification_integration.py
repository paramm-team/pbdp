"""Threshold and continuity metadata survive public classification workflows."""
import json

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from pbdp import Parser
from pbdp.segment import find_rest, segment_data
from pbdp.states import add_state_label, find_cc_and_cv, normalize_current_direction


def frame(times, current, voltage=None):
    return pd.DataFrame({
        'Time [s]': times, 'Current [A]': current,
        'Voltage [V]': voltage if voltage is not None else [4.0] * len(times),
    })


def test_imported_low_current_threshold_survives_implicit_classification(tmp_path):
    source = tmp_path / 'small_current.csv'
    source.write_text('time/s,Current [A],Voltage [V]\n'
                      '0,0.0001,3.0\n10,0.0001,3.1\n20,0.0001,3.2\n')
    data = Parser(current_epsilon=.00005).data_importer(
        source, save_option='none', state_option='yes')
    assert data.attrs['pbdp_current_epsilon'] == .00005
    for query in ['charging', 'cc', 'power']:
        result = segment_data(data, [query])
        assert len(result) == 1
        assert result[0]['Time [s]'].tolist() == [0, 10, 20]
    assert segment_data(data, ['rest']) == []


def test_explicit_rest_threshold_controls_power_and_rest_extension():
    data = frame([0, 10, 20, 30], [.01, 1, 1, -.01])
    add_state_label(data, .01)
    assert data.attrs['pbdp_current_epsilon'] == .01
    result = find_rest(data, [data.iloc[1:3]])
    assert_frame_equal(result[0], data)
    result = segment_data(data, ['power'])
    assert len(result) == 1
    assert result[0]['Time [s]'].tolist() == [10, 20]


def test_state_and_normalization_helpers_inherit_recorded_threshold():
    data = frame([0, 10], [.05, -.05]).assign(Mode='R')
    data.attrs['pbdp_current_epsilon'] = .1
    normalized = normalize_current_direction(data, 'Mode', {'R': 'rest'})
    assert normalized['Current [A]'].tolist() == [.05, -.05]
    assert normalized.attrs['pbdp_current_epsilon'] == .1
    assert add_state_label(normalized)['Battery State'].tolist() == ['rest', 'rest']


@pytest.mark.parametrize('query', ['cc', 'charging', 'power'])
def test_two_qualified_runs_across_gap_stay_separate(query):
    data = frame([0, 5, 10, 100, 105, 110], [1] * 6)
    find_cc_and_cv(data, max_gap_s=10)
    original = data.copy(deep=True)
    result = segment_data(data, [query])
    assert [part['Time [s]'].tolist() for part in result] == [
        [0, 5, 10], [100, 105, 110]]
    assert_frame_equal(data, original)
    assert json.loads(json.dumps(data.attrs))['pbdp_classification']['max_gap_s'] == 10


@pytest.mark.parametrize('query', ['cccv', 'cc,cv'])
def test_combined_cc_cv_cannot_cross_recording_gap(query):
    data = frame([0, 5, 10, 100, 105, 110], [1, 1, 1, .8, .5, .2],
                 [3.5, 3.8, 4.2, 4.2, 4.2, 4.2])
    find_cc_and_cv(data, max_gap_s=10)
    assert data['CCCV'].tolist() == ['CC'] * 3 + ['CV'] * 3
    assert segment_data(data, [query]) == []


@pytest.mark.parametrize('times,current', [
    ([0, 5, 10, 10, 15, 20], [1] * 6),
    ([0, 5, 10, 15, 20, 25], [1, 1, 1, -1, -1, -1]),
])
def test_phase_grouping_respects_duplicate_time_and_direction(times, current):
    data = frame(times, current)
    find_cc_and_cv(data)
    result = segment_data(data, ['cc'])
    assert len(result) == 2
    assert [len(part) for part in result] == [3, 3]


def test_explicit_options_reclassify_but_existing_snapshot_is_preserved_by_default():
    data = frame([0, 5, 10], [1, 1, 1], [3, 3.2, 3.4])
    data['Battery State'] = 'charging'
    data['CCCV'] = 'CV'
    original = data.copy(deep=True)
    assert len(segment_data(data, ['cv'])) == 1
    result = segment_data(data, ['cc'], classification_options={})
    assert len(result) == 1
    assert result[0]['CCCV'].tolist() == ['CC'] * 3
    assert_frame_equal(data, original)


def test_csv_reload_can_restore_threshold_and_gap_options(tmp_path):
    source = tmp_path / 'snapshot.csv'
    data = frame([0, 5, 10, 100, 105, 110], [.0001] * 6)
    find_cc_and_cv(data, current_epsilon=.00005, max_gap_s=10)
    data.to_csv(source, index=False)
    restored = pd.read_csv(source)
    assert restored.attrs == {}
    result = segment_data(restored, ['cc'], classification_options={
        'current_epsilon': .00005, 'max_gap_s': 10})
    assert [len(part) for part in result] == [3, 3]


def test_rest_extension_cannot_cross_configured_gap():
    data = frame([0, 5, 100, 105, 110], [0, 0, 1, 1, 0])
    find_cc_and_cv(data, max_gap_s=10)
    assert_frame_equal(find_rest(data, [data.iloc[2:4]])[0], data.iloc[2:])


def test_rest_extension_inherits_gap_from_segments_classified_on_a_copy():
    data = frame([0, 10, 1000, 1001], [1, 1, 0, 0])
    original = data.copy(deep=True)
    segments = segment_data(data, ['cc'], classification_options={'max_gap_s': 20})
    extended = find_rest(data, segments)
    assert extended[0].index.tolist() == [0, 1]
    assert extended[0].attrs['pbdp_classification']['max_gap_s'] == 20
    assert_frame_equal(data, original)
    assert data.attrs == original.attrs == {}


def test_rest_extension_prefers_segment_threshold_but_allows_explicit_override():
    data = frame([0, 10, 11, 12], [1, 1, .0005, .0005])
    segments = segment_data(data, ['cc'], classification_options={
        'current_epsilon': .0001})
    extended = find_rest(data, segments)
    assert extended[0].index.tolist() == [0, 1]
    assert extended[0].attrs['pbdp_current_epsilon'] == .0001
    overridden = find_rest(data, segments, current_epsilon=.001)
    assert overridden[0].index.tolist() == [0, 1, 2, 3]
    assert overridden[0].attrs['pbdp_current_epsilon'] == .001
    assert segments[0].attrs['pbdp_current_epsilon'] == .0001
    assert data.attrs == {}


def test_rest_extension_handles_distinct_segment_settings_in_one_call():
    data = frame([0, 10, 1000, 1001], [1, 1, 0, 0])
    limited = segment_data(data, ['cc'], classification_options={'max_gap_s': 20})
    unlimited = segment_data(data, ['cc'], classification_options={'max_gap_s': None})
    extended = find_rest(data, [limited[0], unlimited[0]])
    assert [part.index.tolist() for part in extended] == [[0, 1], [0, 1, 2, 3]]


@pytest.mark.parametrize('options', [[], {'unknown_option': 2}])
def test_invalid_classification_options_fail_clearly(options):
    with pytest.raises(ValueError, match='classification_options'):
        segment_data(frame([0, 10], [1, 1]), ['cc'],
                     classification_options=options)
