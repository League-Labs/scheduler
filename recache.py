#!/usr/bin/env python
"""
Thread-based worker for recaching GitHub team members.

This module implements a worker thread that periodically refreshes the GitHub team
members cache in MongoDB to ensure that team membership data is up-to-date.
"""
import os
import time
import threading
import logging
from datetime import datetime, timezone
from pymongo import MongoClient

from gh_api import parse_team_url, list_team_members
from mongo import get_mongo_connection, cache_team_members

# Configure logger
logger = logging.getLogger(__name__)

class RecacheWorker:
    """
    Worker thread that periodically refreshes the GitHub team members cache.
    
    The worker runs in a persistent loop that:
    1. Recaches the data
    2. Waits for GITHUB_TEAM_TTL seconds
    3. Waits for a threading.Event signal (for immediate refresh)
    4. Clears the event
    5. Continues the loop
    """
    
    def __init__(self, ttl_seconds=3600):
        """
        Initialize the recache worker.
        
        Args:
            ttl_seconds: Time to live in seconds for the cache (default: 1 hour)
        """
        self.ttl_seconds = ttl_seconds
        self.thread = None
        self.stop_event = threading.Event()
        self.refresh_event = threading.Event()
        self.is_running = False
        
        # Get GitHub team from environment
        self.github_team = os.environ.get('GITHUB_TEAM')
        if not self.github_team:
            logger.warning("GITHUB_TEAM environment variable not set. Cache worker will not run.")
        else:
            logger.info(f"Initialized RecacheWorker for team: {self.github_team}")
            
        # Try to parse team URL
        self.org_name = None
        self.team_slug = None
        if self.github_team:
            self.org_name, self.team_slug = parse_team_url(self.github_team)
            if not (self.org_name and self.team_slug):
                logger.error(f"Failed to parse GitHub team URL: {self.github_team}")
                self.github_team = None
    
    def start(self):
        """Start the recache worker thread."""
        if self.thread is not None and self.thread.is_alive():
            logger.warning("RecacheWorker thread is already running")
            return
            
        if not self.github_team:
            logger.warning("Cannot start RecacheWorker: GITHUB_TEAM not set or invalid")
            return
            
        logger.info(f"Starting RecacheWorker thread (TTL: {self.ttl_seconds}s)")
        self.stop_event.clear()
        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
    def stop(self):
        """Stop the recache worker thread."""
        if self.thread is None or not self.thread.is_alive():
            logger.debug("RecacheWorker thread is not running")
            return
            
        logger.info("Stopping RecacheWorker thread")
        self.is_running = False
        self.stop_event.set()
        self.refresh_event.set()  # Wake up the thread if it's waiting
        
        # Wait for the thread to terminate
        self.thread.join(timeout=6)  # Increased timeout to be slightly longer than the test wait
        if self.thread.is_alive():
            logger.warning("RecacheWorker thread did not terminate gracefully")
            # Make the thread a daemon so it won't block program exit
            self.thread = None
        else:
            logger.info("RecacheWorker thread stopped successfully")
            
    def trigger_refresh(self):
        """Trigger an immediate refresh of the cache."""
        if self.thread is None or not self.thread.is_alive():
            logger.debug("Cannot trigger refresh: RecacheWorker thread is not running")
            return False
            
        logger.debug("Triggering immediate cache refresh")
        self.refresh_event.set()
        return True
        
    def _run(self):
        """Main thread loop for the recache worker."""
        logger.info("RecacheWorker thread started")
        
        while self.is_running and not self.stop_event.is_set():
            try:
                # Perform cache refresh
                self._refresh_cache()
                
                # Wait for TTL or until refresh is triggered
                logger.debug(f"Waiting {self.ttl_seconds} seconds until next cache refresh")
                wait_start = datetime.now(timezone.utc)
                
                # Wait for either the TTL to expire or the refresh event to be set
                while self.is_running and not self.stop_event.is_set():
                    # Check if we should refresh (either due to timeout or event)
                    elapsed = (datetime.now(timezone.utc) - wait_start).total_seconds()
                    if elapsed >= self.ttl_seconds or self.refresh_event.is_set():
                        break
                    
                    # Wait for a short time or until the refresh event is set
                    wait_remaining = max(0.1, min(5, self.ttl_seconds - elapsed))
                    self.refresh_event.wait(wait_remaining)
                
                # Clear the refresh event if it was set
                if self.refresh_event.is_set():
                    logger.debug("Refresh event triggered")
                    self.refresh_event.clear()
                
            except Exception as e:
                logger.error(f"Error in RecacheWorker thread: {e}", exc_info=True)
                # Wait a bit before retrying to avoid tight loop on persistent errors
                time.sleep(10)
                
        logger.info("RecacheWorker thread exiting")
    
    def _refresh_cache(self):
        """Refresh the GitHub team members cache."""
        # Exit early if stop requested
        if self.stop_event.is_set() or not self.is_running:
            logger.debug("Skipping cache refresh - worker stopping")
            return False
            
        if not (self.org_name and self.team_slug):
            logger.error("Cannot refresh cache: organization or team slug not available")
            return False
            
        try:
            logger.info(f"Refreshing cache for team {self.org_name}/{self.team_slug}")
            
            # Get MongoDB connection
            db = get_mongo_connection()
            if db is None:
                logger.error("Failed to connect to MongoDB for cache refresh")
                return False
                
            # Check again if we should stop before making API calls
            if self.stop_event.is_set() or not self.is_running:
                logger.debug("Stopping cache refresh - worker stopping")
                return False
                
            # Fetch team members from GitHub API
            members = list_team_members(self.org_name, self.team_slug)
            if members is None:
                logger.error(f"Failed to fetch members for team {self.org_name}/{self.team_slug}")
                return False
                
            logger.info(f"Retrieved {len(members)} members for team {self.org_name}/{self.team_slug}")
            
            # Cache the team members in MongoDB
            result = cache_team_members(
                db=db,
                org_name=self.org_name,
                team_slug=self.team_slug,
                members=members
            )
            
            if result:
                logger.info(f"Successfully cached {len(members)} members for team {self.org_name}/{self.team_slug}")
            else:
                logger.error(f"Failed to cache members for team {self.org_name}/{self.team_slug}")
                
            return result
            
        except Exception as e:
            logger.error(f"Error refreshing cache: {e}", exc_info=True)
            return False

# Global instance of the recache worker
_worker = None

def start_recache_worker():
    """Start the global recache worker."""
    global _worker
    
    # Get TTL from environment or use default
    ttl_seconds = int(os.environ.get('GITHUB_TEAM_TTL', 3600))
    
    if _worker is None:
        _worker = RecacheWorker(ttl_seconds=ttl_seconds)
    
    _worker.start()
    return _worker

def stop_recache_worker():
    """Stop the global recache worker."""
    global _worker
    if _worker is not None:
        _worker.stop()
        # Clear the reference to ensure garbage collection
        if _worker.thread and _worker.thread.is_alive():
            # If thread is still alive but we've signaled stop,
            # clear the reference anyway - it's a daemon thread
            _worker = None
        else:
            _worker = None

def trigger_recache():
    """Trigger an immediate recache."""
    global _worker
    if _worker is not None:
        return _worker.trigger_refresh()
    return False

def get_recache_worker():
    """Get the global recache worker instance."""
    global _worker
    return _worker
