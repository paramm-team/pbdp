#
# Tests for the Parser class
#
import pbdp
import os
from pathlib import Path
import unittest
import warnings


class TestOptimisationResult(unittest.TestCase):
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
        self.assertDictEqual(parser.cycler_keywords, cycler_keywords)

        # Check standard time
        standard_time = ["Total Time, (h:m:s)", "Run Time (h)"]
        self.assertListEqual(parser.standard_time, standard_time)

        # Check standard units
        standard_units = {"<I>/mA": 1e3, "(Q-Qo)/mA.h": 1e3}
        self.assertDictEqual(parser.standard_units, standard_units)

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
            self.assertListEqual(parser.standard_headers[key], value)

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

        self.assertDictEqual(parser.cycler_keywords, cycler_keywords)
        self.assertListEqual(parser.standard_time, standard_time)
        self.assertDictEqual(parser.standard_units, standard_units)
        self.assertDictEqual(parser.standard_headers, standard_headers)

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
        self.assertEqual(
            files,
            [path / "Maccor.csv"],
        )

        # Check empty file
        with self.assertRaisesRegex(ValueError, "Empty file"):
            parser.look_for_files(path / "empty.txt")

        # Check empty directory
        os.makedirs(path / "empty")

        with self.assertRaisesRegex(ValueError, "No files"):
            parser.look_for_files(path / "empty")

        os.removedirs(path / "empty")

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

        self.assertEqual(pos, 593)
        self.assertEqual(encoding, "ascii")

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
        # self.assertFalse((path / "pre_processed").exists())

        # Check split file works with save first
        output = parser.split_file(2, path / "test1.csv", "save first")
        self.assertEqual(output, (b"ab", b"cd"))

        # TODO: why is this here?
        # Check split file does not save to pre_processed folder
        # self.assertFalse((path / "pre_processed").exists())

        # Check split file works with save all
        output = parser.split_file(2, path / "test1.csv", "save all")
        self.assertEqual(output, (b"ab", b"cd"))

        # Check split file saves to pre_processed folder
        self.assertTrue(
            (path / "pre_processed" / "test1_data.csv").exists()
        )
        self.assertTrue(
            (path / "pre_processed" / "test1_metadata.txt").exists()
        )

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

    def test_data_importer(self):
        # Get the path to the data folder
        path = Path(pbdp.__path__[0], "input", "data").absolute()
        # Create a parser object
        parser = pbdp.Parser()
        data = parser.data_importer(path_or_file=path / "Digatron.csv", print_option="diff", file_type="csv", save_option="save all", state_option="yes")
        pass


if __name__ == "__main__":
    print("Add -v for more debug output")
    import sys

    if "-v" in sys.argv:
        debug = True

    unittest.main()
