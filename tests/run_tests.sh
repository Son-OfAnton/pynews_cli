#!/bin/bash

# Script to run all the PyNews comment functionality tests

echo "Running PyNews comment functionality tests..."
echo "---------------------------------------------"

cd "$(dirname "$0")"

echo "1. Running core comment functionality tests (test_comments.py)"
python -m unittest test_comments.py

echo "---------------------------------------------"
echo "2. Running comment display formatting tests (test_comment_display.py)"
python -m unittest test_comment_display.py

echo "---------------------------------------------"
echo "3. Running comment integration tests (test_comment_integration.py)"
python -m unittest test_comment_integration.py

echo "---------------------------------------------"
echo "All tests completed!"