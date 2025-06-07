from flask_dance.consumer.storage import BaseStorage
from flask import session
import datetime
from datetime import timezone
import logging
import os
from urllib.parse import urlparse
from pymongo import MongoClient

logger = logging.getLogger(__name__)

class MongoStorage(BaseStorage):
    """
    MongoDB-backed storage for OAuth tokens using Flask-Session.
    """
    def __init__(self, session_key="oauth_token"):
        self.session_key = session_key
        super().__init__()

    def get(self, blueprint):
        key = f"{blueprint.name}_{self.session_key}"
        return session.get(key)

    def set(self, blueprint, token):
        key = f"{blueprint.name}_{self.session_key}"
        session[key] = token
        return token

    def delete(self, blueprint):
        key = f"{blueprint.name}_{self.session_key}"
        if key in session:
            del session[key]

def cache_team_members(db=None, org_name=None, team_slug=None, members=None):
    """
    Cache team members list in MongoDB with TTL
    
    Args:
        db: MongoDB database connection (if None, gets from environment)
        org_name: GitHub organization name
        team_slug: GitHub team slug
        members: List of team members
        ttl_seconds: Time-to-live in seconds (default: 1 hour)
        
    Returns:
        True if successfully cached, False otherwise
    """
    try:
        # Connect to MongoDB if not provided
        if db is None:
            db = get_mongo_connection()
        if db is None:
            return False
            
        if not org_name or not team_slug or not members:
            logger.error("Missing required parameters for caching team members")
            return False
        
        # Get TTL from environment or use default (1 hour)
        ttl_seconds = int(os.environ.get('GITHUB_TEAM_TTL', 3600))
        
        # Ensure the collection exists with TTL index
        if 'github_teams_cache' not in db.list_collection_names():
            db.create_collection('github_teams_cache')


        # Cache key is a combination of org and team
        cache_key = f"{org_name}/{team_slug}"
        
        # Store in MongoDB with expiration
        db.github_teams_cache.update_one(
            {'cache_key': cache_key},
            {
                '$set': {
                    'org_name': org_name,
                    'team_slug': team_slug,
                    'members': members,
                    'updated_at': datetime.datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        logger.info(f"Cached {len(members)} members for team {cache_key}")
        return True
    except Exception as e:
        logger.error(f"Failed to cache team members: {e}")
        return False

def get_cached_team_members(db, org_name, team_slug):
    """
    Get cached team members from MongoDB
    
    Args:
        db: MongoDB database connection
        org_name: GitHub organization name
        team_slug: GitHub team slug
        
    Returns:
        List of team members or None if not in cache or expired
    """
    cache_key = f"{org_name}/{team_slug}"
    cached = db.github_teams_cache.find_one({'cache_key': cache_key})
    
    if cached:

        logger.info(f"Cache hit for team {cache_key}, found {len(cached['members'])} members")
        return cached.get('members')
    else:
        logger.info(f"Cache miss for team {cache_key}")
        return None
        
def get_mongo_connection():
    """Get MongoDB connection from environment variables."""
    mongo_uri = os.environ.get('MONGO_URI')
    if not mongo_uri:
        logger.error("MONGO_URI environment variable not set")
        return None
    
    try:
        client = MongoClient(mongo_uri)
        # Get the database name from the URI
        db_name = urlparse(mongo_uri).path.strip('/') or 'scheduler'
        db = client[db_name]
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None

def invalidate_team_cache(db=None, org_name=None, team_slug=None):
    """
    Invalidate the team members cache in MongoDB.
    
    Args:
        db: MongoDB database connection (if None, gets from environment)
        org_name: GitHub organization name (None to invalidate all)
        team_slug: GitHub team slug (None to invalidate all for the org)
        
    Returns:
        Number of cache entries invalidated
    """
    # Connect to MongoDB if not provided
    if db is None:
        db = get_mongo_connection()
    if db is None:
        return 0
    
    try:
        query = {}
        if org_name:
            query['org_name'] = org_name
            if team_slug:
                query['team_slug'] = team_slug
        
        result = db.github_teams_cache.delete_many(query)
        count = result.deleted_count
        if org_name and team_slug:
            logger.info(f"Invalidated cache for team {org_name}/{team_slug}")
        elif org_name:
            logger.info(f"Invalidated cache for all teams in organization {org_name}")
        else:
            logger.info(f"Invalidated all team caches")
        
        return count
    except Exception as e:
        logger.error(f"Failed to invalidate team cache: {e}")
        return 0

def get_cache_status(db=None):
    """
    Get status of the team cache.
    
    Args:
        db: MongoDB database connection (if None, gets from environment)
    
    Returns:
        Dictionary with cache status information
    """
    # Connect to MongoDB if not provided
    if db is None:
        db = get_mongo_connection()
    if db is None:
        return {"error": "Could not connect to MongoDB"}
    
    try:
        # Check if collection exists
        if 'github_teams_cache' not in db.list_collection_names():
            return {
                "total_cached_teams": 0,
                "teams": []
            }
            
        # Get all cached teams
        cached_teams = list(db.github_teams_cache.find())
        
        now = datetime.datetime.now(timezone.utc)
        result = {
            "total_cached_teams": len(cached_teams),
            "teams": []
        }
        
        for team in cached_teams:
            try:
                # Get required fields with defaults to avoid KeyError
                org_name = team.get('org_name', 'unknown')
                team_slug = team.get('team_slug', 'unknown')
                members = team.get('members', [])
                member_count = len(members)

                updated_at = team.get('updated_at', now)

                # Format times for display
                updated_at_str = updated_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(updated_at, 'strftime') else 'unknown'

                
                result["teams"].append({
                    "org_name": org_name,
                    "team_slug": team_slug,
                    "member_count": member_count,
                    "updated_at": updated_at_str,

                })
            except Exception as e:
                logger.warning(f"Skipping team entry due to error: {e}")
                continue
        
        return result
    except Exception as e:
        logger.error(f"Failed to get cache status: {e}")
        return {"error": str(e)}
