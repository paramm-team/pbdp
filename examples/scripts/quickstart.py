"""Run a synthetic import, classification, segmentation, and CSV round trip.

From an environment with this checkout installed, run:
    python examples/scripts/quickstart.py --output-dir /tmp/pbdp-quickstart
The output directory must not exist. No experimental data is downloaded.
"""
import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from pbdp import Parser
from pbdp.save import save_file
from pbdp.segment import segment_data
from pbdp.states import add_state_label, find_cc_and_cv


def run_quickstart(output_dir: Path) -> dict:
    """Create and verify an illustrative trace inside a new output directory."""
    output_dir = Path(output_dir).resolve()
    # Refuse to overwrite an existing directory, including a previous run.
    output_dir.mkdir(parents=True, exist_ok=False)
    source = output_dir / "synthetic_cycle.csv"
    times = list(range(0, 55, 5))
    currents_ma = [1000, 1000, 1000, 1000, 700, 400, 200, 0, 0, -500, -500]
    voltages = [3.5, 3.7, 3.9, 4.2, 4.2, 4.2, 4.2, 4.1, 4.1, 4.0, 3.9]
    # Trapezoidal integration gives signed accumulated charge in mAh.
    charge_mah = [0.0]
    for previous, current in zip(currents_ma, currents_ma[1:]):
        charge_mah.append(charge_mah[-1] + (previous + current) / 2 * 5 / 3600)
    with source.open("w", encoding="utf-8", newline="") as stream:
        stream.write("Synthetic demonstration; not experimental data\n")
        stream.write("Technique started on : 01/01/2020 00:00:00\n")
        writer = csv.writer(stream)
        writer.writerow(["time/s", "<I>/mA", "Ecell/V", "(Q-Qo)/mA.h"])
        writer.writerows(zip(times, currents_ma, voltages, charge_mah))
    original = source.read_bytes()

    # Import without writing output until units and classifications are checked.
    data = Parser().data_importer(source, save_option="none")
    np.testing.assert_allclose(data["Time [s]"], times)
    np.testing.assert_allclose(
        data["Current [A]"], [1, 1, 1, 1, .7, .4, .2, 0, 0, -.5, -.5]
    )
    np.testing.assert_allclose(data["Voltage [V]"], voltages)
    np.testing.assert_allclose(data["AmpHrs [Ah]"].iloc[-1], .005625)

    data = find_cc_and_cv(add_state_label(data))
    expected_states = ["charging"] * 7 + ["rest"] * 2 + ["discharging"] * 2
    if data["Battery State"].tolist() != expected_states:
        raise AssertionError("Unexpected charging/rest/discharging labels")
    if data["CCCV"].tolist() != ["CC"] * 4 + ["CV"] * 3 + ["N/A"] * 4:
        raise AssertionError("Unexpected constant-current/constant-voltage labels")
    periods = segment_data(data, ["cccv"])
    if len(periods) != 1:
        raise AssertionError("Expected one contiguous CC-to-CV charging period")
    assert_frame_equal(periods[0], data.iloc[:7])

    cleaned = save_file(data, "csv", source)
    cccv = save_file(periods[0], "csv", output_dir / "synthetic_cccv.csv")
    # CSV has no type metadata: parse timestamps and preserve the literal N/A.
    for path, expected in [(cleaned, data), (cccv, periods[0])]:
        reloaded = pd.read_csv(
            path, parse_dates=["Absolute Time [s]"], keep_default_na=False
        )
        assert_frame_equal(reloaded, expected.reset_index(drop=True))
    if source.read_bytes() != original:
        raise AssertionError("Import changed the raw input")

    return {"source": source, "cleaned": cleaned, "cccv": cccv}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", required=True, type=Path,
        help="new directory for the synthetic input and verified CSV exports",
    )
    args = parser.parse_args()
    try:
        outputs = run_quickstart(args.output_dir)
    except FileExistsError:
        parser.error("--output-dir already exists; choose a new directory")
    print("Verified 11 samples, A/Ah units, three states, and one CC/CV period.")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
