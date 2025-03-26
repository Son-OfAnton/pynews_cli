#!/bin/bash

# Script to run all the PyNews Job listings functionality tests

echo "Running PyNews Job listings functionality tests..."
echo "---------------------------------------------"

cd "$(dirname "$0")"

# Ensure parent directory is in PYTHONPATH
export PYTHONPATH="..:$PYTHONPATH"

echo "1. Running Job view functionality tests (test_job_view.py)"
python -m unittest test_job_view.py

echo "---------------------------------------------"
echo "2. Running Job integration tests (test_job_integration.py)"
python -m unittest test_job_integration.py

echo "---------------------------------------------"
echo "3. Running Job interactive and advanced features tests (test_job_interactive.py)"
python -m unittest test_job_interactive.py

echo "---------------------------------------------"
echo "All Job listings tests completed!"