#
# Tests for the Parser class
#
import src
import os

import unittest


class TestOptimisationResult(unittest.TestCase):
    def test_init_default(self):
        """Test the init method with default settings"""

        # Check default settings
        parser = src.Parser()

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
        standard_time = ["Total Time, (h:m:s)", "Run Time (h)", "TestTime"]
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
            "Voltage Full [V]": [
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
        self.assertDictEqual(parser.standard_headers, standard_headers)

    def test_init_custom(self):
        """Test the init method with custom settings"""

        # Check custom settings
        cycler_keywords = {"test": ["a", "b", "c"]}
        standard_time = ["a", "b", "c"]
        standard_units = {"a": 1, "b": 2}
        standard_headers = {"a": ["b", "c"]}
        parser = src.Parser(
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
        parser = src.Parser()

        # Check wrong path
        with self.assertRaisesRegex(ValueError, "Invalid path"):
            parser.look_for_files("")

        path = os.path.join(
            src.__path__[0],
            "input",
            "data",
        )

        # Check single file
        files = parser.look_for_files(os.path.join(path, "Maccor.csv"))
        self.assertEqual(
            files,
            [os.path.join(path, "Maccor.csv")],
        )

        # Check empty file
        with self.assertRaisesRegex(ValueError, "Empty file"):
            parser.look_for_files(os.path.join(path, "empty.txt"))

        # Check directory
        files = parser.look_for_files(path)
        self.assertEqual(len(files), 5)

        # Check empty directory
        with self.assertRaisesRegex(ValueError, "No files"):
            parser.look_for_files(os.path.join(path, "empty"))

    def test_convert_xlsx_to_csv(self):
        """Test the convert_xlsx_to_csv method"""
        pass

    def test_find_words(self):
        """Test the find_words method"""
        parser = src.Parser()

        # Test it returns expected position and encoding for known file
        path = os.path.join(
            src.__path__[0],
            "input",
            "data",
            "Maccor.csv",
        )
        pos, encoding = parser.find_words(path)

        self.assertEqual(pos, 593)
        self.assertEqual(encoding, "ascii")

    def test_split_file(self):
        """Test the split_file method"""
        path = os.path.join(
            src.__path__[0],
            "input",
            "data",
        )

        parser = src.Parser()

        # Check pre_processed folder does not exist
        self.assertFalse(os.path.exists(os.path.join(path, "pre_processed")))

        # Check split file works with save first
        output = parser.split_file(2, os.path.join(path, "test1.csv"), "save first")
        self.assertEqual(output, (b"ab", b"cd"))

        # Check split file does not save to pre_processed folder
        self.assertFalse(os.path.exists(os.path.join(path, "pre_processed")))

        # Check split file works with save all
        output = parser.split_file(2, os.path.join(path, "test1.csv"), "save all")
        self.assertEqual(output, (b"ab", b"cd"))

        # Check split file saves to pre_processed folder
        self.assertTrue(
            os.path.exists(os.path.join(path, "pre_processed", "test1_data.csv"))
        )
        self.assertTrue(
            os.path.exists(os.path.join(path, "pre_processed", "test1_metadata.txt"))
        )

        # Clean up
        os.remove(os.path.join(path, "pre_processed", "test1_data.csv"))
        os.remove(os.path.join(path, "pre_processed", "test1_metadata.txt"))
        os.removedirs(os.path.join(path, "pre_processed"))

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
        pass


if __name__ == "__main__":
    print("Add -v for more debug output")
    import sys

    if "-v" in sys.argv:
        debug = True
    unittest.main()
