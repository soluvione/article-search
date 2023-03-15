"""
A helper method for writing objects/iterables as .csv files.
"""

import csv
import json
import os
import sys


with open(os.path.join(sys.path[0], "namespace"), "r", encoding='utf-8') as f:
    dict1 = json.loads(f.read())

with open('namespace.csv', 'w', encoding='utf_8_sig') as output:
    writer = csv.writer(output)
    for key, value in dict1.items():
        writer.writerow([key, value])
