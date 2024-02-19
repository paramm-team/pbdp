import pbdp
from pbdp import segment
import pandas as pd
from pbdp_logger import create_logger
logger = create_logger(logger_name='pbdp_logger')

parser = pbdp.Parser()
logger.info("Parser created")
data = pd.read_csv(
    "./src/input/data/processed/Digatron_cleaned_data.csv"
)
logger.info("Data loaded via pandas read_csv")
# returns all the segments for rest periods
# output = segment.segment_data(data=data, requests=["power 1.05W"])
output = segment.segment_data(data=data, requests=["pulse -10A"])
logger.info("Data segmented")
print(output)
# adding the rest periods before and after if they exist
new = segment.find_rest(data=data, segments=output)
logger.info("segments created")
#print(segment.reset_time(output))
print(new)
