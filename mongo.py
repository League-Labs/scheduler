from flask_dance.consumer.storage import BaseStorage
from flask import session
import datetime
import logging

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

def cache_team_members(db, org_name, team_slug, members, ttl_seconds=3600):
    """
    Cache team members list in MongoDB with TTL
    
    Args:
        db: MongoDB database connection
        org_name: GitHub organization name
        team_slug: GitHub team slug
        members: List of team members
        ttl_seconds: Time-to-live in seconds (default: 1 hour)
    """
    # Ensure the collection exists with TTL index
    if 'github_teams_cache' not in db.list_collection_names():
        db.create_collection('github_teams_cache')
        # Create TTL index on the expires_at field
        db.github_teams_cache.create_index('expires_at', expireAfterSeconds=0)
    
    # Calculate expiration time
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=ttl_seconds)
    
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
                'expires_at': expires_at,
                'updated_at': datetime.datetime.utcnow()
            }
        },
        upsert=True
    )
    logger.info(f"Cached {len(members)} members for team {cache_key}, expires at {expires_at}")

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
        # Check if it's still valid (MongoDB TTL might have a delay in deletion)
        if cached.get('expires_at') > datetime.datetime.utcnow():
            logger.info(f"Cache hit for team {cache_key}, found {len(cached['members'])} members")
            return cached.get('members')
        else:
            logger.info(f"Cache expired for team {cache_key}")
            return None
    else:
        logger.info(f"Cache miss for team {cache_key}")
        return None
