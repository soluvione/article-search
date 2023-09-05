#!/bin/bash

# Activate the virtual environment
source /home/ubuntu/article-search/venv/bin/activate

# Change to the directory of Dergi Plarformu dispatcher
cd /home/ubuntu/article-search/dispatchers/dergi_platformu/dergi_platformu_1-5

# Run the Python script
python dergi_platformu_dispatcher.py