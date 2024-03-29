#
# Tests for the Parser class
#
import pbdp


class TestOptimisationResult():
    def test_init(self):
        parser = pbdp.Parser()

        cycler_keywords = {
            "maccor": ["Cyc#", "Rec#", "TestTime", "Rec,"],
            "vmp3": ["mode", "(Q-Qo)/mA.h", "freq/Hz", "time/s", "Ecell/V"],
            "bitrode": ["Exclude", "Total Time", "Loop Counter#1", "Amp-Hours"],
            "digatron": ["Step,", "AhAccu", "Prog Time"],
            "ivium": ["freq. /Hz", "Z1 /ohm"],
            "gamry": ["Pt\tT", "IERange"],
            "solatron": ["Time (s)", "Z' (Ohm)"],
            "novonix": ["Potential (V)", "Cycle Number",
                        "\bDate\b \band\b \bTime\b"],
        }
        assert parser.cycler_keywords == cycler_keywords
