import numpy as np
import pandas as pd
from .states import find_cc_and_cv
import logging


def group_by_input_state(data: pd.DataFrame, input_str: str,
                         logger_name: str = 'pbdp_logger') -> list:
    """
    Group the data based on a specific column value.

    Args:
        data (pd.DataFrame): The input DataFrame containing battery data.
        input_str (str): Column name to group the data by.

    Returns:
        list: List of DataFrames, each representing a group.
    """
    logger = logging.getLogger(logger_name)
    if input_str == "battery":
        # Group the DataFrame by consecutive values in "Battery State" column
        groups = (data["Battery State"] != data["Battery State"].shift()).cumsum()
        grouped_df = data.groupby(groups)
        group_list = [group for _, group in grouped_df]
        logger.info("Data grouped by Battery State")
    elif input_str == "CCCV":
        # Group the DataFrame by consecutive values in "CCCV" column
        groups = (data["CCCV"] != data["CCCV"].shift()).cumsum()
        grouped_df = data.groupby(groups)
        group_list = [group for _, group in grouped_df]
        logger.info("Data grouped by CCCV")
    else:
        # If input_str is not recognized, keep the original DataFrame
        group_list = data
        logger.warning(f"Input string not recognized: {input_str}, no grouping")

    return group_list


def find_periods(
    data: pd.DataFrame,
    first: str,
    second: str = None,
    curr: float = None,
    volt: float = None,
    pulse_t: int = 5,
    logger_name: str = 'pbdp_logger'
) -> list:
    """
    Find periods based on specified input states.

    Args:
        data (pd.DataFrame): The input DataFrame containing battery data.
        first (str): First input state to identify periods.
        second (str, optional): Second input state to identify periods.
                                Defaults to None.
        pulse_t (int): Rows threshold for detecting a 'pulse' period before not
                        a CV interval.

    Returns:
        list: List of DataFrames representing the identified periods.
    """
    logger = logging.getLogger(logger_name)
    # Identify the start and end of first input periods
    if first in ["rest", "charging", "discharging"]:
        logger.info(f"First input1: {first}")
        if curr is None or first == "rest":
            first_mask = data["Battery State"] == first
        else:
            first_mask = (data["Battery State"] == first) & (
                data["Current [A]"].round(2) == curr
            )
    elif first in ["cc", "cv"]:
        logger.info(f"First input2: {first}")
        if first == "cc":
            if curr is None:
                first_mask = data["CCCV"] == "CC"
            else:
                first_mask = (data["CCCV"] == "CC") & (
                    data["Current [A]"].round(2) == curr
                )
        elif first == "cv":
            if volt is None:
                first_mask = data["CCCV"] == "CV"
            else:
                first_mask = (data["CCCV"] == "CV") & (
                    data["Voltage [V]"].round(2) == volt
                )
    elif first == "cccv":
        logger.info(f"First input3: {first}")
        if curr is None:
            first_mask = (
                (data["CCCV"] == "CC") & (data["Battery State"] == "charging")
            )
        else:
            first_mask = (
                (data["CCCV"] == "CC")
                & (data["Battery State"] == "charging")
                & (data["Current [A]"].round(2) == curr)
            )
    elif first == "pulse":
        if curr is None:
            first_mask = data["CCCV"] == "CC"
        else:
            first_mask = (data["CCCV"] == "CC") & (data["Current [A]"].round(2) == curr)
    else:
        return "None provided"
    logger.info(f"First mask: {first_mask}")

    # Adjacency is defined by row position, never by index arithmetic.
    start_indices_first = np.flatnonzero(
        (first_mask & ~first_mask.shift(1, fill_value=False)).fillna(False)
    )
    end_indices_first = np.flatnonzero(
        (first_mask & ~first_mask.shift(-1, fill_value=False)).fillna(False)
    )
    logger.info(f"Start indices: {start_indices_first}")
    logger.info(f"End indices: {end_indices_first}")

    if first == "pulse":
        pulse_indices = [
            (start, end)
            for start, end in zip(start_indices_first, end_indices_first)
            if data["Time [s]"].iloc[end] - data["Time [s]"].iloc[start] < 360
        ]
        # Combine adjusted start and end indices to get the ranges of pulses
        pulse_periods = []
        for pulse_start, pulse_end in pulse_indices:
            following = data["CCCV"].iloc[pulse_end + 1:pulse_end + pulse_t + 1]
            if not following.eq("CV").any():
                pulse_periods.append(data.iloc[pulse_start:pulse_end + 1])
        return pulse_periods

    first_indices = list(zip(start_indices_first, end_indices_first))
    logger.info(f"First indices: {first_indices}")

    if first == "cccv":
        if volt is None:
            second_mask = (data["CCCV"] == "CV") & (data["Battery State"] == "charging")
        else:
            second_mask = (
                (data["CCCV"] == "CV")
                & (data["Battery State"] == "charging")
                & (data["Voltage [V]"].round(2) == volt)
            )
    if second in ["rest", "charging", "discharging"]:
        logger.info(f"Second input1: {second}")
        if volt is None or second == "rest":
            second_mask = data["Battery State"] == second
        else:
            second_mask = (data["Battery State"] == second) & (
                data["Current [A]"].round(2) == volt
            )
    elif second in ["cc", "cv"]:
        logger.info(f"Second input2: {second}")
        if second == "cc":
            if curr is None:
                second_mask = data["CCCV"] == "CC"
            else:
                second_mask = (data["CCCV"] == "CC") & (
                    data["Current [A]"].round(2) == curr
                )
        elif second == "cv":
            logger.info(f"Second input2: {second}")
            if volt is None:
                second_mask = data["CCCV"] == "CV"
            else:
                second_mask = (data["CCCV"] == "CV") & (
                    data["Voltage [V]"].round(2) == volt
                )
    # Identify the start and end of second input periods
    start_indices_second = np.flatnonzero(
        (second_mask & ~second_mask.shift(1, fill_value=False)).fillna(False)
    )
    end_indices_second = np.flatnonzero(
        (second_mask & ~second_mask.shift(-1, fill_value=False)).fillna(False)
    )

    second_indices = list(zip(start_indices_second, end_indices_second))
    logger.info(f"Second indices: {second_indices}")

    # Combine adjusted start and end indices to get the ranges of the periods
    periods = []
    for first_start, first_end in first_indices:
        for second_start, second_end in second_indices:
            if first_end == second_start - 1:
                periods.append(data.iloc[first_start:second_end + 1])

    logger.info(f"Periods: {periods}")
    return periods


def segment_data(data: pd.DataFrame, requests: list, reset: bool = False,
                 logger_name: str = 'pbdp_logger') -> list:
    """
    Segments the battery data based on the provided requests.

    Args:
        data (pd.DataFrame): The input DataFrame containing battery data.
        requests (list): A list of strings specifying the segments to be
                        extracted.

    Returns:
        list: A list of filtered DataFrames representing the segmented data.

    Notes:
        Power requests select contiguous non-rest intervals lasting at least
        10 seconds, with consecutive power changes no greater than 0.01 W.
        An optional signed wattage filters power rounded to two decimal places.
        Combined requests accept two unqualified states, or a rest period
        followed by one state with a single current/voltage constraint. Use
        ``cccv`` for constrained CC/CV pairs.
    """
    logger = logging.getLogger(logger_name)
    normalized_requests = []
    for request in requests:
        if not isinstance(request, str) or not request.strip():
            raise ValueError("Each segment request must be a non-empty string")
        normalized_requests.append(" ".join(request.split()))
    requests = normalized_requests
    # Check if request can be performed
    required_cols = ["Current [A]", "Voltage [V]", "Time [s]"]
    missing_cols = [col for col in required_cols if col not in data.columns]
    if missing_cols:
        missing_col_names = ", ".join(missing_cols)
        logger.error(f"Action cannot be performed because {missing_col_names},\
                      required columns not found in dataframe")
        raise ValueError(
            f"Action cannot be performed because {missing_col_names}, "
            "required columns not found in dataframe"
        )

    # Check if required columns are present in dataframe
    required_cols = ["CCCV", "Battery State"]
    for col in required_cols:
        if col not in data.columns:
            data = find_cc_and_cv(data)

    logger.info('Required columns found in dataframe')

    filtered_df_list = []

    # Iterate over each request in the list for the data segment
    for sub_request in requests:
        # Handle combined requests
        if "," in sub_request:
            curr = volt = None
            parts = [part.strip().split() for part in sub_request.split(",")]
            states = {"rest", "charging", "discharging", "cc", "cv"}
            error = (f"Unsupported combined request: {sub_request!r}. Use two "
                     "states, or 'rest, cc 1A' / 'rest, cv 4.2V'; use cccv "
                     "for constrained CC/CV pairs.")
            if (len(parts) != 2 or len(parts[0]) != 1
                    or not 1 <= len(parts[1]) <= 2
                    or parts[0][0] not in states or parts[1][0] not in states):
                raise ValueError(error)
            first_request, second_request = parts[0][0], parts[1][0]
            if len(parts[1]) == 2:
                units = {"cc": "A", "cv": "V",
                         "charging": "A", "discharging": "A"}
                parameter = parts[1][1]
                if (first_request != "rest" or second_request not in units
                        or not parameter.endswith(units[second_request])):
                    raise ValueError(error)
                try:
                    value = float(parameter[:-1])
                except ValueError as exc:
                    raise ValueError(error) from exc
                if not np.isfinite(value):
                    raise ValueError(error)
                if second_request == "cc":
                    curr = value
                else:
                    # find_periods uses volt for a second-state constraint,
                    # including the current of charging/discharging states.
                    volt = value
            filtered_df_list.extend(
                find_periods(data, first_request, second_request, curr, volt)
            )
            logger.info(f"Handled Sub-request: {sub_request}")
            continue

        # Match whole request types: discharging must not match charging.
        elif sub_request.split()[0] == "rest":
            df_list = group_by_input_state(data, "battery")
            filtered_df_list.extend(
                [group for group in df_list if "rest" in group["Battery State"].values]
            )
            logger.info(f"Handled Sub-request: {sub_request}")
        elif sub_request.split()[0] == "charging":
            # Segment based on charging state
            df_list = group_by_input_state(data, "battery")
            if "A" in sub_request:
                # Segment based on charging current
                chg_A = abs(float(sub_request.split("A")[0].split(" ")[1]))
                filtered_df_list.extend(
                    [
                        group[group["Current [A]"].round(2) == chg_A]
                        for group in df_list
                        if ("charging" in group["Battery State"].values)
                        and (group["Current [A]"].round(2) == chg_A).any()
                    ]
                )
            else:
                # Segment all charging periods
                filtered_df_list.extend(
                    [
                        group
                        for group in df_list
                        if "charging" in group["Battery State"].values
                    ]
                )
            logger.info(f"Handled Sub-request: {sub_request}")
        elif sub_request.split()[0] in ["dischg", "discharging"]:
            # Segment based on discharging state
            df_list = group_by_input_state(data, "battery")
            if "A" in sub_request:
                # Segment based on discharging current
                dchg_A = -abs(float(sub_request.split("A")[0].split(" ")[1]))
                filtered_df_list.extend(
                    [
                        group[group["Current [A]"].round(2) == dchg_A]
                        for group in df_list
                        if ("discharging" in group["Battery State"].values)
                        and (group["Current [A]"].round(2) == dchg_A).any()
                    ]
                )
            else:
                # Segment all discharging periods
                filtered_df_list.extend(
                    [
                        group
                        for group in df_list
                        if "discharging" in group["Battery State"].values
                    ]
                )
            logger.info(f"Handled Sub-request: {sub_request}")
        elif sub_request.split()[0] == "cc":
            # Segment based on constant current state
            df_list = group_by_input_state(data, "CCCV")
            if "A" in sub_request:
                # Segment based on constant current value
                CC_A = float(sub_request.split("A")[0].split(" ")[1])
                filtered_df_list.extend(
                    [
                        group[group["Current [A]"].round(2) == CC_A]
                        for group in df_list
                        if ("CC" in group["CCCV"].values)
                        and (group["Current [A]"].round(2) == CC_A).any()
                    ]
                )
            else:
                # Segment all constant current periods
                filtered_df_list.extend(
                    [group for group in df_list if "CC" in group["CCCV"].values]
                )
            logger.info(f"Handled Sub-request: {sub_request}")
        elif sub_request.split()[0] == "cv":
            # Segment based on constant voltage state
            df_list = group_by_input_state(data, "CCCV")
            if "V" in sub_request:
                CV_V = float(sub_request.split("V")[0].split(" ")[1])
                filtered_df_list.extend(
                    [
                        group[group["Voltage [V]"].round(2) == CV_V]
                        for group in df_list
                        if ("CV" in group["CCCV"].values)
                        and (group["Voltage [V]"].round(2) == CV_V).any()
                    ]
                )
            else:
                # Segment all constant voltage periods
                filtered_df_list.extend(
                    [group for group in df_list if "CV" in group["CCCV"].values]
                )
            logger.info(f"Handled Sub-request: {sub_request}")
        elif sub_request.split()[0] == "cccv":
            # Segment based on cc values
            cccv_A = cccv_V = None
            if "A" in sub_request:
                cccv_A = float(sub_request.split("A")[0].split(" ")[1])
            # Segment based on cv values
            if "V" in sub_request:
                if "A" in sub_request:
                    cccv_V = float(sub_request.split("V")[0].split(" ")[2])
                else:
                    cccv_V = float(sub_request.split("V")[0].split(" ")[1])
            filtered_df_list.extend(find_periods(data, "cccv", None, cccv_A, cccv_V))
            logger.info(f"Handled Sub-request: {sub_request}")
        elif sub_request.split()[0] == "pulse":
            # Segment based on pulse values
            if "A" in sub_request:
                pulse_A = float(sub_request.split("A")[0].split(" ")[1])
                filtered_df_list.extend(find_periods(data, "pulse", None, pulse_A))
            else:
                # Segment all pulse periods
                filtered_df_list.extend(find_periods(data, "pulse"))
            logger.info(f"Handled Sub-request: {sub_request}")
        # Segment based on step number
        elif sub_request.split()[0] == "step":
            if ":" in sub_request:
                start_step, end_step = map(
                    float, sub_request.split("step")[1].split(':')
                )
                if end_step < start_step:
                    start_step, end_step = end_step, start_step
                last_step = data["Step Number"].max()
                if end_step > last_step and start_step > last_step:
                    filtered_df_list.append(data[data["Step Number"] == last_step])
                elif end_step > last_step:
                    filtered_df_list.append(
                        data[data["Step Number"].between(start_step, last_step)]
                    )
                else:
                    filtered_df_list.append(
                        data[data["Step Number"].between(start_step, end_step)]
                    )
            else:
                filtered_df_list.append(data)
            logger.info(f"Handled Sub-request: {sub_request}")
        # Segment based on time
        elif sub_request.split()[0] == "time":
            if "/" in sub_request:
                start_time, stop_time = map(
                    float, sub_request.split("time")[1].split('/')
                )
                end_time = data["Time [s]"].max()
                if start_time > stop_time:
                    start_time, stop_time = stop_time, start_time
                if stop_time > end_time and start_time > end_time:
                    filtered_df_list.append(
                        data[data["Time [s]"] == end_time]
                    )
                elif stop_time > end_time:
                    filtered_df_list.append(
                        data[data["Time [s]"].between(start_time, end_time)]
                    )
                elif start_time == stop_time:
                    filtered_df_list.append(
                        data[data["Time [s]"].between(start_time, start_time + 1)]
                    )
                else:
                    filtered_df_list.append(
                        data[data["Time [s]"].between(start_time, stop_time)]
                    )
            else:
                filtered_df_list.append(data)
            logger.info(f"Handled Sub-request: {sub_request}")
        elif sub_request.split()[0] == "power":
            parts = sub_request.split()
            target = None
            error = f"Invalid power request: {sub_request!r}; use power or power 4W"
            if len(parts) != 1:
                if len(parts) != 2 or not parts[1].endswith("W"):
                    raise ValueError(error)
                try:
                    target = float(parts[1][:-1])
                except ValueError as exc:
                    raise ValueError(error) from exc
                if not np.isfinite(target):
                    raise ValueError(error)
            power = data["Voltage [V]"] * data["Current [A]"]
            power_data = data.assign(**{"Power [W]": power})
            active = data["Current [A]"].abs().ge(0.001) & np.isfinite(power)
            if target is not None:
                active &= power.round(2).eq(target)
            # Rest rows and excluded values break runs even when neighboring
            # accepted values happen to have the same power. Group positionally
            # so repeated source index labels remain valid.
            groups = (power.diff().abs().gt(0.01)
                      | active.ne(active.shift(fill_value=False))).cumsum()
            selected = np.flatnonzero(active.to_numpy())
            intervals = power_data.iloc[selected].groupby(
                groups.to_numpy()[selected], sort=False
            )
            for _, group in intervals:
                duration = group["Time [s]"].iloc[-1] - group["Time [s]"].iloc[0]
                if duration >= 10:
                    filtered_df_list.append(group)
            logger.info(f"Handled Sub-request: {sub_request}")

        else:
            raise ValueError(f"Unknown segment request: {sub_request!r}")

    if reset is True:
        logger.info("Resetting time")
        logger.info("Filtered the list")
        return reset_time(filtered_df_list)
    else:
        logger.info("Filtered the list")
        return filtered_df_list


def reset_time(data: list, logger_name: str = 'pbdp_logger') -> pd.DataFrame:
    """
    Resets the 'Time [s]' column in each DataFrame in a list to start from 0,
    while preserving the original time in a new column 'Original Time [s]'.

    Args:
        data (list): List of pandas DataFrames. Each DataFrame should have a 'Time [s]'
                     column.

    Returns:
        list: List of the same DataFrames with the 'Time [s]' column reset and
              'Original Time [s]' column added in each DataFrame.
    """
    logger = logging.getLogger(logger_name)
    logger.info("Resetting time")

    # Reset the Time column to start from 0 and keep the original one seperate
    def map_fun(df):
        return df.assign(
            **{
                "Original Time [s]": df["Time [s]"],
                "Time [s]": df["Time [s]"] - (0 if df.empty else df["Time [s]"].iloc[0])
            }
        )
    data = list(map(map_fun, data))

    return data


def find_rest(data: pd.DataFrame,
              segments: list,
              current_epsilon: float = 0.001,
              logger_name: str = 'pbdp_logger'
              ) -> list:
    """
    Finds and includes rest periods adjacent to each segment in a list based on a
    current threshold.
    This function processes each segment in the provided list and identifies rest
    periods immediately
    before and after the segment.

    Args:
        data (pd.DataFrame): The input DataFrame containing battery data with a
                             'Current [A]' column.
        segments (list): List of DataFrames, each representing a segment to process.
        current_epsilon (float): Threshold for defining a rest period based on the
                                 current. Defaults to 0.001.

    Returns:
        list: List of DataFrames, each including the original segment and its adjacent
              rest periods.
    """
    logger = logging.getLogger(logger_name)

    if not data.index.is_unique:
        raise ValueError("find_rest requires unique source index labels")
    rest = data["Current [A]"].abs().lt(current_epsilon).to_numpy()

    def process_segment(segment: pd.DataFrame):
        if segment.empty:
            return segment.copy()
        positions = data.index.get_indexer(segment.index)
        if (positions < 0).any() or (np.diff(positions) != 1).any():
            raise ValueError("Each segment must be consecutive rows of the source")
        start, end = positions[0], positions[-1]
        # Extend through adjacent rest rows only; never cross another activity.
        while start > 0 and rest[start - 1]:
            start -= 1
        while end + 1 < len(data) and rest[end + 1]:
            end += 1
        return data.iloc[start:end + 1]

    # Process each segment in the list
    updated_segments = [process_segment(segment) for segment in segments]

    logger.info("Rest periods found")
    return updated_segments
