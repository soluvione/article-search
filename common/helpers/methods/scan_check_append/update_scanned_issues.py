"""
This module updates the local scanned issues json file and writes the newly scanned issue to the json
alongside the date and time of modification
"""

import json
from pathlib import Path
from datetime import datetime


def update_scanned_issues(vol_num: int, issue_num: int, path_: str):
    """
    It is very important to have the local latest_scanned_issue.json file.
    :param vol_num: Volume number passed to the function
    :param issue_num: Issue number passed to the function
    :param path_: PATH value of the script, "__file__" should be used
    :return: Returns True updating was successful
    """
    scanned_issues_path = Path(path_).parent / "latest_scanned_issue.json"
    last_scanned_items = {'Last scanned Volume': vol_num,
                          'Last scanned Issue': issue_num,
                          'Edited on': datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}

    try:
        with open(scanned_issues_path, 'w') as json_file:
            json_file.write(json.dumps(last_scanned_items, indent=4))

        return True

    except FileNotFoundError:
        print("Could not update the issue records!")
        return False
