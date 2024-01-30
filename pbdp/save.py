from pathlib import Path
import pandas as pd
import logging


def save_file(data: pd.DataFrame, file_type: str, file_path: Path) -> str:
    """
    Save the cleaned DataFrame to the specified file type.

    Args:
        data (pd.DataFrame): The input DataFrame containing battery data.
        file_type (str): The desired file type for saving
                        (csv, parquet, pickle, feather).
        file_path (Path): The path of the original input file.

    Returns:
        str: The path to the saved output file.

    Raises:
        ValueError: If an unsupported file type is provided.
    """
    # Get the directory containing the input file
    current_dir = file_path.parent
    # Create a subdirectory to store the output file
    output_dir = current_dir / "processed"
    output_dir.mkdir(exist_ok=True)
    logging.info(f"Output directory created at {output_dir}")
    # Extract the file name and extension from the input file path
    file_name = file_path.name.split(".")[0]
    output_path = output_dir / file_name
    logging.info(f"Output file name: {output_path}")

    # Save the dataframe to the file type in the output directory
    if file_type == "csv":
        new_file_name = f"{file_name}_cleaned_data.csv"
        output_path = output_dir / new_file_name
        data.to_csv(output_path, index=False)
        logging.info(f"Output csv file saved at {output_path}")
    elif file_type == "parquet":
        new_file_name = f"{file_name}_cleaned_data.parquet"
        output_path = output_dir / new_file_name
        data = data.applymap(lambda x: pd.to_numeric(x, errors='coerce'))
        data.to_parquet(output_path, index=False)
        logging.info(f"Output parquet file saved at {output_path}")
    elif file_type == "pickle":
        new_file_name = f"{file_name}_cleaned_data.pickle"
        output_path = output_dir / new_file_name
        data.to_pickle(output_path)
        logging.info(f"Output pickle file saved at {output_path}")
    elif file_type == "feather":
        new_file_name = f"{file_name}_cleaned_data.feather"
        output_path = output_dir / new_file_name
        data.to_feather(output_path, index=False)
        logging.info(f"Output feather file saved at {output_path}")
    else:
        logging.warning(f"Unsupported file type: {file_type}")
        raise ValueError(f"Unsupported file type: {file_type}")

    return output_path
