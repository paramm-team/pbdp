import pandas as pd
from modules.states import find_cc_and_cv


def group_by_input_state(data: pd.DataFrame, input_str: str) -> list:
    """
    Group the data based on a specific column value.

    Args:
        data (pd.DataFrame): The input DataFrame containing battery data.
        input_str (str): Column name to group the data by.

    Returns:
        list: List of DataFrames, each representing a group.
    """
    if input_str == "battery":
        # Group the DataFrame by consecutive values in "Battery State" column
        groups = (
            data["Battery State"] != data["Battery State"].shift()
            ).cumsum()
        grouped_df = data.groupby(groups)
        group_list = [group for _, group in grouped_df]
    elif input_str == "CCCV":
        # Group the DataFrame by consecutive values in "CCCV" column
        groups = (data["CCCV"] != data["CCCV"].shift()).cumsum()
        grouped_df = data.groupby(groups)
        group_list = [group for _, group in grouped_df]
    else:
        # If input_str is not recognized, keep the original DataFrame
        group_list = data

    return group_list


def find_periods(
        data: pd.DataFrame,
        first: str,
        second: str = None,
        curr: float = None,
        volt: float = None,
        pulse_t: int = 5
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
    print(first, second, curr, volt)
    # Identify the start and end of first input periods
    if first in ["rest", "charging", "discharging"]:
        if curr is None:
            first_mask = data["Battery State"] == first
        else:
            first_mask = (
                (data["Battery State"] == first) &
                (data["Current [A]"].round(2) == curr)
            )
    elif first in ["cc", "cv"]:
        if first == "cc":
            if curr is None:
                first_mask = data["CCCV"] == "CC"
            else:
                first_mask = (
                    (data["CCCV"] == "CC") &
                    (data["Current [A]"].round(2) == curr)
                )
        elif first == "cv":
            if volt is None:
                first_mask = data["CCCV"] == "CV"
            else:
                first_mask = (
                    (data["CCCV"] == "CV") &
                    (data["Voltage Full [V]"].round(2) == volt)
                )
    elif first == "cccv":
        if curr is None:
            first_mask = (
                (data["CCCV"] == "CC") &
                (data["Battery State"] == "charging")
            )
        else:
            first_mask = (
                (data["CCCV"] == "CC") &
                (data["Battery State"] == "charging") &
                (data["Current [A]"].round(2) == curr)
            )
    elif first == "pulse":
        if curr is None:
            first_mask = (data["CCCV"] == "CC")
        else:
            first_mask = (
                (data["CCCV"] == "CC") &
                (data["Current [A]"].round(2) == curr)
            )
    else:
        return "None provided"

    start_indices_first = data.index[
        (first_mask) & (~first_mask.shift(1).fillna(False))
    ]
    end_indices_first = data.index[
        (first_mask) & (~first_mask.shift(-1).fillna(False))
    ]

    if first == "pulse":
        pulse_indices = [
            (start, end)
            for start, end in zip(start_indices_first, end_indices_first)
            if data.loc[end, "Time [s]"] - data.loc[start, "Time [s]"] < 360
        ]
        # Combine adjusted start and end indices to get the ranges of pulses
        pulse_periods = []
        for pulse_start, pulse_end in pulse_indices:
            if data["CCCV"].iloc[pulse_end + pulse_t] != "CV":
                pulse_periods.append(data.loc[pulse_start:pulse_end])
        return pulse_periods

    first_indices = list(zip(start_indices_first, end_indices_first))

    if first == "cccv":
        if volt is None:
            second_mask = (
                (data["CCCV"] == "CV") &
                (data["Battery State"] == "charging")
            )
        else:
            second_mask = (
                (data["CCCV"] == "CV")
                & (data["Battery State"] == "charging")
                & (data["Voltage [V]"].round(2) == volt)
            )
    if second in ["rest", "charging", "discharging"]:
        if volt is None:
            second_mask = data["Battery State"] == second
        else:
            second_mask = (
                (data["Battery State"] == second) &
                (data["Current [A]"].round(2) == volt)
            )
    elif second in ["cc", "cv"]:
        if second == "cc":
            if curr is None:
                second_mask = data["CCCV"] == "CC"
            else:
                second_mask = (
                    (data["CCCV"] == "CC") &
                    (data["Current [A]"].round(2) == curr)
                )
        elif second == "cv":
            if volt is None:
                second_mask = data["CCCV"] == "CV"
            else:
                second_mask = (data["CCCV"] == "CV") & (
                    data["Voltage [V]"].round(2) == volt
                )
    # Identify the start and end of second input periods
    start_indices_second = data.index[
        (second_mask) & (~second_mask.shift(1).fillna(False))
    ]
    end_indices_second = data.index[
        (second_mask) & (~second_mask.shift(-1).fillna(False))
    ]

    second_indices = list(zip(start_indices_second, end_indices_second))

    # Combine adjusted start and end indices to get the ranges of the periods
    periods = []
    for first_start, first_end in first_indices:
        for second_start, second_end in second_indices:
            if first_end == second_start - 1:
                periods.append(data.loc[first_start:second_end])

    return periods


def segment_data(data: pd.DataFrame, requests: list) -> list:
    """
    Segments the battery data based on the provided requests.

    Args:
        data (pd.DataFrame): The input DataFrame containing battery data.
        requests (list): A list of strings specifying the segments to be
                        extracted.

    Returns:
        list: A list of filtered DataFrames representing the segmented data.
    """
    # Check if request can be performed
    required_cols = ["Current [A]", "Voltage [V]", "Time [s]"]
    missing_cols = [col for col in required_cols if col not in data.columns]
    if missing_cols:
        missing_col_names = ", ".join(missing_cols)
        raise ValueError(
            f"Action cannot be performed because {missing_col_names}, "
            "required columns not found in dataframe"
        )

    # Check if required columns are present in dataframe
    required_cols = ["CCCV", "Battery State"]
    for col in required_cols:
        if col not in data.columns:
            data = find_cc_and_cv(data)

    filtered_df_list = []

    # Iterate over each request in the list for the data segment
    for sub_request in requests:
        # Handle combined requests
        if "," in sub_request:
            curr = volt = None
            first_request, second_request = sub_request.split(", ")
            second_request = second_request.split(" ")[0]
            if "A" in sub_request:
                curr = float(sub_request.split("A")[0].split(" ")[2])
            if "V" in sub_request:
                if "A" in sub_request:
                    volt = float(sub_request.split("V")[0].split(" ")[3])
                else:
                    volt = float(sub_request.split("V")[0].split(" ")[2])
            if "amp" in sub_request:
                if "A" in sub_request:
                    volt = float(sub_request.split("amp")[0].split(" ")[3])
                else:
                    volt = float(sub_request.split("amp")[0].split(" ")[2])
            filtered_df_list.extend(
                find_periods(data, first_request, second_request, curr, volt)
                )
            continue

        # Process each sub-request
        elif "rest" in sub_request:
            df_list = group_by_input_state(data, "battery")
            filtered_df_list.extend(
                [group for group in df_list
                    if "rest" in group["Battery State"].values]
            )
        elif "charging" in sub_request:
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
        elif "dischg" in sub_request:
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
        elif "cc" in sub_request:
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
                filtered_df_list.extend([
                    group for group in df_list if "CC" in group["CCCV"].values
                    ])
        elif "cv" in sub_request:
            # Segment based on constant voltage state
            df_list = group_by_input_state("CCCV")
            if "V" in sub_request:
                CV_V = float(sub_request.split("V")[0].split(" ")[1])
                filtered_df_list.extend(
                    [
                        group[group["Voltage Full [V]"].round(2) == CV_V]
                        for group in df_list
                        if ("CV" in group["CCCV"].values)
                        and (group["Voltage [V]"].round(2) == CV_V).any()
                    ]
                )
            else:
                # Segment all constant voltage periods
                filtered_df_list.extend([
                    group for group in df_list if "CV" in group["CCCV"].values
                ])
        elif "cccv" in sub_request:
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
            filtered_df_list.extend(
                find_periods(data, "cccv", None, cccv_A, cccv_V)
            )
        elif "pulse" in sub_request:
            # Segment based on pulse values
            if "A" in sub_request:
                pulse_A = float(sub_request.split("A")[0].split(" ")[1])
                filtered_df_list.extend(
                    find_periods(data, "pulse", None, pulse_A)
                )
            else:
                # Segment all pulse periods
                filtered_df_list.extend(find_periods(data, "pulse"))
        # Segment based on step number
        elif "step" in sub_request:
            if ":" in sub_request:
                step = int(sub_request.split(":")[1])
                last_step = data["Step Number"].max()
                if step > last_step:
                    filtered_df_list.extend(
                        data[data["Step Number"] == last_step]
                        )
                else:
                    filtered_df_list.extend(data[data["Step Number"] == step])
            else:
                filtered_df_list.extend(data)
        # Segment based on time
        elif "time" in sub_request:
            if "/" in sub_request:
                start_time = float(sub_request.split("time")[1].split("/")[0])
                stop_time = float(sub_request.split("/")[1])
                end_time = data["Time [s]"].max()
                if stop_time > end_time:
                    filtered_df_list.extend(data[data["Time [s]"] == end_time])
                else:
                    filtered_df_list.extend(
                        data[
                            (data["Time [s]"] >= start_time)
                            & (data["Time [s]"] <= stop_time)
                        ]
                    )
            else:
                filtered_df_list.extend(data)
        elif "power" in sub_request:
            # Segment based on power
            data["Power [W]"] = data["Voltage [V]"] * data["Current [A]"]
            # df_list = group_by_input_state(data, "Power")
            df_list = data[~data["Current [A]"].abs().lt(0.001)].groupby(
                    data["Power [W]"].diff().abs().gt(0.01).cumsum())
            if "W" in sub_request:
                # Segment based on charging current
                pwr_W = float(sub_request.split("W")[0].split(" ")[1])
                for _, group in df_list:
                    filtered_group = group[
                        group["Power [W]"].round(2) == pwr_W
                    ]
                    if not filtered_group.empty and (
                        filtered_group["Time [s]"].iloc[-1] -
                        filtered_group["Time [s]"].iloc[0] >= 10
                    ):
                        filtered_df_list.append(filtered_group)
            else:
                # Segment all power periods
                filtered_df_list.append(data)

    return filtered_df_list


def find_rest(data: pd.DataFrame, period: pd.DataFrame) -> pd.DataFrame:
    return 0
