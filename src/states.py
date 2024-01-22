import pandas as pd


def add_state_label(data: pd.DataFrame, current_epsilon: float = 0.001) -> pd.DataFrame:
    """
    Add battery state labels to the DataFrame based on current values.

    Args:
        data (pd.DataFrame): The input DataFrame containing battery data.
        current_epsilon (float, optional): Threshold to classify current
                                            values as rest, charging,
                                            discharging. Default is 0.001.

    Returns:
        pd.DataFrame: DataFrame with added "Battery State" column.

    Raises:
        ValueError: If required columns are not present in the DataFrame.
    """
    # Check if required columns are present in dataframe
    required_cols = ["Current [A]", "Voltage [V]", "Time [s]"]
    for col in required_cols:
        if col not in data.columns:
            raise ValueError(f"{col}, required column not found in dataframe")

    # Set initial state label to "unknown" for all rows
    data["Battery State"] = "unknown"

    # Define masks for each state
    rest_mask = data["Current [A]"].abs().lt(current_epsilon)
    charging_mask = data["Current [A]"].gt(current_epsilon)
    discharging_mask = data["Current [A]"].lt(-current_epsilon)

    # Assign labels for each state
    data.loc[rest_mask, "Battery State"] = "rest"
    data.loc[charging_mask, "Battery State"] = "charging"
    data.loc[discharging_mask, "Battery State"] = "discharging"

    return data


def find_cc_and_cv(
    data: pd.DataFrame,
    current_epsilon: float = 0.001,
    voltage_epsilon: float = 0.001,
    time_t: float = 10.0,
    rest_t: int = 8,
    cc_t: int = 5,
) -> pd.DataFrame:
    """
    Identify constant current (CC) and constant voltage (CV) periods in the
    battery data.

    Args:
        data (pd.DataFrame): The input DataFrame containing battery data.
        current_epsilon (float): A small value to consider as near-zero current.
        voltage_epsilon (float): A small value for near-zero voltage difference.
        time_t (float): Time threshold for considering CC and CV period.
        rest_t (int): Rows threshold for detecting a 'rest' period before a CC
                        interval.
        cc_t (int): Rows threshold for detecting a 'CC' period before a CC
                    interval.

    Returns:
        pd.DataFrame: The input DataFrame with 'CCCV' column updated with 'CC'
                        and 'CV' labels.
    """
    # Check if required columns are present in dataframe
    required_cols = ["Battery State"]
    for col in required_cols:
        if col not in data.columns:
            data = add_state_label(data)

    data["CCCV"] = "N/A"
    rest_mask = data["Current [A]"].abs().lt(current_epsilon)

    # Group rows with constant current values
    cc_intervals = data[~rest_mask].groupby(
        data["Current [A]"].diff().abs().gt(current_epsilon).cumsum()
    )

    # Loop over each constant current interval and update columns
    for _, group in cc_intervals:
        if group["Time [s]"].iloc[-1] - group["Time [s]"].iloc[0] >= time_t:
            group_indices = group.index.tolist()

            # Check if there is a 'rest' or 'CC' period before the group
            if (
                data.loc[group_indices[0] - rest_t, "Battery State"] == "rest"
                or data.loc[group_indices[0] - cc_t, "CCCV"] == "CC"
            ):
                data.loc[group_indices, "CCCV"] = "CC"

    CC_mask = data["CCCV"] == "CC"
    # Group rows with constant voltage values
    cv_intervals = data[~rest_mask].groupby(
        data[~CC_mask]["Voltage [V]"].diff().abs().gt(voltage_epsilon).cumsum()
    )

    # Loop over each constant voltage interval and update columns
    for i, group in cv_intervals:
        if group["Time [s]"].iloc[-1] - group["Time [s]"].iloc[0] >= time_t:
            group_indices = group.index.tolist()
            data.loc[group_indices, "CCCV"] = "CV"

    return data
