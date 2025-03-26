#!/bin/bash

# Script to run all the PyNews Ask HN functionality tests

echo "Running PyNews Ask HN functionality tests..."
echo "---------------------------------------------"

cd "$(dirname "$0")"

# Ensure parent directory is in PYTHONPATH
export PYTHONPATH="..:$PYTHONPATH"

echo "1. Running Ask HN view functionality tests (test_ask_view.py)"
python -m unittest test_ask_view.py

echo "---------------------------------------------"
echo "2. Running Ask HN sorting and filtering tests (test_ask_sorting_filtering.py)"
python -m unittest test_ask_sorting_filtering.py

echo "---------------------------------------------"
echo "3. Running Ask HN integration tests (test_ask_integration.py)"
python -m unittest test_ask_integration.py

echo "---------------------------------------------"
echo "All Ask HN tests completed!"