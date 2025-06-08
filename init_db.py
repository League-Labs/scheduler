import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.environ.get('MONGO_URI')

client = MongoClient(MONGO_URI)
default_db = client.get_default_database()
db = default_db if default_db is not None else client['scheduler']

# Ensure collections and indexes exist
def init_db():
    # Get the list of existing collections first to avoid errors
    existing_collections = db.list_collection_names()
    
    # Create main collections if they don't exist
    if 'users' not in existing_collections:
        db.create_collection('users', capped=False)
    if 'userteam' not in existing_collections:
        db.create_collection('userteam', capped=False)
    if 'teams' not in existing_collections:
        db.create_collection('teams', capped=False)
    
    # Create GitHub team cache collection with TTL index
    if 'github_teams_cache' not in existing_collections:
        db.create_collection('github_teams_cache')

    
    # Create cache key index for faster lookups
    db.github_teams_cache.create_index('cache_key', unique=True)
    
    # Create indexes for main collections
    db.users.create_index('username', unique=True)
    db.userteam.create_index([('user_id', 1), ('team', 1)], unique=True)
    db.teams.create_index('team_name', unique=True)
    
    # Add test users if not present
    for username in ['test1', 'test2', 'test3']:
        db.users.update_one({'username': username}, {'$setOnInsert': {'username': username}}, upsert=True)

if __name__ == '__main__':
    init_db()
    print('MongoDB initialized at', MONGO_URI)
