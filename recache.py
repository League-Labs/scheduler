#!/usr/bin/env python
"""
Thread-based worker for recaching GitHub team members.

This module implements a worker thread that performs a single refresh of the GitHub team
members cache in MongoDB and then exits. Each call to start_recache_worker() creates
a new worker thread that runs once and terminates.
"""
import os
import time
import threading
import logging
from datetime import datetime, timezone
from pymongo import MongoClient

from gh_api import parse_team_url, list_team_members
from mongo import get_mongo_connection, cache_team_members
from time import time 
# Configure logger
logger = logging.getLogger(__name__)

logger.setLevel(logging.DEBUG)

class RecacheWorker:
    """
    Worker thread that runs one GitHub team members cache refresh and then exits.
    """
    
    def __init__(self, team_uri, ttl_seconds=3600):
        """
        Initialize the recache worker.
        
        Args:
            team_uri: GitHub team URI to cache
        """
        self.thread = None

        self.next_run = time()
        self.ttl_seconds = ttl_seconds
        
        # Get GitHub team from parameter
        self.github_team = team_uri
        if not self.github_team:
            logger.warning("GITHUB_TEAM not provided. Cache worker will not run.")
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
            

        logger.info("Starting RecacheWorker thread for one-time cache refresh")
        self.thread = threading.Thread(target=self._run)
        self.thread.start()
        
    def start_maybe(self):
        """Start the recache worker thread if not already running."""
        if self.thread is not None and self.thread.is_alive():
            logger.debug("RecacheWorker thread is already running")
           
            
        if time() > self.next_run:
            logger.debug("RecacheWorker TTL expired, starting new thread")
            self.next_run = time() + self.ttl_seconds

            self.start()

    def _run(self):
        """Run one cache refresh and exit."""
        logger.info("RecacheWorker thread started")
        self._refresh_cache()
        logger.info("RecacheWorker thread exiting")
    
    def _refresh_cache(self):
        """Refresh the GitHub team members cache."""
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



def stop_recache_worker():
    """No-op function for compatibility. Workers exit automatically."""
    pass

def trigger_recache():
    """Trigger an immediate recache by starting a new worker."""
    return start_recache_worker()

def get_recache_worker():
    """Get the global recache worker instance (deprecated - workers are one-time use)."""
    return None
