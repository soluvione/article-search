#!/bin/bash

# Activate the virtual environment
source /home/ubuntu/article-search/venv/bin/activate

# Change to the directory of Wolters Kluwer dispatcher
cd /home/ubuntu/article-search/dispatchers/wolters_kluwer/wolters_kluwer_1-4

# Run the Python script
python wolters_kluwer_dispatcher.py