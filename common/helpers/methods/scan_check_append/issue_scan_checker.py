import json
import os

def is_issue_scanned(vol_num: int, issue_num: int, path_: str) -> bool:
    """

    :param vol_num: Volume number passed to the function
    :param issue_num: Issue number passed to the function
    :param path_: PATH of the logs folder
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
        last_scanned_volume = int(scanned_issue_dict['lastScannedVolume'])
        last_scanned_issue = scanned_issue_dict['lastScannedIssue']
        is_issue_scanned = True
        json_file.close()

        if int(last_scanned_volume) < int(vol_num) or (int(last_scanned_volume) == int(vol_num) and int(last_scanned_issue) < int(issue_num)):
            is_issue_scanned = False
            return is_issue_scanned

        return is_issue_scanned
    except FileNotFoundError:
        raise Exception("Scanned issues file does not exist! (is_issue_scanned, issue_scan_checker.py)")
    except KeyError:
        raise Exception("Contents of issues file is corrupted!")


def tk_no_ref_is_scanned(recent_text: str, path_: str) -> bool:
    try:
        scanned_issues_path = os.path.join(path_, "latest_scanned_issue.json")
        with open(scanned_issues_path, 'r', encoding='utf-8') as json_file:
            scanned_issue_dict = json.load(json_file)
            """
            Sample:
            {
                "lastScannedText": (23.03.2023),
                "lastEdited": ""
            }
            """
            if scanned_issue_dict['lastScannedText']:
                last_scanned_text = scanned_issue_dict['lastScannedText'].replace("(", "").replace(")", "")
            else:
                last_scanned_text = recent_text.strip().replace("(", "").replace(")", "")
            scanned_month, scanned_year = int(last_scanned_text.split(".")[1]), \
                int(last_scanned_text.split(".")[2])
            recent_text = recent_text.replace("(", "").replace(")", "")
            recent_month, recent_year = int((recent_text.split(".")[1])), \
                int(recent_text.split(".")[2])

            if recent_year > scanned_year or recent_month > scanned_month:
                return False

            return True
    except FileNotFoundError:
        raise Exception("Scanned issues file does not exist! (tk_no_ref_is_scanned, issue_scan_checker.py)")
    except KeyError:
        raise Exception("Contents of issues file is corrupted!")


if __name__ == "__main__":
    print(is_issue_scanned(1, 1, r"C:\Users\emine\PycharmProjects\Article-Search\downloads_n_logs\dergipark_manual"
                                 r"\monday_first80_drg\15_ankemdergisi\logs"))
