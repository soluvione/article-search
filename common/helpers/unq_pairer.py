import pprint
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import pandas as pd
from bs4 import BeautifulSoup, Tag
import requests
import zss


# Function to fetch HTML
def fetch_html(url):
    try:
        response = requests.get(url, verify=False)
        return response.text
    except requests.exceptions.SSLError as e:
        print(f"SSL error encountered for URL: {url}")
        print(f"Error details: {e}")
        return ""
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error encountered for URL: {url}")
        print(f"Error details: {e}")
        return ""
# Define functions required by zss to work with BeautifulSoup tags
def get_children(tag):
    return [child for child in tag.children if isinstance(child, Tag)]


def get_label(tag):
    return tag.name


# Compare two BeautifulSoup tags using tree edit distance
def compare_trees(tree1, tree2):
    return zss.simple_distance(tree1, tree2, get_children, get_label)


xlx_file = "/home/emin/Desktop/unq.xlsx"
# Read the excel file, there is no column names
df = pd.read_excel(xlx_file, header=None)
# save the second column as a list
urls = df[1].tolist()


# Fetch and parse HTML for each URL
parsed_htmls = {url: BeautifulSoup(fetch_html(url), 'html.parser') for url in urls}

# Dictionary to store the groups
groups = {}

# Threshold for structural similarity (you may need to adjust this value)
THRESHOLD = 5  # example value, you might need to tweak this

# Grouping pages based on structure similarity
for url1, html1 in parsed_htmls.items():
    added = False
    for group, members in groups.items():
        representative = members[0]

        # Clearing contents for representative HTML
        for tag in parsed_htmls[representative].find_all(True):
            if tag.name not in ['html', 'head', 'body']:
                tag.clear()

        # Clearing contents for the current HTML being compared
        for tag in html1.find_all(True):
            if tag.name not in ['html', 'head', 'body']:
                tag.clear()

        distance = compare_trees(parsed_htmls[representative], html1)

        # Check if the distance is below the threshold
        if distance < THRESHOLD:
            groups[group].append(url1)
            added = True
            break

    if not added:
        # This page structure is distinct enough to start a new group
        groups[url1] = [url1]

# Print grouped URLs based on similar structure
for group, group_urls in groups.items():
    pprint.pprint(f"Group: {group}, URLs: {', '.join(group_urls)}", indent=4, width=150)
