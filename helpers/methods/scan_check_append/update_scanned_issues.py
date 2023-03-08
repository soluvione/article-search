import json
from pathlib import Path
from datetime import datetime


def update_scanned_issues(vol_num: int, issue_num: int, path_: str):
    scanned_issues_path = Path(path_).parent / "latest_scanned_issue.json"
    last_scanned_items = {'Last scanned Volume': vol_num,
                          'Last scanned Issue': issue_num,
                          'Edited on': datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}

    try:
        with open(scanned_issues_path, 'w') as json_file:
            json_file.write(json.dumps(last_scanned_items, indent=4))

        return True

    except FileNotFoundError:
        raise Exception("Could not update the issue records!")
        return False
