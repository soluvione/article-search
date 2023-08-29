"""
This helper method can be run anywhere but must run on Windows, it is os dependant. Other than that, the params file
path must be adjusted and the target folder as well.
"""
import json
import os

def create_files_from_params():
    with open(
            r'C:\Users\BT-EMIN\PycharmProjects\article-search\dispatchers\wolters_kluwer\wolters_kluwer_1-4\wolters_kluwer_1-4_params.json',
            'r', encoding='utf-8') as f:
        params_data = json.load(f)
    # journal_name, start_page_url, pages_to_send, pdf_scrape_type, parent_type, file_reference
    for param_item in params_data:
        first_level = param_item[4]
        second_level = param_item[-1]
        prefix_path = r'C:\Users\BT-EMIN\PycharmProjects\article-search\downloads_n_logs\wolters_kluwer_manual\sunday_1-4_wolters_kluwer'
        abs_path = os.path.join(prefix_path, second_level)
        os.makedirs(os.path.join(abs_path, 'logs'))
        os.makedirs(os.path.join(abs_path, 'downloads'))
        with open(os.path.join(abs_path, 'logs') + r'\latest_scanned_issue.json', 'w') as f:
            f.write(json.dumps({
                "lastScannedVolume": 0,
                "lastScannedIssue": 0,
                "lastEdited": ""
            }, indent=4))
        with open(os.path.join(abs_path, 'logs') + r'\scanned_article_dois.json', 'w') as f:
            f.write(json.dumps([]))
        with open(os.path.join(abs_path, 'downloads') + r'\.gitkeep', 'w') as f:
            pass
        with open(os.path.join(abs_path, 'logs') + r'\scanned_article_urls.json', 'w') as f:
            f.write(json.dumps([]))
        with open(os.path.join(abs_path, 'logs') + r'\logs.json', 'w') as f:
            f.write(json.dumps([]))

if __name__ == "__main__":
    create_files_from_params()