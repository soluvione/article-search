"""This module deletes all files in the given directory."""
import os
import glob
import time
from pathlib import Path

from common.errors import GeneralError
from common.services.send_notification import send_notification


def clear_directory(path_: str) -> bool:
    """
    !!Takes the download folder PATH. 3 trials to check if the directory has been completely emptied.
    :param path_: PATH to the folder where the files will be deleted
    :return: Returns True if all files are deleted inn less than 3 trials
    """
    trials = 0
    while any(Path(path_).iterdir()) and trials < 3:
        try:
            for f in Path(path_).iterdir():
                if f.is_file():
                    f.unlink()
                elif f.is_dir():
                    clear_directory(str(f))  # recursively delete subdirectories
                    f.rmdir()  # remove the now-empty subdirectory
            trials += 1
            time.sleep(1)
        except Exception as e:
            send_notification(GeneralError(f"Error while clearing the directory. Error encountered: {e}"))
            return False
    if trials == 3:
        return False
    else:
        try:
            with open(os.path.join(path_, '.gitkeep'), 'w'):   # Create .gitkeep
                pass
        except Exception as e:
            send_notification(GeneralError(f"Error while creating gitkeep file at downloads directory. Error encountered: {e}"))
            return False

        return True
"""
Old version:
def clear_directory(path_: str) -> bool:
    ""
    !!Takes the download folder PATH. 3 trials to check if the directory has been completely emptied.
    :param path_: PATH to the folder where the files will be deleted
    :return: Returns True if all files are deleted inn less than 3 trials
    ""
    trials = 0
    while len(glob.glob(os.path.join(path_, "*"))) != 0 and trials < 3:
        [f.unlink() for f in Path(path_).glob("*") if f.is_file()]
        trials += 1
        time.sleep(1)
    if trials == 3:
        return False
    else:
        return True
"""
if __name__ == "__main__":
    print(clear_directory("/home/emin/Desktop/tk_downloads"))