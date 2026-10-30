import pandas as pd
import logging
from numbers import Real

import numpy as np


def _validate_threshold(value, name, positive=False):
    if (isinstance(value, (bool, np.bool_)) or not isinstance(value, Real)
            or not np.isfinite(value) or value < 0 or (positive and value == 0)):
        requirement = 'positive' if positive else 'nonnegative'
        raise ValueError(f'{name} must be a finite {requirement} number')


def validate_current_configuration(current_epsilon=.001, mode_column=None,
                                   mode_map=None):
    """Validate an explicit current convention without reading or changing data."""
    _validate_threshold(current_epsilon, 'current_epsilon')
    if mode_column is None and mode_map is None:
        return
    if not isinstance(mode_column, str) or not mode_column.strip():
        raise ValueError('mode_column must name the explicit source mode column')
    if not isinstance(mode_map, dict) or not mode_map:
        raise ValueError('mode_map must be a nonempty dictionary with mode_column')
    for state in mode_map.values():
        if (not isinstance(state, str)
                or state not in {'charging', 'discharging', 'rest'}):
            raise ValueError('mode_map values must be charging, discharging, or rest')


def _measurement_values(data, column):
    if not data.columns.is_unique:
        raise ValueError('Duplicate measurement column names are ambiguous')
    if column not in data.columns:
        raise ValueError(f'{column}, required column not found in dataframe')
    try:
        values = pd.to_numeric(data[column], errors='coerce').to_numpy(
            dtype=float, na_value=np.nan)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{column} must contain finite numbers') from exc
    invalid = np.flatnonzero(~np.isfinite(values))
    if invalid.size:
        raise ValueError(
            f'{column} must contain finite numbers; invalid row {invalid[0]}'
        )
    return values


def _state_labels(current, current_epsilon):
    return np.where(np.abs(current) <= current_epsilon, 'rest',
                    np.where(current > 0, 'charging', 'discharging'))


def get_current_epsilon(data, current_epsilon=None):
    """Use an explicit threshold, recorded frame metadata, or the 0.001 A default."""
    if current_epsilon is None:
        current_epsilon = data.attrs.get('pbdp_current_epsilon', .001)
    validate_current_configuration(current_epsilon)
    return float(current_epsilon)


def continuity_breaks(data, include_direction=True):
    """Locate recording boundaries without joining gaps or repeated timestamps.

    Gap size comes only from recorded classification settings. Frames without a
    time column retain row adjacency unless a gap limit was explicitly recorded.
    Direction boundaries include transitions into and out of measured rest.
    """
    settings = data.attrs.get('pbdp_classification', {})
    if not isinstance(settings, dict):
        raise ValueError('pbdp_classification metadata must be a dictionary')
    max_gap_s = settings.get('max_gap_s')
    if max_gap_s is not None:
        _validate_threshold(max_gap_s, 'max_gap_s', positive=True)
    boundaries = np.zeros(len(data), dtype=bool)
    if len(data):
        boundaries[0] = True
    if 'Time [s]' in data.columns:
        time = _measurement_values(data, 'Time [s]')
        delta = np.diff(time)
        if (delta < 0).any():
            raise ValueError('Time [s] must be nondecreasing; split or correct data')
        boundaries[1:] |= delta == 0
        if max_gap_s is not None:
            boundaries[1:] |= delta > max_gap_s
    elif max_gap_s is not None:
        raise ValueError('Time [s] is required to enforce max_gap_s')
    if include_direction and 'Current [A]' in data.columns:
        current = _measurement_values(data, 'Current [A]')
        states = _state_labels(current, get_current_epsilon(data))
        boundaries[1:] |= states[1:] != states[:-1]
    return boundaries


def normalize_current_direction(data: pd.DataFrame, mode_column, mode_map,
                                current_epsilon=None) -> pd.DataFrame:
    """Apply a caller-declared mode convention, preserving measured current.

    Return a copy with the exact original current in ``Source current [A]``.
    Charging/discharging modes set the sign of the measured magnitude. Rest
    modes retain their measured current and must satisfy the inclusive rest
    threshold. Unknown or missing modes and conflicting rest measurements fail.
    Existing state labels are refreshed and stale phase labels are removed.
    """
    current_epsilon = get_current_epsilon(data, current_epsilon)
    validate_current_configuration(current_epsilon, mode_column, mode_map)
    if 'Source current [A]' in data.columns:
        raise ValueError('Source current [A] already exists; refusing to overwrite it')
    current = _measurement_values(data, 'Current [A]')
    if mode_column not in data.columns:
        raise ValueError(f'mode_column {mode_column!r} was not found in the data')
    try:
        modes = data[mode_column]
        mapped = modes.map(mode_map)
        unknown = np.flatnonzero((modes.isna() | mapped.isna()).to_numpy())
    except (TypeError, ValueError) as exc:
        raise ValueError('mode values must be scalar keys present in mode_map') from exc
    if unknown.size:
        raise ValueError(
            f'Unknown or missing mode at row {unknown[0]}; provide an explicit mode_map'
        )
    rest = mapped.eq('rest').to_numpy()
    conflict = np.flatnonzero(rest & (np.abs(current) > current_epsilon))
    if conflict.size:
        raise ValueError(
            f'rest mode conflicts with measured current at row {conflict[0]}; '
            'check the mode_map or current_epsilon'
        )
    normalized = current.copy()
    charging = mapped.eq('charging').to_numpy()
    discharging = mapped.eq('discharging').to_numpy()
    normalized[charging] = np.abs(current[charging])
    normalized[discharging] = -np.abs(current[discharging])
    result = data.copy(deep=True)
    result['Source current [A]'] = data['Current [A]'].copy()
    result['Current [A]'] = normalized
    if 'Battery State' in result.columns:
        result['Battery State'] = _state_labels(normalized, current_epsilon)
    result.attrs['pbdp_current_epsilon'] = current_epsilon
    result.attrs.pop('pbdp_classification', None)
    return result.drop(columns=['CCCV'], errors='ignore')


def add_state_label(data: pd.DataFrame, current_epsilon=None,
                    logger_name: str = 'pbdp_logger') -> pd.DataFrame:
    """Label current using inclusive rest boundaries at +/- current_epsilon.

    Positive current above the threshold is charging; negative current below
    its negative is discharging. Call normalize_current_direction first when
    the source convention requires an explicit vendor-mode mapping.
    """
    current_epsilon = get_current_epsilon(data, current_epsilon)
    for column in ['Current [A]', 'Voltage [V]', 'Time [s]']:
        if column not in data.columns:
            raise ValueError(f'{column}, required column not found in dataframe')
    current = _measurement_values(data, 'Current [A]')
    data['Battery State'] = _state_labels(current, current_epsilon)
    data.attrs['pbdp_current_epsilon'] = current_epsilon
    logging.getLogger(logger_name).info('Battery state labels assigned')
    return data


def _plateau_ranges(values, eligible, boundaries, tolerance):
    """Yield contiguous ranges whose full value span stays within tolerance.

    Each row is visited once. A failed row begins a new candidate interval;
    excluded rows and continuity boundaries cannot join adjacent intervals.
    """
    start = None
    low = high = 0.0
    for position in range(len(values)):
        if not eligible[position]:
            if start is not None:
                yield start, position
                start = None
            continue
        value = values[position]
        if start is not None:
            next_low, next_high = min(low, value), max(high, value)
            if boundaries[position] or next_high - next_low > tolerance:
                yield start, position
                start = None
            else:
                low, high = next_low, next_high
        if start is None:
            start, low, high = position, value, value
    if start is not None:
        yield start, len(values)


def find_cc_and_cv(
    data: pd.DataFrame,
    current_epsilon=None,
    voltage_epsilon: float = 0.001,
    time_t: float = 10.0,
    rest_t=None,
    cc_t=None,
    logger_name: str = 'pbdp_logger',
    max_gap_s=None,
) -> pd.DataFrame:
    """Label contiguous current/voltage plateaus lasting at least time_t seconds.

    A plateau's full maximum-minus-minimum span must stay within its current
    or voltage tolerance. CC takes precedence over CV. Rest and direction
    changes split intervals; equal timestamps also split them. Decreasing or
    nonfinite elapsed time is rejected. Optional max_gap_s splits gaps larger
    than the caller's declared recording interval limit; no gap size is inferred.

    Default classification has no row-count lookbacks. Explicit rest_t or cc_t
    retains the legacy CC context gate: recording start, a rest row rest_t rows
    before the candidate, or a CC row cc_t rows before it. The unspecified legacy
    argument defaults to 8 or 5 respectively. These optional gates remain
    sensitive to sampling density. New interval rules still apply in this mode.

    Labels are observational heuristics; sampling can conceal transitions or
    shorten an observed plateau below time_t. The function updates the input
    frame's Battery State and CCCV columns while preserving its index.
    """
    current_epsilon = get_current_epsilon(data, current_epsilon)
    _validate_threshold(voltage_epsilon, 'voltage_epsilon')
    _validate_threshold(time_t, 'time_t')
    if max_gap_s is not None:
        _validate_threshold(max_gap_s, 'max_gap_s', positive=True)
    legacy = rest_t is not None or cc_t is not None
    for name, value in [('rest_t', rest_t), ('cc_t', cc_t)]:
        if value is not None and (isinstance(value, (bool, np.bool_))
                                  or not isinstance(value, (int, np.integer))
                                  or value < 0):
            raise ValueError(f'{name} must be a nonnegative integer or None')
    rest_rows = 8 if rest_t is None else rest_t
    cc_rows = 5 if cc_t is None else cc_t
    current = _measurement_values(data, 'Current [A]')
    voltage = _measurement_values(data, 'Voltage [V]')
    time = _measurement_values(data, 'Time [s]')
    delta = np.diff(time)
    if (delta < 0).any():
        raise ValueError('Time [s] must be nondecreasing; split or correct recording')
    states = _state_labels(current, current_epsilon)
    active = states != 'rest'
    boundaries = np.ones(len(data), dtype=bool)
    if len(data) > 1:
        boundaries[1:] = (delta == 0) | (states[1:] != states[:-1])
        if max_gap_s is not None:
            boundaries[1:] |= delta > max_gap_s
    labels = np.full(len(data), 'N/A', dtype=object)
    for start, stop in _plateau_ranges(current, active, boundaries, current_epsilon):
        if time[stop - 1] - time[start] < time_t:
            continue
        if legacy and not (
            start == 0
            or (start >= rest_rows and states[start - rest_rows] == 'rest')
            or (start >= cc_rows and labels[start - cc_rows] == 'CC')
        ):
            continue
        labels[start:stop] = 'CC'
    for start, stop in _plateau_ranges(
        voltage, active & (labels != 'CC'), boundaries, voltage_epsilon
    ):
        if time[stop - 1] - time[start] >= time_t:
            labels[start:stop] = 'CV'
    data['Battery State'] = states
    data['CCCV'] = labels
    data.attrs['pbdp_current_epsilon'] = current_epsilon
    data.attrs['pbdp_classification'] = {
        'current_epsilon': current_epsilon,
        'voltage_epsilon': float(voltage_epsilon), 'time_t': float(time_t),
        'rest_t': None if rest_t is None else int(rest_t),
        'cc_t': None if cc_t is None else int(cc_t),
        'max_gap_s': None if max_gap_s is None else float(max_gap_s),
    }
    logging.getLogger(logger_name).info('Duration-based CC/CV labels assigned')
    return data
