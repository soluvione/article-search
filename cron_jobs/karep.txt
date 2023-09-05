#!/bin/bash

# Activate the virtual environment
source /home/ubuntu/article-search/venv/bin/activate

# Change to the directory of Karep dispatcher
cd /home/ubuntu/article-search/dispatchers/karep/karep_1-3

# Run the Python script
python karep_dispatcher.py