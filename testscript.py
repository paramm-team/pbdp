from classes.parser import Parser
from modules.segment import segment_data
from modules.states import add_state_label
from modules.states import find_cc_and_cv
my_instance = Parser()

data = my_instance.data_importer(path_or_file='C:/Users/alex_/Downloads/Cell033_RPT_0p3C_0p3C_100_0_80cyc_10degC.csv', 
                 state_option='', print_option='', save_option='', file_type='csv')

list_df = segment_data(data, ["dischg"])
#print(list_df[0]["Current [A]"], list_df[1]["Voltage Full [V]"], list_df[2])
print(list_df)
print(len(list_df))


# # test_my_functions.py

# def test_add_positive_numbers():
#     assert 2 + 3 == 5

# def test_add_negative_numbers():
#     assert -2 + -3 == -5
 