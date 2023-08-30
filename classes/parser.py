import re
import os

import chardet
import openpyxl
import csv

import pandas as pd
from modules.states import add_state_label
from modules.save import save_file
from modules.plots import display_data, plot_current_voltage_diff

class Parser:
    """
    Class for parsing, processing, and analyzing battery data files.

    This class provides methods to import battery data from various file
    formats, process the data by changing units and headers, and perform various
    analyses and visualizations on the battery data.

    Attributes:
        cycler_keywords (dict): Dictionary containing keywords associated with
                                different file types.
        standard_units (dict): Dictionary containing unit conversion factors for
                                 standard units.
        standard_time (list): List of standard time columns to be processed.
        standard_headers (dict): Dictionary mapping standard column headers to
                                    their variations.
    """

    def __init__(
        self,
        cycler_keywords: dict = {},
        standard_units: dict = {},
        standard_time: list = [],
        standard_headers: dict = {},
    ):
        """
        Initialize the class with optional parameters for configuring data 
        processing.

        Args:
            cycler_keywords (dict): Keywords specific to cycler data columns.
            standard_units (dict): Mapping of units to standardize column
                                    values.
            standard_time (list): List of standard time columns.
            standard_headers (dict): Mapping of header variables to standardized
                                     variables.
        """

        # Initialize the class variables based on provided arguments.
        # Data header row options to terminate meta info. NOTE: enter unique
        # names provided by the cycler and not generic e.g. "TestTime" 
        # instead of "time"
        self.cycler_keywords = (
            {
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
            if bool(cycler_keywords) is False
            else cycler_keywords
        )

        # Define the standard time columns
        self.standard_time = (
            ["Total Time, (h:m:s)", "Run Time (h)", "TestTime"]
            if len(standard_time) == 0
            else standard_time
        )

        # Define the standard units
        self.standard_units = (
            {
                "<I>/mA": 1e3,
                "(Q-Qo)/mA.h": 1e3,
            }
            if bool(standard_units) is False
            else standard_units
        )

        # Map key header variables to a standardized variable
        self.standard_headers = (
            {
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
            if bool(standard_headers) is False
            else standard_headers
        )

    def look_for_files(self, path_or_file: str) -> str:
        """
        Locate files based on the provided path or file.

        Args:
            path_or_file (str): The path to a file or a directory.

        Returns:
            list: A list of paths to non-empty files found.

        Raises:
            ValueError: If the provided path or file is invalid or empty.
        """
        if os.path.isfile(path_or_file):
            # If the input is a file, check if it's not empty
            if os.path.getsize(path_or_file) > 1:
                return [path_or_file]
            else:
                raise ValueError(f"Empty file: {path_or_file}")
        elif os.path.isdir(path_or_file):
            # If the input is a directory, scan for non-empty files
            files = [
                os.path.join(path_or_file, f)
                for f in os.listdir(path_or_file)
                if os.path.isfile(os.path.join(path_or_file, f))
                and os.path.getsize(os.path.join(path_or_file, f))
            ]

            if not files:
                raise ValueError(f"""No files found in the directory: 
                                {path_or_file}""")
            return files
        else:
            # If the input is neither a file nor a directory
            raise ValueError(f"Invalid path or file: {path_or_file}")
        

    def convert_xlsx_to_csv(self, file_path: str) -> str:
        """
        Convert an Excel (xlsx) file to a CSV file.

        Args:
            file_path (str): The path to the Excel file to be converted.

        Returns:
            str: The path to the converted CSV file.
        """
        # Load the Excel workbook
        workbook = openpyxl.load_workbook(file_path)
        # Get the active sheet
        sheet = workbook.active

        # Define the path for the temporary CSV file
        current_dir = os.path.dirname(file_path)
        csv_file_path = os.path.join(current_dir, "converted_temporary.csv")

        # Write Excel sheet data to the CSV file
        with open(csv_file_path, "w", newline="") as csv_file:
            writer = csv.writer(csv_file)
            # Write each row in the Excel sheet to the CSV file
            for row in sheet.iter_rows(values_only=True):
                writer.writerow(row)

        return csv_file_path

    def find_words(self, file_path: str) -> tuple:
        """
        Find specific keywords in a file and return the starting position of 
        the match.

        Args:
            file_path (str): The path to the file to search for keywords.

        Returns:
            tuple: A tuple containing the starting position of the match and 
                    the encoding of the file.
        """
        # Check if the file is in xlsx format and convert if necessary
        if file_path.endswith(".xlsx"):
            file_path = self.convert_xlsx_to_csv(file_path)

        # Read the contents of the file and detect the encoding
        with open(file_path, "rb") as f:
            contents = f.read()
            encoding = chardet.detect(contents)["encoding"]
            if encoding is None:
                raise ValueError("Something is wrong with your input file")
            else:
                contents = contents.decode(encoding)

        # Compile the regular expression pattern using cycler_keywords
        data = []
        for value in self.cycler_keywords.values():
            data.extend([rf"\s*{re.escape(word)}\s*" for word in value])
        pattern = re.compile("|".join(data))

        # Search for the keywords in the file
        match = pattern.search(contents)
        if match:
            with open(file_path, "rb") as f:
                # If a match is found, set the file pointer to that location
                f.seek(match.start())
                return (f.tell(), encoding)
        else:
            # If no match is found, raise an exception
            raise ValueError(f"No keywords found in file: {file_path}")

    def split_file(
        self,
        pointer: int,
        file_path: str,
        save_option: str
    ) -> tuple:
        """
        Split a file into two parts based on a pointer position and save them
        as separate files.

        Args:
            pointer (int): The position in the file where the split should
                             occur.
            file_path (str): The path to the file to split.
            save_option (str): The option for saving the split files 
                                ("save all" or "save first").

        Returns:
            tuple: A tuple containing the metadata part and data part as bytes.
        """
        name = file_path

        # Check if the file is in xlsx format and convert if necessary
        if file_path.endswith(".xlsx"):
            file_path = os.path.dirname(file_path) + "/converted_temporary.csv"

        with open(file_path, "rb") as f:
            contents = f.read()
            # Split the file into two parts based on the pointer position
            metadata = contents[:pointer]
            data = contents[pointer:]

        # Find the first non-empty line in the data part
        first_line = next(line for line in data.splitlines() if line.strip())

        # Remove all commas from the first line
        modified_line = first_line.replace(b",", b"")

        # Construct the modified data with the modified first line
        data.replace(first_line, modified_line, 1)

        if save_option == "save all":
            # Get the current directory of the file
            current_dir = os.path.dirname(name)
            # Extract the file name and extension from the input file path
            file_name, file_ext = os.path.splitext(os.path.basename(name))

            # Create a subfolder if it doesn't exist
            output_dir = os.path.join(current_dir, "pre_processed")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Save the metadata part to a text file in the output directory
            metadata_file_name = file_name + "_metadata.txt"
            metadata_output_path = os.path.join(output_dir, metadata_file_name)
            with open(metadata_output_path, "wb") as f:
                f.write(metadata)

            # Save the data part to a new file with the original file format in
            # the output directory
            data_file_name = file_name + "_data" + file_ext
            data_output_path = os.path.join(output_dir, data_file_name)
            with open(data_output_path, "wb") as f:
                f.write(data)

            if "converted_temporary.csv" in os.path.basename(file_path):
                os.remove(file_path)

            return (metadata, data)
        
        else:
            if "converted_temporary.csv" in os.path.basename(file_path):
                os.remove(file_path)
            return (metadata, data)

    def read_data_to_pandas(
        self,
        data: bytes,
        filepath: str,
        encoding: str
    ) -> pd.DataFrame:
        """
        Read data from a bytes object into a Pandas DataFrame.

        Args:
            data (bytes): The bytes object containing the data to be read.
            filepath (str): The original file path (determine file extension).
            encoding (str): The encoding to use for reading the data.

        Returns:
            pd.DataFrame: A Pandas DataFrame containing the read data.
        """

        # Write data to a temporary file
        temp_file = "new_file_name"
        with open(temp_file, "wb") as f:
            f.write(data)

        # Determine file extension
        file_ext = os.path.splitext(filepath)[1]

        # Read file using the appropriate Pandas function based on its extension
        if file_ext == ".csv":
            df = pd.read_csv(temp_file, encoding=encoding)
        elif file_ext == ".xlsx":
            df = pd.read_excel(temp_file, encoding=encoding)
        elif file_ext == ".txt":
            df = pd.read_csv(temp_file, sep="\t", encoding=encoding)
        elif file_ext == ".mpt":
            df = pd.read_table(temp_file, encoding=encoding)
        elif file_ext == ".DTA":
            df = pd.read_table(temp_file, sep="\t", encoding=encoding)
        else:
            os.remove(temp_file)
            raise ValueError(f"Invalid file format: {file_ext}")

        # Remove the temporary file
        os.remove(temp_file)

        return df

    def change_units(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Change units of selected columns in a DataFrame based on standard units.

        Args:
            df (pd.DataFrame): The DataFrame containing data to be processed.

        Returns:
            pd.DataFrame: A new DataFrame with units converted according to
                            standard_units.
        """

        for col in data.columns:
            if col in self.standard_units:
                # Convert values in columns with standard units
                data[col] = data[col] * self.standard_units[col]
            elif col in self.standard_time:
                if col == "Run Time (h)":
                    # Convert hours to seconds
                    data[col] = data[col] * 3600
                else:
                    # Convert a string representing a time duration to seconds
                    time_delta = pd.to_timedelta(data[col])
                    data[col] = time_delta.total_seconds()

        return data

    def change_headers(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Change column headers of a DataFrame based on standard header mapping.

        Args:
            df (pd.DataFrame): The DataFrame containing data to be processed.

        Returns:
            pd.DataFrame: A new DataFrame with column headers converted
                            according to standard_headers.
        """

        # Get the original column names
        original_headers = data.columns
        # Create a dictionary to store the new header names
        new_headers = {}

        for col in original_headers:
            for header, value in self.standard_headers.items():
                # Check if the original header matches the mapping
                if col in value:
                    new_headers[col] = header
                    break

        # Rename columns using the new mapping
        data.rename(columns=new_headers, inplace=True)

        # Convert columns with new headers to numeric data types
        for col in data.columns:
            if col in self.standard_headers:
                data[col] = pd.to_numeric(data[col], errors="coerce")

        return data

    def remove_unwanted(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Remove unwanted rows and columns from a DataFrame.

        Args:
            df (pd.DataFrame): The DataFrame containing data to be processed.

        Returns:
            pd.DataFrame: A new DataFrame with unwanted rows and columns
                            removed.
        """

        if "Step Number" in data.columns:
            # Drop rows from threshold index to the end of the DataFrame
            diff_threshold = 5  # You can adjust this threshold based on the data NOT IMPLEMENTED YET
            t_index = (data["Step Number"].diff() > diff_threshold).idxmax()
            data = data.iloc[:t_index]

        # Get the column(s) with unnamed header and drop them
        unnamed_cols = data.columns[data.columns.str.contains("^Unnamed:")]
        data = data.drop(columns=unnamed_cols)

        # Drop unwanted NAs created by pre-processing
        data = data.dropna()
        data = data.reset_index(drop=True)

        return data

    def data_importer(
        self,
        path_or_file: str,
        file_type: str = "parquet",
        save_option: str = "save",
        state_option: str = "",
        print_option: str = "",
    ) -> pd.DataFrame:
        """
        Import, process, and optionally save and/or print battery data.

        Args:
            path_or_file (str): Path to a directory or file containing battery 
                                data.
            file_type (str, optional): The type of file to save as. Defaults to 
                                        "csv".
            save_option (str, optional): Option for saving files. Defaults to
                                        "save".
            state_option (str, optional): Option to add battery state labels.
                                            Defaults to "".
            print_option (str, optional): Option for printing data and plots.
                                            Defaults to "".
        """
        for file in self.look_for_files(path_or_file):
            # Process each file
            pointer, encoding = self.find_words(file)
            metadata, data = self.split_file(pointer, file, save_option)
            data = self.read_data_to_pandas(data, file, encoding)
            data = self.change_units(data)
            data = self.change_headers(data)
            data = self.remove_unwanted(data)
            if state_option == "yes":
                try:
                    data = add_state_label(data)
                except Exception as e:
                    print(f"An error occurred: {e} in file {file}")
            # Save the file if the option is set to 'save all' or 'save'
            if save_option in ["save all", "save"]:
                save_file(data, file_type, file)
            # Print the dataframe and the plots if print_option is 'yes' or all
            if print_option in ["yes", "diff"]:
                try:
                    display_data(data)
                except Exception as e:
                    print(f"An error occurred: {e} in file {file}")
            # Print the diff on current and voltage if print_option is 'all'
            if print_option == "diff":
                try:
                    plot_current_voltage_diff(data)
                except Exception as e:
                    print(f"An error occurred: {e} in file {file}")

        return data