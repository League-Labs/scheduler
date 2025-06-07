#!/usr/bin/env python
"""
Debug script to test if multiple recache workers are running.
"""
import os
import time
import threading
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up test environment
os.environ['GITHUB_TEAM'] = 'https://github.com/orgs/testorg/teams/testteam'
os.environ['GITHUB_TEAM_TTL'] = '10'

# Import after setting environment
from recache import start_recache_worker, stop_recache_worker, get_recache_worker, _worker
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def count_recache_threads():
    """Count the number of RecacheWorker threads running."""
    count = 0
    for thread in threading.enumerate():
        if 'RecacheWorker' in str(thread) or 'recache' in thread.name.lower():
            count += 1
            logger.info(f"Found thread: {thread}")
    return count

def main():
    logger.info("=== Testing RecacheWorker for multiple instances ===")
    
    # Initial state
    logger.info(f"Initial global worker: {_worker}")
    logger.info(f"Initial thread count: {count_recache_threads()}")
    
    # Start first worker
    logger.info("\n--- Starting first worker ---")
    worker1 = start_recache_worker()
    logger.info(f"Worker1: {worker1}")
    logger.info(f"Worker1 running: {worker1.is_running if worker1 else 'N/A'}")
    logger.info(f"Worker1 thread alive: {worker1.thread.is_alive() if worker1 and worker1.thread else 'N/A'}")
    logger.info(f"Global worker: {_worker}")
    logger.info(f"Thread count after first start: {count_recache_threads()}")
    
    time.sleep(2)
    
    # Start second worker (should return existing)
    logger.info("\n--- Starting second worker ---")
    worker2 = start_recache_worker()
    logger.info(f"Worker2: {worker2}")
    logger.info(f"Worker1 == Worker2: {worker1 is worker2}")
    logger.info(f"Global worker: {_worker}")
    logger.info(f"Thread count after second start: {count_recache_threads()}")
    
    time.sleep(2)
    
    # Stop worker
    logger.info("\n--- Stopping worker ---")
    stop_recache_worker()
    logger.info(f"Global worker after stop: {_worker}")
    logger.info(f"Thread count after stop: {count_recache_threads()}")
    
    time.sleep(2)
    
    # Check final state
    logger.info("\n--- Final state ---")
    logger.info(f"Final thread count: {count_recache_threads()}")
    
    # List all threads
    logger.info("\n--- All threads ---")
    for thread in threading.enumerate():
        logger.info(f"Thread: {thread}")

if __name__ == '__main__':
    main()
