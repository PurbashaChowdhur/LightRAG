"""
This file contains useful I/O functions.
"""

import pickle
import os

def save_to_pkl(obj, filename:str) -> None:
    """
    Saves an object to a pickle file.

    Args:
    - obj: object to save
    - filename: name of the file to save the object
    """
    with open(filename, 'wb') as f:
        pickle.dump(obj, f)

def load_from_pkl(filename:str):
    """
    Loads an object from a pickle file.

    Args:
    - filename: name of the file to load the object from
    """
    with open(filename, 'rb') as f:
        return pickle.load(f)
    
def save_html_from_log(input_file:str, output_file:str) -> None:
    """
    Saves the content of a log file to an HTML file.

    Args:
    - input_file: str, path to the input log file
    - output_file: str, path to the output HTML file
    """
    with open(input_file, "r") as log_file:
        log_content = log_file.read()

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Results</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
            }}
            pre {{
                background: #f4f4f4;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
            }}
        </style>
    </head>
    <body>
        <h1>Model Results</h1>
        <pre>{log_content}</pre>
    </body>
    </html>
    """

    with open(output_file, "w") as html_file:
        html_file.write(html_content)

    print(f"HTML file created: {output_file}")

def create_directories(base_dir:str, sub_dirs:str, timestamp:str) -> tuple:
    """
    Create directories and return log and HTML file paths.
    """

    dir_path = os.path.join(base_dir, *sub_dirs)
    os.makedirs(dir_path, exist_ok=True)
    log_file = os.path.join(dir_path, f'{timestamp}.log')
    html_file = os.path.join(dir_path, f'{timestamp}.html')
    
    return log_file, html_file