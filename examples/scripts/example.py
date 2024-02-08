from pathlib import Path
import pbdp
from pbdp import segment

data_file = Path(pbdp.__path__[0], "input", "data", "Digatron.csv")

parser = pbdp.Parser()
data = parser.data_importer(
    path_or_file=data_file,
    file_type='csv'
)
print(segment.segment_data(data=data, requests=["cccv, rest"]))
#print(data["Step Number"])
