import math
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_current_voltage_diff(data: pd.DataFrame) -> None:
    """
    Plot the current and voltage differences over time.

    Args:
        data (pd.DataFrame): The input DataFrame containing battery data.

    Raises:
        ValueError: If required columns are not present in the DataFrame.
    """
    # Check if required columns are present in dataframe
    required_cols = ["Current [A]", "Voltage [V]", "Time [s]"]
    for col in required_cols:
        if col not in data.columns:
            raise ValueError(f"{col} column not found in dataframe")

    # Compute difference between consecutive elements for Current and Voltage
    diff_current = data["Current [A]"].diff()
    diff_voltage = data["Voltage [V]"].diff() + data["Voltage [V]"].median()

    # Create a 1x2 grid of subplots
    fig = make_subplots(rows=1, cols=2)

    # Plot current on time with diff layered on top
    fig.add_trace(
        go.Scatter(
            x=data["Time [s]"],
            y=data["Current [A]"],
            mode="lines",
            name="Current [A]",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=data["Time [s]"],
            y=diff_current,
            mode="lines",
            name="Current Diff",
        ),
        row=1,
        col=1,
    )
    # Set axis labels and title for the entire figure
    fig.update_yaxes(title_text="Current [A]", row=1, col=1)

    # Plot voltage on time with diff layered on top
    fig.add_trace(
        go.Scatter(
            x=data["Time [s]"],
            y=data["Voltage [V]"],
            mode="lines",
            name="Voltage [V]",
        ),
        row=1,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=data["Time [s]"],
            y=diff_voltage,
            mode="lines",
            name="Voltage Diff",
        ),
        row=1,
        col=2,
    )
    # Set axis labels and title for the entire figure
    fig.update_yaxes(title_text="Voltage [V]", row=1, col=2)

    # Update the layout of the subplots for synchronization
    fig.update_xaxes(matches="x")

    # Add a common x-axis label, title and set dimensions
    fig.update_xaxes(title_text="Time [s]")
    fig.update_layout(title="Current and Voltage Diff", height=400, width=1200)

    # Show the plot
    fig.show()


def display_data(data: pd.DataFrame) -> None:
    """
    Display a summary of the data and plot required columns.

    Args:
        data (pd.DataFrame): The input DataFrame containing battery data.

    Raises:
        ValueError: If none of the required columns are present.
                    If the "Time [s]" column is not present in the DataFrame
    """
    # Display the first 10 rows of the DataFrame
    print(data.head(10))

    # Check if at least one required column is present
    required_cols = [
        "Current [A]",
        "Voltage [V]",
        "Temperature [degC]",
        "Step Number",
    ]
    if not any(col in data.columns for col in required_cols):
        raise ValueError("None of the required columns are present")

    # Check if the time column is present
    if "Time [s]" not in data.columns:
        raise ValueError("Time [s] column is not present in the dataframe")

    # Remove missing columns from required_cols
    required_cols = [col for col in required_cols if col in data.columns]

    # Create a grid of subplots
    n_cols = len(required_cols) % 3 + math.floor(len(required_cols) / 3)
    n_rows = math.ceil(len(required_cols) / n_cols)
    fig = make_subplots(rows=n_rows, cols=n_cols)

    # Plot the data on each subplot
    for i, col in enumerate(required_cols):
        if col in data.columns:
            col_idx = i % n_cols + 1
            row_idx = i // n_cols + 1

            # Add traces to the subplots
            fig.add_trace(
                go.Scatter(
                    x=data["Time [s]"],
                    y=data[col],
                    mode="lines",
                    name=col,
                ),
                row=row_idx,
                col=col_idx,
            )
            # Set axis labels and title for the entire figure
            fig.update_yaxes(title_text=col, row=row_idx, col=col_idx)

    # Update the layout of the subplots for synchronization
    fig.update_xaxes(matches="x")

    # Add a common x-axis label, title and set dimensions
    fig.update_xaxes(title_text="Time [s]")
    fig.update_layout(title="Battery Data", height=800, width=1200)

    # Show the plot
    fig.show()
