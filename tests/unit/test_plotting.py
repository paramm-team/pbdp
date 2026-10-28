"""Inspect figure traces without opening a browser or notebook renderer."""
import pandas as pd
import plotly.graph_objects as go
import pytest

from pbdp.plots import display_data, plot_current_voltage_diff


@pytest.fixture
def measurements():
    return pd.DataFrame({
        'Time [s]': [0, 10, 20],
        'Current [A]': [1.0, .5, 0.0],
        'Voltage [V]': [3.5, 3.7, 4.0],
        'Temperature [degC]': [20, 21, 22],
        'Step Number': [1, 1, 2],
    })


def test_display_data_plots_available_measurements(measurements, monkeypatch):
    figures = []
    monkeypatch.setattr(go.Figure, 'show', lambda figure: figures.append(figure))
    display_data(measurements)
    assert len(figures) == 1
    expected_columns = ['Current [A]', 'Voltage [V]',
                        'Temperature [degC]', 'Step Number']
    assert [trace.name for trace in figures[0].data] == expected_columns
    for trace, column in zip(figures[0].data, expected_columns):
        assert list(trace.x) == [0, 10, 20]
        assert list(trace.y) == measurements[column].tolist()


def test_difference_plot_values_and_voltage_display_offset(measurements, monkeypatch):
    figures = []
    monkeypatch.setattr(go.Figure, 'show', lambda figure: figures.append(figure))
    plot_current_voltage_diff(measurements)
    assert len(figures) == 1
    traces = figures[0].data
    assert [trace.name for trace in traces] == [
        'Current [A]', 'Current Diff', 'Voltage [V]', 'Voltage Diff',
    ]
    assert list(traces[0].y) == [1.0, .5, 0.0]
    assert list(traces[2].y) == [3.5, 3.7, 4.0]
    assert pd.isna(traces[1].y[0])
    assert list(traces[1].y[1:]) == pytest.approx([-.5, -.5])
    # Voltage differences are intentionally offset by median voltage for display.
    assert pd.isna(traces[3].y[0])
    assert list(traces[3].y[1:]) == pytest.approx([3.9, 4.0])
    assert all(list(trace.x) == [0, 10, 20] for trace in traces)


@pytest.mark.parametrize('column', ['Current [A]', 'Voltage [V]', 'Time [s]'])
def test_difference_plot_requires_each_measurement(measurements, column, monkeypatch):
    monkeypatch.setattr(go.Figure, 'show', lambda _: pytest.fail('Unexpected display'))
    with pytest.raises(ValueError, match='column not found'):
        plot_current_voltage_diff(measurements.drop(columns=column))


@pytest.mark.parametrize('columns,message', [
    (['Time [s]'], 'None of the required columns'),
    (['Current [A]'], 'Time'),
])
def test_display_data_validates_measurements(
    measurements, columns, message, monkeypatch
):
    monkeypatch.setattr(go.Figure, 'show', lambda _: pytest.fail('Unexpected display'))
    with pytest.raises(ValueError, match=message):
        display_data(measurements[columns])
