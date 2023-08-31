#
# Tests for the Parser class
#
import src

import unittest


class TestOptimisationResult(unittest.TestCase):
    def test_init(self):
        parser = src.Parser()

        cycler_keywords = {
            "maccor": ["Cyc#", "Rec#", "TestTime"],
            "vmp3": ["mode", "(Q-Qo)/mA.h", "freq/Hz", "time/s", "Ecell/V"],
            "bitrode": [
                "Exclude",
                "Total Time",
                "Loop Counter#1",
                "Amp-Hours"
                ],
            "digatron": ["Step,", "AhAccu", "Prog Time"],
            "ivium": ["freq. /Hz", "Z1 /ohm"],
            "gamry": ["Pt\tT", "IERange"],
            "solatron": ["Time (s)", "Z' (Ohm)"],
            "novonix": ["Potential (V)", "Cycle Number"],
        }
        self.assertDictEqual(parser.cycler_keywords, cycler_keywords)


if __name__ == "__main__":
    print("Add -v for more debug output")
    import sys

    if "-v" in sys.argv:
        debug = True
    unittest.main()