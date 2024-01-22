import os
import pandas as pd


def save_file(data: pd.DataFrame, file_type: str, file_path: str) -> str:
    """
    Save the cleaned DataFrame to the specified file type.

    Args:
        data (pd.DataFrame): The input DataFrame containing battery data.
        file_type (str): The desired file type for saving
                        (csv, parquet, pickle, feather).
        file_path (str): The path of the original input file.

    Returns:
        str: The path to the saved output file.

    Raises:
        ValueError: If an unsupported file type is provided.
    """
    # Get the directory containing the input file
    current_dir = os.path.dirname(file_path)
    # Create a subdirectory to store the output file
    output_dir = os.path.join(current_dir, "processed")
    os.makedirs(output_dir, exist_ok=True)
    # Extract the file name and extension from the input file path
    file_name, file_ext = os.path.splitext(os.path.basename(file_path))
    output_path = os.path.join(output_dir, file_name)

    # Save the dataframe to the file type in the output directory
    if file_type == "csv":
        new_file_name = f"{file_name}_cleaned_data.csv"
        output_path = os.path.join(output_dir, new_file_name)
        data.to_csv(output_path, index=False)
    elif file_type == "parquet":
        new_file_name = f"{file_name}_cleaned_data.parquet"
        output_path = os.path.join(output_dir, new_file_name)
        data.to_parquet(output_path, index=False)
    elif file_type == "pickle":
        new_file_name = f"{file_name}_cleaned_data.pickle"
        output_path = os.path.join(output_dir, new_file_name)
        data.to_pickle(output_path)
    elif file_type == "feather":
        new_file_name = f"{file_name}_cleaned_data.feather"
        output_path = os.path.join(output_dir, new_file_name)
        data.to_feather(output_path, index=False)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    return output_path
