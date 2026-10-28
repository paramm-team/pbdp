"""Historical function-only example; see quickstart.py for the runnable demo.

Calling test_simple writes beside a bundled vendor fixture. This file is kept
for history and is not run by the supported quickstart or its integration test.
"""
from pathlib import Path
import pbdp
from pbdp import segment


def test_simple():
    data_file = Path(pbdp.__path__[0], "input", "data", "Digatron.csv")

    parser = pbdp.Parser()
    data = parser.data_importer(
        path_or_file=data_file,
        file_type='csv'
    )
    print(segment.segment_data(data=data, requests=["cccv, rest"]))
    #print(data["Step Number"])
