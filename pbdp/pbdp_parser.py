import re
from datetime import datetime, timedelta

import chardet
import openpyxl
import csv
from pathlib import Path
import logging

import pandas as pd
from .states import add_state_label
from .save import save_file
from .plots import display_data, plot_current_voltage_diff
from typing import Union
from typing import List


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
        logger_name: str = "pbdp_logger",
    ):
        self.logger = logging.getLogger(logger_name)
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
            logger_name (str): Name of the logger to use, defaults to "pbdp_logger"
                               which is the default logger. That can be initialized
                               using pbdp.create_logger() function.
        """

        # Initialize the class variables based on provided arguments.
        # Data header row options to terminate meta info. NOTE: enter unique
        # names provided by the cycler and not generic e.g. "TestTime"
        # instead of "time"
        self.cycler_keywords = (
            {
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
            if bool(cycler_keywords) is False
            else cycler_keywords
        )

        # Define the standard time columns
        self.standard_time = (
            ["Total Time, (h:m:s)", "Run Time (h)", "TestTime"]
            if bool(standard_time) is False
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
                "Voltage [V]": [
                    "Voltage V",
                    "Voltage",
                    "Vf",
                    "Volts",
                    "Voltage [V]",
                    "Potential (V)",
                    "Ewe-Ece/V",
                    "Ecell/V",
                    " Ecell/V"
                    "Voltage (V)",
                    "Voltage (v)",
                    " Voltage (V)",
                    "Voltage, V",
                ],
                "Working electrode potential [V]": ["Ewe/V"],
                "Counter electrode potential [V]": ["Ece/V"],
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
                "Absolute time": ["e and Time", "DPT Time",],
            }
            if bool(standard_headers) is False
            else standard_headers
        )

        self.logger.info("Parser initialized")

    def look_for_files(self, path_or_file: Path) -> List[Path]:
        """
        Locate files based on the provided path or file.

        Args:
            path_or_file (Path): The path to a file or a directory.

        Returns:
            List[Path]: A list of paths to non-empty files found.

        Raises:
            ValueError: If the provided path or file is invalid or empty.
        """
        if path_or_file.is_file():
            # If the input is a file, check if it's not empty
            if path_or_file.stat().st_size > 1:
                self.logger.debug("File found")
                return [path_or_file]
            else:
                self.logger.warning(f"Empty file, {path_or_file} ")
                raise ValueError(f"Empty file: {path_or_file}")
        elif path_or_file.is_dir():
            # If the input is a directory, scan for non-empty files
            files = [
                f
                for f in path_or_file.iterdir()
                if f.is_file()
                and f.stat().st_size
            ]
            self.logger.debug("Directory found")

            if not files:
                self.logger.warning("No files found in the directory, {path_or_file}")
                raise ValueError(
                    f"""No files found in the directory:
                                {path_or_file}"""
                )
            return files
        else:
            # If the input is neither a file nor a directory
            self.logger.warning(f"Invalid path or file, {path_or_file}")
            raise ValueError(f"Invalid path or file: {path_or_file}")

    def convert_xlsx_to_csv(self, file_path: Path) -> Path:
        """
        Convert an Excel (xlsx) file to a CSV file.

        Args:
            file_path (str): The path to the Excel file to be converted.

        Returns:
            str: The path to the converted CSV file.
        """
        # Load the Excel workbook
        workbook = openpyxl.load_workbook(str(file_path.resolve()))
        # Get the active sheet
        sheet = workbook.active
        self.logger.debug(f"Excel file, {file_path}, loaded")

        # Define the path for the temporary CSV file
        current_dir = file_path.parent
        csv_file_path = current_dir / "converted_temporary.csv"

        # Write Excel sheet data to the CSV file
        with csv_file_path.open(mode='w') as csv_file:
            writer = csv.writer(csv_file)
            # Write each row in the Excel sheet to the CSV file
            if sheet is not None:
                for row in sheet.iter_rows(values_only=True):
                    writer.writerow(row)

        self.logger.debug(f"Excel file, {file_path}, converted to CSV, {csv_file_path}")
        return csv_file_path

    def find_words(self, file_path: Path, cycler: str = "") -> tuple:
        """
        Searches the file contents for specific keywords related to different types of
        equipment. The search is performed iteratively for each equipment type defined
        in self.cycler_keywords.

        Args:
            file_path (str): Path to the file to be processed.

        Returns:
            tuple: A tuple containing the file pointer position of the first keyword
                   match and the equipment type, or (None, None) if no match is found.
        """
        # Check if the file is in xlsx format and convert if necessary
        if file_path.suffix == ".xlsx":
            self.logger.info(f"Converting Excel file, {file_path}, to CSV")
            file_path = self.convert_xlsx_to_csv(file_path)

        # Read the contents of the file and detect the encoding
        with file_path.open(mode="rb") as f:
            contents = f.read()
            encoding = chardet.detect(contents)["encoding"]
            if encoding is None:
                self.logger.warning(f"No encoding detected; Something is wrong with\
                                     your input file, {file_path}")
                raise ValueError("Something is wrong with your input file")
            else:
                self.logger.info(f"Encoding detected: {encoding}")
                contents = contents.decode(encoding)
                self.logger.info("File content read")

        if not cycler:
            # Iterate over each equipment type in the cycler_keywords dictionary
            for equipment_type, keywords in self.cycler_keywords.items():
                patterns = []
                for phrase in keywords:
                    # Split the phrase into words and escape each word
                    escaped_words = [re.escape(word) for word in phrase.split()]
                    # Join the words with '\s*' to allow for flexible whitespace
                    pattern = r'\s*'.join(escaped_words)
                    patterns.append(pattern)

                # Compile a regex pattern for the current set of keywords/phrases
                full_pattern = re.compile("|".join(patterns))

                # Search for the keywords in the file contents
                match = full_pattern.search(contents)
                if match:
                    with open(file_path, "rb") as f:
                        # If a match is found, set the file pointer to that location
                        # and return the position and the equipment type
                        f.seek(match.start())
                        self.logger.info(f"Keywords found in file, {file_path}, at\
                                         position {match.start()}, pointer set")
                        return (f.tell(), encoding, equipment_type)
        # If the line number is given for the header of the line set the file pointer
        # to that location
        elif str(cycler).isnumeric():
            cycler = int(cycler)
            with open(file_path, "rb") as f:
                current_line = 1
                while current_line < cycler:
                    line = f.readline()
                    if line == b'':
                        # Reached EOF before the desired line number
                        return (-1,)  # Fix: Return -1 as a tuple
                    current_line += 1
                # The file pointer is now at the beginning of the desired line
                return (f.tell(), encoding, 'cannot determine')
        elif cycler in self.cycler_keywords.keys():
            patterns = []
            for phrase in self.cycler_keywords[str(cycler)]:
                # Split the phrase into words and escape each word
                escaped_words = [re.escape(word) for word in phrase.split()]
                # Join the words with '\s*' to allow for flexible whitespace
                pattern = r'\s*'.join(escaped_words)
                patterns.append(pattern)
            # Compile a regex pattern for the current set of keywords/phrases
            full_pattern = re.compile("|".join(patterns))
            # Search for the keywords in the file contents
            match = full_pattern.search(contents)
            if match:
                with open(file_path, "rb") as f:
                    # If a match is found, set the file pointer to that location and
                    # return the position and the equipment type
                    f.seek(match.start())
                    self.logger.info(f"Keywords found in file, {file_path}, at position\
                             {match.start()}, pointer set")
                    return (f.tell(), encoding, cycler)
        else:
            print("This cycler is not yet supported")

        # If no match is found, raise an exception
        self.logger.warning(f"No keywords found in file, {file_path}")
        return (None, None)

    def split_file(self, pointer: int, file_path: Path, save_option: str) -> tuple:
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
        if file_path.suffix == ".xlsx":
            self.logger.info(f"file {file_path} is in xlsx format")
            file_path = file_path.parent / "converted_temporary.csv"

        with file_path.open(mode="rb") as f:
            contents = f.read()
            # Split the file into two parts based on the pointer position
            metadata = contents[:pointer]
            data = contents[pointer:]

        # Define the delimiters to check for
        delimiters = (b',', b'\t', b';', b' ')
        self.logger.info(f"File, {file_path}, split at position {pointer}")

        # Convert binary data to a list of lines for processing
        lines = data.splitlines()

        # Check if the first line is empty or starts with a delimiter
        if lines and (not lines[0].strip() or lines[0].lstrip().startswith(delimiters)):
            # Remove the first line
            lines = lines[1:]

        # Construct the modified data with the modified first line
        data = b'\n'.join(lines)
        self.logger.info("Delimiters removed from first line of data")

        if save_option == "save all":
            self.logger.info("Save All option selected")
            # Get the current directory of the file
            current_dir = name.parent
            # Extract the file name and extension from the input file path
            file_name, file_ext = name.stem, name.suffix

            # Create a subfolder if it doesn't exist
            output_dir = current_dir / "pre_processed"
            if not output_dir.exists():
                self.logger.info(f"Creating directory, {output_dir}")
                output_dir.mkdir()

            # Save the metadata part to a text file in the output directory
            metadata_file_name = file_name + "_metadata.txt"
            metadata_output_path = output_dir / metadata_file_name
            with metadata_output_path.open(mode="wb") as f:
                f.write(metadata)
                self.logger.info(f"Metadata saved to {metadata_output_path}")

            # Save the data part to a new file with the original file format in the
            # output directory
            data_file_name = file_name + "_data" + file_ext
            data_output_path = output_dir / data_file_name
            with data_output_path.open(mode="wb") as f:
                f.write(data)
                self.logger.info(f"Data saved to {data_output_path}")

            if "converted_temporary.csv" in file_path.name:
                self.logger.info(f"Deleting temporary file, {file_path}")
                file_path.unlink()

            return (metadata, data)

        else:
            if "converted_temporary.csv" in file_path.name:
                self.logger.info(f"Deleting temporary file, {file_path}")
                file_path.unlink()
            return (metadata, data)

    def read_data_to_pandas(
        self, data: bytes, filepath: Path, encoding: str
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
        temp_file = filepath.parent / "new_file_name"
        with temp_file.open(mode="wb") as f:
            self.logger.info(f"Writing data to temporary file for Pandas Import,\
                         {temp_file}")
            f.write(data)

        # Determine file extension
        file_ext = filepath.suffix

        # Read file using the appropriate Pandas function based on its extension
        if file_ext == ".csv":
            df = pd.read_csv(temp_file, encoding=encoding, low_memory=False)
        elif file_ext == ".xlsx":
            # xlsx is converted to csv before
            df = pd.read_csv(temp_file, encoding=encoding, low_memory=False)
        elif file_ext == ".txt":
            df = pd.read_csv(temp_file, sep="\t", encoding=encoding, low_memory=False)
        elif file_ext == ".mpt":
            df = pd.read_csv(temp_file, sep="\t", encoding=encoding, low_memory=False)
        elif file_ext == ".DTA":
            df = pd.read_table(temp_file, sep="\t", encoding=encoding, low_memory=False)
        else:
            self.logger.warning(f"Invalid file format, {file_ext},\
                                deleting temporary file")
            temp_file.unlink()
            raise ValueError(f"Invalid file format: {file_ext}")

        # Remove the temporary file
        self.logger.info(f"Data read, deleting temporary file, {temp_file}")
        temp_file.unlink()

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
                self.logger.info(f"Units converted to standard for {col}")
            elif col in self.standard_time:
                if col == "Run Time (h)":
                    # Convert hours to seconds
                    data[col] = data[col] * 3600
                    self.logger.info("Time converted to seconds from Run Time (h)")
                else:
                    # Convert a string representing a time duration to seconds
                    data[col] = pd.to_timedelta(data[col]).dt.total_seconds()
                    self.logger.info("Time converted to seconds from string")

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
        def normalize_header(header):
            """Normalize a header to a common format."""
            # Lowercase and remove special characters
            header = header.lower()
            header = re.sub(r'\s+|\[|\]|/|,', '', header)
            return header

        # Get the original column names
        original_headers = data.columns
        # Create a dictionary to store the new header names
        new_headers = {}
        #normalize headers in the document
        for col in original_headers:
            normalized_col = normalize_header(col)
            matched = False

            for header, values in self.standard_headers.items():
                normalized_values = [normalize_header(value) for value in values]
                # Check if the original header matches the mapping
                if normalized_col in normalized_values:
                    new_headers[col] = header
                    matched = True
                    break

            if not matched:
                self.logger.info(f"No standard header found for: {col}")

        self.logger.info("Headers converted to standard")
        # Rename columns using the new mapping
        data.rename(columns=new_headers, inplace=True)

        # Convert columns with new headers to numeric data types
        for col in data.columns:
            if col in self.standard_headers and col != "Absolute time":
                data[col] = pd.to_numeric(data[col], errors="coerce")

        self.logger.info("Columns converted to numeric")

        return data

    def remove_unwanted(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Remove unwanted rows and columns from a DataFrame.

        Args:
            df (pd.DataFrame): The DataFrame containing data to be processed.

        Returns:
            pd.DataFrame: A new DataFrame with unwanted rows and columns removed.
        """

        self.logger.info("Removing unwanted rows and columns")
        if "Step Number" in data.columns:
            # Drop rows from threshold index to the end of the DataFrame
            diff_threshold = (
                5  # You can adjust this threshold based on the data NOT IMPLEMENTED YET
            )
            t_index = (data["Step Number"].diff() > diff_threshold).idxmax()
            if isinstance(t_index, int) and t_index > 0:
                data = data.iloc[:t_index]

        # Get the column(s) with unnamed header and drop them
        unnamed_cols = data.columns[data.columns.str.contains("^Unnamed:")]
        data = data.drop(columns=unnamed_cols)

        # Drop unwanted NAs created by pre-processing
        data = data.dropna()
        data = data.reset_index(drop=True)
        self.logger.info("Unwanted rows and columns removed")
        return data

    def find_start_time(self, metadata: str) -> str:
        """
        Searches the provided metadata for a start time of an experiment using various
        patterns.

        Args:
            metadata (str): A string containing the experiment's metadata, which may
                             include the start time or date in various formats.

        Returns:
            str or None: The extracted start time as a string if a match is found;
                         otherwise, None.
        """
        # List of regular expression patterns for matching start time/date in metadata.
        # Each pattern accounts for a specific format that the start time/date might be
        # recorded in.
        patterns = [
            # Matches Start Time
            r"Start Time,?(\d+/\d+/\d+ \d+:\d+:\d+ [APM]+)",
            # Matches Test Date
            r"Test Date:?,?\"?(\d+/\d+/\d+ \d+:\d+:\d+)",
            # Matches Start date
            r"Start date:, (\d+ \w+ \d+)",
            # Matches Start time with timezone offset
            r"Start time:, (\d+:\d+:\d+ \+\d+:\d+)",
            # Matches Technique started on
            r"Technique started on : (\d+/\d+/\d+ \d+:\d+:\d+)",
            # Matches DATE with tab-separated LABEL
            r"DATE\tLABEL\t(\d+/\d+/\d+)",
            # Matches DATE with tab-separated LABEL
            r"TIME\tLABEL\t(\d+:\d+:\d+)",
            # Matches Date of Test
            r"Date of Test:?,?\"?(\d+ \w+ \d+, \d+:\d+:\d+ [APM]+)",
            # Matches Started
            r"Started,(\d+/\d+/\d+ \d+:\d+)",
            # Matches Modify on
            r"Modify on : (\d+/\d+/\d+ \d+:\d+)",
            # Matches Acquisition started on
            r"Acquisition started on : (\d+/\d+/\d+ \d+:\d+:\d+)",
            # Matches Date in ISO format
            r"Date,(\d+-\d+-\d+ \d+:\d+:\d+),",
            # Matches Time
            r"Time,(\d+:\d+:\d+),"
        ]

        # Iterate over each pattern, searching for a match in the metadata.
        for pattern in patterns:
            match = re.search(pattern, metadata, re.IGNORECASE)
            if match:
                # If a match is found, return the matched group, which is the date/time.
                self.logger.info("Date and time found in metadata.")
                return match.group(1)

        # If no matches are found, return an empty string.
        self.logger.warning("Date and time not found in metadata.")
        return ""

    def absolute_time(
            self,
            metadata: Union[bytes, str],
            data: pd.DataFrame,
            encoding: str
    ) -> pd.DataFrame:
        """
        Adds an 'Absolute Time [s]' column to the provided DataFrame based on the
        experiment's start time found in metadata. The method attempts to identify the
        start time from various potential formats in the metadata. If successful, it
        calculates absolute time for each row in the data DataFrame and adds this as a
        new column.

        Args:
            metadata (bytes): Metadata containing the experiment's start time.
            data (pd.DataFrame): DataFrame containing the experiment data, including a
                                 "Time [s]" column which is cumulative time since the
                                 start of the experiment.
            encoding (str): Encoding of the metadata if provided as bytes. Default is
                            'utf-8'.

        Returns:
            pd.DataFrame: The input DataFrame with an added 'Absolute Time [s]' column.

        Raises:
            ValueError: If the start time format is not recognized or cannot be found
                        in metadata.
        """

        # Check if 'Absolute Time [s]' is already present in the DataFrame.
        if "Absolute Time [s]" in data.columns:
            return data

        # Decode metadata from bytes to string if necessary.
        if isinstance(metadata, bytes):
            metadata = metadata.decode(encoding)
        metadata = str(metadata)

        # Attempt to find start time from metadata.
        start_time_str = self.find_start_time(metadata)

        # Additional logic for combining separate date and time entries in metadata.
        # This part is crucial for cases where the date and time are provided
        # separately and need to be concatenated.
        combined_patterns = [
            (r"Start date:, (\d+ \w+ \d+)", r"Start time:, (\d+:\d+:\d+ \+\d+:\d+)"),
            (r"DATE\tLABEL\t(\d+/\d+/\d+)", r"TIME\tLABEL\t(\d+:\d+:\d+)"),
            (r"Date,(\d+-\d+-\d+ \d+:\d+:\d+,)", r"Time,(\d+:\d+:\d+,)")
        ]
        for date_pat, time_pat in combined_patterns:
            if re.search(date_pat, metadata) and re.search(time_pat, metadata):
                date_str = self.find_start_time(date_pat + metadata.split(date_pat)[-1])
                time_str = self.find_start_time(time_pat + metadata.split(time_pat)[-1])
                if date_str and time_str:
                    start_time_str += " " + time_str  # Combine date and time.

        # Convert start time string to datetime object using various potential formats.
        for fmt in ("%d/%m/%Y %H:%M:%S", "%d %B %Y %H:%M:%S", "%Y-%m-%d %H:%M:%S",
                    "%d/%m/%Y %H:%M", "%d %B %Y, %I:%M:%S %p"):
            try:
                start_time = datetime.strptime(start_time_str, fmt)
                break
            except ValueError:
                continue
        else:
            self.logger.warning("Start time format not recognized or start time not\
                                 found in metadata.")
            raise ValueError("Start time format not recognized or start time not found\
                              in metadata.")

        # Calculate and add 'Absolute Time [s]' to the DataFrame.
        data["Absolute Time [s]"] = data["Time [s]"].cumsum().apply(
            lambda x: start_time + timedelta(seconds=x))
        self.logger.info("Absolute time added to the data frame")

        return data

    def sanity_check(self, data: pd.DataFrame) -> int:
        """
        Performs a sanity check on the provided DataFrame to determine if it is a
        normal experiment or a frequency experiment and ensures the presence of
        necessary data.
        Required Columns:
            Normal experiments (flexible): Either 'Voltage [V]' or 'Working electrode
                                           potential [V]', along with 'Current [A]' and
                                           'Time [s]'.
            Frequency experiments: 'freq [Hz]', 'ReZ [Ohm]', 'ImZ [Ohm]'

        Args:
            data (pd.DataFrame): The DataFrame to be checked. It should contain data
                                 from experiments.

        Returns:
            int: A confirmation 0 integer saying the sanity check has passed.

        Raises:
            ValueError: If any required columns are missing based on the determined
                        experiment type. or if the three electrode data doesn't make
                        sense working - counter = voltage
        """
        check_normal = ["Current [A]", "Time [s]"]
        check_either_normal = [("Voltage [V]", "Working electrode potential [V]",
                                "Counter electrode potential [V]")]
        check_freq = ["freq [Hz]", "ReZ [Ohm]", "ImZ [Ohm]"]

        # Determine if the data is likely a frequency experiment
        is_freq_experiment = any(col in data.columns for col in check_freq)
        is_normal_experiment = \
            any(col in data.columns for col_pair in check_either_normal
                for col in col_pair)\
            or \
            any(col in data.columns for col in check_normal)

        if is_freq_experiment or not is_normal_experiment:
            # Check for missing columns in frequency experiments
            missing_freq = [col for col in check_freq if col not in data.columns]
            if missing_freq:
                self.logger.warning(f"Frequency data is missing {missing_freq} for\
                                    experiments")
                raise ValueError(f"Your frequency data is missing the following\
                                 columns:{', '.join(missing_freq)}")
        else:
            # Check for missing columns in normal experiments
            missing_normal = [col for col in check_normal if col not in data.columns]
            missing_either = all(col not in data.columns for col_pair in
                                 check_either_normal for col in col_pair)

            # Raise error noting the missing columns from the data
            if missing_normal or missing_either:
                missing_cols = ', '.join(missing_normal)
                if missing_either:
                    missing_cols += '; At least one of each pair is required: '\
                        + ', '.join([' or '.join(pair) for pair in check_either_normal])
                self.logger.warning(f"Data is missing {missing_cols} for experiments")
                raise ValueError(f"Your data is missing the following columns for\
                                 normal experiments: {missing_cols}")

        # Check that the thre electrode voltage data makes sense
        three_el = ["Working electrode potential [V]",
                    "Counter electrode potential [V]",
                    "Voltage [V]"]
        if all(elem in data.columns for elem in three_el):
            check = (data["Working electrode potential [V]"].abs() -
                     data["Counter electrode potential [V]"].abs()).abs()
            if not (check - data["Voltage [V]"]).abs().lt(0.02).all():
                self.logger.warning("Voltage data in three electrode experiment is\
                                    corrupted")
                raise ValueError("Your voltage data is corrupted")

        self.logger.info("Sanity check passed")
        return 0

    def data_importer(
        self,
        path_or_file: Path,
        cycler: str = "",
        file_type: str = "csv",
        save_option: str = "save",
        state_option: str = "",
        print_option: str = "",
    ) -> pd.DataFrame:
        """
        Import, process, and optionally save and/or print battery data.

        Args:
            path_or_file (pathlib.path): Path to a directory or file containing battery
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
        self.logger.info("Importing data")
        for file in self.look_for_files(path_or_file):
            # Process each file
            self.logger.info(f"Processing file, {file}")
            pointer, encoding, equipment_type = self.find_words(file, cycler)
            self.logger.info(f"Pointer and encoding found for file, {file}")
            metadata, data = self.split_file(pointer, file, save_option)
            self.logger.info(f"File, {file}, split into metadata and data")
            data = self.read_data_to_pandas(data, file, encoding)
            data = self.change_units(data)
            data = self.change_headers(data)
            data = self.remove_unwanted(data)
            try:
                data = self.absolute_time(metadata, data, encoding)
                self.sanity_check(data)
            except Exception as e:
                self.logger.warning(f"An error occurred: {e} when processing {file}")
            self.logger.info(f"Data imported from file, {file}")
            if state_option == "yes":
                try:
                    data = add_state_label(data)
                    self.logger.info(f"State labels added to file, {file}")
                except Exception as e:
                    self.logger.warning(
                        f"An error occurred: {e} when processing {file}"
                    )
            # Save the file if the option is set to 'save all' or 'save'
            if save_option in ["save all", "save"]:
                save_file(data, file_type, file)
                self.logger.info(f"File, {file}, saved")
            # Print the dataframe and the plots if print_option is 'yes' or all
            if print_option in ["yes", "diff"]:
                try:
                    display_data(data)
                    self.logger.info(f"Data displayed for file, {file}")
                except Exception as e:
                    self.logger.error(f"An error occurred: {e} when processing {file}")
            # Print the diff on current and voltage if print_option is 'all'
            if print_option == "diff":
                try:
                    plot_current_voltage_diff(data)
                except Exception as e:
                    self.logger.error(f"An error occurred: {e} when processing {file}")

        # Return the data from the last file processed, or None if all failed
        return data
