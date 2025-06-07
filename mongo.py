from flask_dance.consumer.storage import BaseStorage
from flask import session

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
