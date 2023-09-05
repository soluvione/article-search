#!/bin/bash

# Activate the virtual environment
source /home/ubuntu/article-search/venv/bin/activate

# Change to the directory of Firat dispatcher
cd /home/ubuntu/article-search/dispatchers/firat/firat_1-5

# Run the Python script
python firat_dispatcher.py