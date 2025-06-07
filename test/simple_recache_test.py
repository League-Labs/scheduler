#!/usr/bin/env python
"""
Simple test for the RecacheWorker implementation.
"""
import os
import sys
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import dotenv for environment variables
from dotenv import load_dotenv
load_dotenv()

# Import the module to test
import recache

class SimpleRecacheTest(unittest.TestCase):
    """Simple test case for basic functionality."""
    
    def test_import(self):
        """Test that we can import the recache module."""
        self.assertIsNotNone(recache)
        self.assertTrue(hasattr(recache, 'RecacheWorker'))
    
    def test_worker_creation(self):
        """Test that we can create a RecacheWorker instance."""
        worker = recache.RecacheWorker()
        self.assertIsNotNone(worker)

if __name__ == '__main__':
    unittest.main()
