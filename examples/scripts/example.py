import src
import pandas as pd
from src import segment
parser = src.Parser()
#data = parser.data_importer(
#   path_or_file='C:/Users/alex_/Downloads/data/Digatron.csv',
#   file_type='csv'
#)
data = pd.read_csv('C:/Users/alex_/Downloads/data/processed/Digatron_cleaned_data.csv')
print(segment.segment_data(data=data, requests=["cccv, rest"]))
#print(data["Step Number"])
