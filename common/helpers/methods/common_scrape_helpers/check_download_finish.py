"""This module function has a method to check whether there is an ongoing Chrome download at given folder"""
import time
import os


def check_download_finish(downloads_path: str, is_long=False) -> bool:
    """
    Has a timeout value of 20 seconds. If the download takes longer than 20 seconds than the process will be terminated.
    :param is_long: Is the download will take place for a site that has long download times?
    :param downloads_path: PATH to the download folder
    :return: Returns True if there are no ongoing downloads at the given folder at the time of execution.
    """
    seconds = 0
    if is_long:
        while seconds < 80:
            time.sleep(1)
            ongoing_downloads = 0
            for file_name in os.listdir(downloads_path):
                if file_name.endswith('.crdownload'):
                    ongoing_downloads += 1
            if ongoing_downloads == 0:
                return True
            seconds += 1
        return False
    else:
        while seconds < 20:
            time.sleep(1)
            ongoing_downloads = 0
            for file_name in os.listdir(downloads_path):
                if file_name.endswith('.crdownload'):
                    ongoing_downloads += 1
            if ongoing_downloads == 0:
                return True
            seconds += 1
        return False
