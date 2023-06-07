"""This module deletes all files in the given directory."""
import os
import glob
import time
from pathlib import Path


def clear_directory(path_: str) -> bool:
    """
    !!Takes the download folder PATH. 3 trials to check if the directory has been completely emptied.
    :param path_: PATH to the folder where the files will be deleted
    :return: Returns True if all files are deleted inn less than 3 trials
    """
    trials = 0
    while len(glob.glob(path_ + r"\*")) != 0 and trials < 3:
        [f.unlink() for f in Path(path_).glob("*") if f.is_file()]
        trials += 1
        time.sleep(1)
    if trials == 3:
        return False
    else:
        return True
