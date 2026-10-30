"""Public importer configuration using only invented battery measurements."""
from pathlib import Path

import pytest

from pbdp import Parser


def write_cycle(directory: Path, currents=(1, 1, 0)) -> Path:
    path = directory / 'configured_cycle.csv'
    path.write_text(
        'Technique started on : 03/02/2024 04:05:06\n'
        'TestTime,Current [A],Voltage [V],Md\n'
        + ''.join(f'{t},{current},3.5,{mode}\n'
                  for t, current, mode in zip((0, 1, 2), currents, ('C', 'D', 'R'))),
        encoding='utf-8',
    )
    return path


def test_import_combines_explicit_time_and_current_conventions(tmp_path):
    source = write_cycle(tmp_path)
    original = source.read_bytes()
    parser = Parser(
        time_units={'TestTime': 'min'}, current_mode_column='Md',
        current_mode_map={'C': 'charging', 'D': 'discharging', 'R': 'rest'},
    )
    result = parser.data_importer(source, save_option='none', state_option='yes')
    assert result['Time [s]'].tolist() == [0, 60, 120]
    assert result['Current [A]'].tolist() == [1, -1, 0]
    assert result['Source current [A]'].tolist() == [1, 1, 0]
    assert result['Md'].tolist() == ['C', 'D', 'R']
    assert result['Battery State'].tolist() == ['charging', 'discharging', 'rest']
    assert source.read_bytes() == original
    assert list(tmp_path.iterdir()) == [source]


def test_importer_uses_configured_small_current_threshold(tmp_path):
    source = write_cycle(tmp_path, currents=(.0005, -.0005, .0001))
    parser = Parser(time_units={'TestTime': 's'}, current_epsilon=.0001)
    result = parser.data_importer(source, save_option='none', state_option='yes')
    assert result['Battery State'].tolist() == ['charging', 'discharging', 'rest']
    assert 'Source current [A]' not in result


def test_unknown_mode_rejects_before_processed_output_is_saved(tmp_path):
    source = write_cycle(tmp_path)
    parser = Parser(
        time_units={'TestTime': 's'}, current_mode_column='Md',
        current_mode_map={'C': 'charging'},
    )
    original = source.read_bytes()
    with pytest.raises(ValueError):
        parser.data_importer(source, save_option='save', state_option='yes')
    assert source.read_bytes() == original
    assert list(tmp_path.iterdir()) == [source]


def test_direction_configuration_is_copied_and_validated_at_construction():
    mapping = {'C': 'charging'}
    parser = Parser(current_mode_column='Md', current_mode_map=mapping)
    mapping['C'] = 'discharging'
    assert parser.current_mode_map == {'C': 'charging'}
    with pytest.raises(ValueError):
        Parser(current_mode_column='Md')
    with pytest.raises(ValueError):
        Parser(current_epsilon=float('nan'))
