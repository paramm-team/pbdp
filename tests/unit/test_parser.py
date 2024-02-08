#
# Tests for the Parser class
#
import pbdp
from pbdp import segment
import os
from pathlib import Path
import pytest


@pytest.fixture
def data():
    parser = pbdp.Parser()
    path = Path(pbdp.__path__[0], "input", "data").absolute()
    data = parser.data_importer(path_or_file=path / "Digatron.csv",
                                file_type="csv", save_option="save all",
                                state_option="yes")
    return data


class TestOptimisationResult():
    def test_init_default(self):
        """Test the init method with default settings"""

        # Check default settings
        parser = pbdp.Parser()

        # Check keywords
        cycler_keywords = {
            "maccor": ["Cyc#", "Rec#", "TestTime"],
            "vmp3": ["mode", "(Q-Qo)/mA.h", "freq/Hz", "time/s", "Ecell/V"],
            "bitrode": ["Exclude", "Total Time", "Loop Counter#1", "Amp-Hours"],
            "digatron": ["Step,", "AhAccu", "Prog Time"],
            "ivium": ["freq. /Hz", "Z1 /ohm"],
            "gamry": ["Pt\tT", "IERange"],
            "solatron": ["Time (s)", "Z' (Ohm)"],
            "novonix": ["Potential (V)", "Cycle Number"],
        }
        assert parser.cycler_keywords == cycler_keywords, \
            'Cycler keywords should be as expected'

        # Check standard time
        standard_time = ["Total Time, (h:m:s)", "Run Time (h)"]
        assert parser.standard_time == standard_time, \
            'Standard time should be as expected'

        # Check standard units
        standard_units = {"<I>/mA": 1e3, "(Q-Qo)/mA.h": 1e3}
        parser.standard_units == standard_units, 'Standard units should be as expected'

        # Check standard headers
        standard_headers = {
            "Current [A]": [
                "Current A",
                "Current",
                "Im",
                "Amps",
                " Current (A)",
                "Current (A)",
                "<I>/mA",
                "I/mA",
                "Current, A",
            ],
            "Voltage [V]": [
                "Voltage V",
                "Voltage",
                "Vf",
                "Volts",
                "Voltage [V]",
                "Potential (V)",
                "Ewe-Ece/V",
                "Ecell/V",
                "Voltage (V)",
                "Voltage (V)",
                "Voltage, V",
            ],
            "Voltage We [V]": ["Ewe/V"],
            "Voltage Ce [V]": ["Ece/V"],
            "AmpHrs [Ah]": [
                "Amp-Hours AH",
                "Amp-Hours",
                "AhAccu",
                "Amp-hr",
                "Cap. [Ah]",
                "Capacity (Ah)",
                "Charge (C)",
                "(Q-Qo)/mA.h",
                "Charge (C)",
                "Amp-Hours, AH",
            ],
            "WattHrs [Wh]": [
                "Watt-Hours WH",
                "Watt-Hours",
                "WhAccu",
                "Watt-hr",
                "Ener. [Wh]",
                "Energy (Wh)",
                "Watt-Hours, WH",
            ],
            "Temperature [degC]": [
                "Temperature A1",
                "LogTemp001",
                "Temp",
                "Temp 1",
                "Temperature (°C)",
                "LogTemp0130102",
                "Aux #1",
            ],
            "Step Number": ["Step", "Step Number"],
            "freq [Hz]": [
                "freq. /Hz",
                "Frequency (Hz)",
                "freq/Hz",
                "Frequency (Hz)",
            ],
            "ReZ [Ohm]": ["Z1 /ohm", "Z' (Ohm)", "Re(Z)/Ohm", "Z' (Ohm)"],
            "ImZ [Ohm]": ["Z2 /ohm", "Z'' (Ohm)", "Im(Z)/Ohm", "Z'' (Ohm)"],
            "magZ [Ohm]": ["| Z | (Ohm)", "|Z|/Ohm"],
            "phaseZ [deg]": ["Phase (Deg)", "Phase(Z)/deg"],
            "Cycle Number": ["Cyc#", "Cycle Number", "cycle number"],
            "Time [s]": [
                "TestTime",
                "TestTime(s)",
                "time/s",
                "Total Time, (h:m:s)",
                "Total Time",
                "Prog Time",
                "T",
                "Time (s)",
                "Run Time (h)",
                "Time, (s)",
                "Total Time S",
            ],
        }
        for key, value in standard_headers.items():
            assert parser.standard_headers[key] == value, \
                f'Standard headers for {key} should be as expected'

    def test_init_custom(self):
        """Test the init method with custom settings"""

        # Check custom settings
        cycler_keywords = {"test": ["a", "b", "c"]}
        standard_time = ["a", "b", "c"]
        standard_units = {"a": 1, "b": 2}
        standard_headers = {"a": ["b", "c"]}
        parser = pbdp.Parser(
            cycler_keywords=cycler_keywords,
            standard_units=standard_units,
            standard_time=standard_time,
            standard_headers=standard_headers,
        )

        assert parser.cycler_keywords == cycler_keywords, \
            'Cycler keywords should be as expected'
        assert parser.standard_time == standard_time, \
            'Standard time should be as expected'
        assert parser.standard_units == standard_units, \
            'Standard units should be as expected'
        assert parser.standard_headers == standard_headers, \
            'Standard headers should be as expected'

    def test_look_for_files(self):
        """Test the look_for_files method"""
        parser = pbdp.Parser()

        path = Path(
            pbdp.__path__[0],
            "input",
            "data",
        )

        # Check single file
        files = parser.look_for_files(path / "Maccor.csv")
        assert files == [path / "Maccor.csv"], 'Files should be as expected'

        # Check empty file
        try:
            parser.look_for_files(path / "empty.txt")
        except ValueError as e:
            assert "Empty file" in str(e), 'Empty File should be in Error'

        # Check empty directory
        os.makedirs(path / "empty")

        try:
            parser.look_for_files(path / "empty")
        except ValueError as e:
            assert "No files" in str(e), 'No Files should be in Error'

        os.removedirs(path / "empty")

    def test_data_importer(self, data):
        assert data is not None

    def test_segment_data(self, data):
        segment.segment_data(data, requests=["step"])
        segment.segment_data(data, requests=["step 10:20"])
        segment.segment_data(data, requests=["step 5:5"])
        segment.segment_data(data, requests=["time"])
        segment.segment_data(data, requests=["time 50/200"])
        segment.segment_data(data, requests=["time 50/50"])
        segment.segment_data(data, requests=["rest"])
        segment.segment_data(data, requests=["charging"])
        segment.segment_data(data, requests=["charging 0.5A"])
        segment.segment_data(data, requests=["dischg"])
        segment.segment_data(data, requests=["dischg 0.5A"])
        segment.segment_data(data, requests=["cc"])
        segment.segment_data(data, requests=["cc 1.67A"])
        segment.segment_data(data, requests=["cv"])
        segment.segment_data(data, requests=["cv 4.2V"])
        segment.segment_data(data, requests=["power"])
        segment.segment_data(data, requests=["power 1.05W"])
        segment.segment_data(data, requests=["cccv"])
        segment.segment_data(data, requests=["cccv 1.67A 4.2V"])
        segment.segment_data(data, requests=["cccv 4.2V"])
        segment.segment_data(data, requests=["pulse"])
        segment.segment_data(data, requests=["pulse -1.67A"])
        segment.segment_data(data, requests=["cv, rest"])
        segment.segment_data(data, requests=["rest, cc 1.67A"])
        pulse = segment.segment_data(data, requests=["pulse -10A"])
        segment.reset_time(data=pulse)
        pulse = segment.segment_data(data, requests=["pulse -10A"])
        segment.find_rest(data=data, segments=pulse)

    def test_convert_xlsx_to_csv(self):
        """Test the convert_xlsx_to_csv method"""
        pass

    def test_find_words(self):
        """Test the find_words method"""
        parser = pbdp.Parser()

        # Test it returns expected position and encoding for known file
        path = Path(
            pbdp.__path__[0],
            "input",
            "data",
            "Maccor.csv",
        )
        pos, encoding = parser.find_words(path)

        assert pos == 593, 'Position should be 593'
        assert encoding == "ascii", 'Encoding should be ascii'

    def test_split_file(self):
        """Test the split_file method"""
        path = Path(
            pbdp.__path__[0],
            "input",
            "data",
        )

        parser = pbdp.Parser()

        # The TODOs are because they fail if you have run examples before

        # Check pre_processed folder does not exist
        # TODO: why is this here?
        # assertFalse((path / "pre_processed").exists())

        # Check split file works with save first
        output = parser.split_file(2, path / "test1.csv", "save first")
        assert output == (b"ab", b"cd"), 'Output should be (b"ab", b"cd")'

        # TODO: why is this here?
        # Check split file does not save to pre_processed folder
        # assertFalse((path / "pre_processed").exists())

        # Check split file works with save all
        output = parser.split_file(2, path / "test1.csv", "save all")
        assert output == (b"ab", b"cd"), 'Output should be (b"ab", b"cd")'

        # Check split file saves to pre_processed folder
        assert (path / "pre_processed" / "test1_data.csv").exists(), \
            'File should exist'
        assert (path / "pre_processed" / "test1_metadata.txt").exists(), \
            'File should exist'

        # Clean up
        (path / "pre_processed" / "test1_data.csv").unlink()
        (path / "pre_processed" / "test1_metadata.txt").unlink()
        # TODO: this is also problematic
        # (path / "pre_processed").rmdir()

    def test_read_data_to_pandas(self):
        """Test the read_data_to_pandas method"""
        pass

    def test_change_units(self):
        pass

    def test_change_headers(self):
        pass

    def test_remove_unwanted(self):
        pass
