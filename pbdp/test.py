import pbdp
from pbdp import segment
import pandas as pd
import logging
from pbdp_logger import create_logger
_logger = create_logger()

parser = pbdp.Parser()
logging.info("Parser created")
data = pd.read_csv(
    "./src/input/data/processed/Digatron_cleaned_data.csv"
)
logging.info("Data loaded via pandas read_csv")
# returns all the segments for rest periods
# output = segment.segment_data(data=data, requests=["power 1.05W"])
output = segment.segment_data(data=data, requests=["pulse -10A"])
logging.info("Data segmented")
print(output)
# adding the rest periods before and after if they exist
new = segment.find_rest(data=data, segments=output)
logging.info("segments created")
#print(segment.reset_time(output))
print(new)
