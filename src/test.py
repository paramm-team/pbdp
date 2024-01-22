import src
from src import segment
import pandas as pd

parser = src.Parser()
data = pd.read_csv(
    "./src/input/data/processed/Digatron_cleaned_data.csv"
)
# returns all the segments for rest periods
# output = segment.segment_data(data=data, requests=["power 1.05W"])
output = segment.segment_data(data=data, requests=["pulse -10A"])
print(output)
# adding the rest periods before and after if they exist
new = segment.find_rest(data=data, segments=output)
#print(segment.reset_time(output))
print(new)
