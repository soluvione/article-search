#!/bin/bash

# Activate the virtual environment
source /home/ubuntu/article-search/venv/bin/activate

# Change to the directory of Dergipark 1-80 dispatcher
cd /home/ubuntu/article-search/dispatchers/dergipark/dergipark_first80

# Run the Python script
python first80_drg.py