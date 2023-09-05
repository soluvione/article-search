#!/bin/bash

# Change to the directory of the project
cd /home/ubuntu/article-search

# Pull changes
git pull

# Add changes in working directory
git add .

# Commit changes with week data in the message
current_week=$(date +"%U-%Y")
git commit -m "Weekly Project Update for Week ${current_week}"

# Push changes
git push