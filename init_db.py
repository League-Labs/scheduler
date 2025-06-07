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
    db.create_collection('users', capped=False)
    db.create_collection('userteam', capped=False)
    db.users.create_index('username', unique=True)
    db.userteam.create_index([('user_id', 1), ('team', 1)], unique=True)
    # Add test users if not present
    for username in ['test1', 'test2', 'test3']:
        db.users.update_one({'username': username}, {'$setOnInsert': {'username': username}}, upsert=True)

if __name__ == '__main__':
    init_db()
    print('MongoDB initialized at', MONGO_URI)
