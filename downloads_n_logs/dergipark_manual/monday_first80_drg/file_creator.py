import json
import os

with open(
        'C:\Users\emine\PycharmProjects\Article-Search\dispatchers\dergipark\dergipark_first80\dergipark_1-80_params.json',
        'r', encoding='utf-8') as f:
    params_data = json.load(f)
i = 0
# journal_name, start_page_url, pages_to_send, pdf_scrape_type, parent_type, file_reference
for param_item in params_data:
    if i > 2:
        break
    first_level = param_item[4]
    second_level = param_item[-1]
    prefix_path = r'C:\Users\emine\PycharmProjects\Article-Search\downloads_n_logs\dergipark_manual\monday_first80_drg'
    abs_path = os.path.join(prefix_path, second_level)
    os.makedirs(os.path.join(abs_path, 'logs'))
    os.makedirs(os.path.join(abs_path, 'downloads'))
    with open(os.path.join(abs_path, 'logs') + r'\latest_scanned_issue.json', 'w') as f:
        f.write(json.dumps({
            "Last scanned Volume": 0,
            "Last scanned Issue": 0,
            "Edited on": ""
        }, indent=4))
    with open(os.path.join(abs_path, 'logs') + r'\scanned_article_dois.json', 'w') as f:
        f.write(json.dumps([]))
    with open(os.path.join(abs_path, 'logs') + r'\scanned_article_urls.json', 'w') as f:
        f.write(json.dumps([]))
    with open(os.path.join(abs_path, 'logs') + r'\logs.json', 'w') as f:
        f.write(json.dumps([]))
    i += 1