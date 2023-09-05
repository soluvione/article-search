#!/bin/bash

# Activate the virtual environment
source /home/ubuntu/article-search/venv/bin/activate

# Change to the directory of Span9 dispatcher
cd /home/ubuntu/article-search/dispatchers/span9/span9_1-5

# Run the Python script
python span9_dispatcher.py