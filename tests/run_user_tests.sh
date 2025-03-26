#!/bin/bash

# Script to run all the PyNews User functionality tests

echo "Running PyNews User functionality tests..."
echo "---------------------------------------------"

cd "$(dirname "$0")"

# Ensure parent directory is in PYTHONPATH
export PYTHONPATH="..:$PYTHONPATH"

echo "1. Running User fetching functionality tests (test_user_fetch.py)"
python -m unittest test_user_fetch.py

echo "---------------------------------------------"
echo "All User functionality tests completed!"