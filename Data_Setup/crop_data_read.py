import numpy as np
import pandas as pd


def read_crop_data(file_path):
    """
    Reads crop data from a CSV file and returns it as a pandas DataFrame.

    Parameters:
    file_path (str): The path to the CSV file containing crop data.

    Returns:
    pd.DataFrame: A DataFrame containing the crop data.
    """
    try:
        crop_data = pd.read_csv(file_path)
        return crop_data
    except Exception as e:
        print(f"An error occurred while reading the crop data: {e}")
        return None
    

