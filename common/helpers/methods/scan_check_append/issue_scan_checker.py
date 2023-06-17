import json
import os


def is_issue_scanned(vol_num: int, issue_num: int, path_: str) -> bool:
    """
    It is very important to name scanned issues json as latest_scanned_issue.json in the same directory.
    :param vol_num: Volume number passed to the function
    :param issue_num: Issue number passed to the function
    :param path_: PATH value of the script, "__file__" should be used
    :return: Returns boolean value, True if the issue has already been scanned
    """
    try:
        scanned_issues_path = os.path.join(path_, "latest_scanned_issue.json")
        json_file = open(scanned_issues_path, encoding='utf-8')
        scanned_issue_dict = json.load(json_file)
        """
        Sample:
        {
            "lastScannedVolume": 0,
            "lastScannedIssue": 0,
            "lastEdited": ""
        }
        """
        last_scanned_volume = scanned_issue_dict['lastScannedVolume']
        last_scanned_issue = scanned_issue_dict['lastScannedIssue']
        is_issue_scanned = True
        json_file.close()

        if last_scanned_volume < vol_num or (last_scanned_volume == vol_num and last_scanned_issue < issue_num):
            is_issue_scanned = False
            return is_issue_scanned

        return is_issue_scanned
    except FileNotFoundError:
        raise Exception("Scanned issues file does not exist!")
    except KeyError:
        raise Exception("Contents of issues file is corrupted!")


if __name__ == "__main__":
    print(is_issue_scanned(1, 1, r"C:\Users\emine\PycharmProjects\Article-Search\downloads_n_logs\dergipark_manual"
                                 r"\monday_first80_drg\15_ankemdergisi\logs"))
