#!/usr/bin/env python
"""
Debugging script for recache tests.
"""
import os
import sys

print("Script starting")
print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
print(f"Added to path: {parent_dir}")

try:
    print("Trying to import recache...")
    import recache
    print("Successfully imported recache")
    
    print("Creating RecacheWorker...")
    worker = recache.RecacheWorker()
    print(f"Created worker: {worker}")
    
    # Try basic worker operations
    print("Starting worker...")
    worker.start()
    print("Worker started")
    
    import time
    print("Sleeping for 2 seconds...")
    time.sleep(2)
    
    print("Stopping worker...")
    worker.stop()
    print("Worker stopped")
    
    print("All tests passed!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
