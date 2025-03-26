#!/bin/bash

# Script to run all the PyNews Poll stories functionality tests

echo "Running PyNews Poll stories functionality tests..."
echo "---------------------------------------------"

cd "$(dirname "$0")"

# Ensure parent directory is in PYTHONPATH
export PYTHONPATH="..:$PYTHONPATH"

echo "1. Running Poll view functionality tests (test_poll_view.py)"
python -m unittest test_poll_view.py

echo "---------------------------------------------"
echo "All Poll stories tests completed!"