#!/bin/bash

# Activate the virtual environment
source /home/ubuntu/article-search/venv/bin/activate

# Change to the directory of PKP dispatcher
cd /home/ubuntu/article-search/dispatchers/pkp/pkp_1-20

# Run the Python script
python pkp_1-20.py