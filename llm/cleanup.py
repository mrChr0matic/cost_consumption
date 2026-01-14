# llm/cleanup.py
import os
import shutil


def safe_delete_file(path: str):
    try:
        if path and os.path.isfile(path):
            os.remove(path)
            print(f"Deleted file: {path}")
    except Exception as e:
        print(f"Warning: could not delete file {path}: {e}")


def safe_delete_dir_if_empty(dir_path: str):
    try:
        if os.path.isdir(dir_path) and not os.listdir(dir_path):
            os.rmdir(dir_path)
            print(f"Deleted empty directory: {dir_path}")
    except Exception as e:
        print(f"Warning: could not delete directory {dir_path}: {e}")


def cleanup_local_files(excel_path: str = None, temp_image_paths: list[str] = None):
    """
    Deletes:
    1. Excel output file
    2. Temp images
    3. Empty use_case_name directory
    4. Empty client_name directory
    """

    # -------------------------
    # Delete Excel file
    # -------------------------
    if excel_path:
        safe_delete_file(excel_path)

        # Determine directories
        use_case_dir = os.path.dirname(excel_path)           # client/use_case
        client_dir = os.path.dirname(use_case_dir)           # client

        # Delete use_case directory if empty
        safe_delete_dir_if_empty(use_case_dir)

        # Delete client directory if empty
        safe_delete_dir_if_empty(client_dir)

    # -------------------------
    # Delete temp images
    # -------------------------
    if temp_image_paths:
        for p in temp_image_paths:
            safe_delete_file(p)
