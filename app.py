import atexit
import json
import logging
import os
from collections import defaultdict
from functools import wraps
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from dotenv import load_dotenv
from flask import (Flask, jsonify, redirect, render_template, request, session,
                   url_for)
from flask.sessions import SecureCookieSessionInterface
from flask_dance.contrib.github import github, make_github_blueprint
from flask_session import Session
from pymongo import MongoClient

from gh_api import parse_team_url
from mongo import MongoStorage
from recache import start_recache_worker, stop_recache_worker

import logging

logger = logging.getLogger(__name__)

def init_app():
    # Load environment variables from .env
    load_dotenv()
    
    # Try loading .env.docker if we're in a Docker environment
    if os.path.exists('.env'):
        load_dotenv('.env', override=True)

    app = Flask(__name__)
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')  # For development only
    
    # Set server name if EXTERNAL_URL is defined to ensure correct URL generation
    external_url = os.environ.get('EXTERNAL_URL')
    if external_url:
        parsed = urlparse(external_url)
        app.config['SERVER_NAME'] = parsed.netloc
        
    # Trust proxy headers for HTTPS detection when behind reverse proxy
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    
    # Tell Flask that it's behind a proxy - handle X-Forwarded-Proto, Host, For headers
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_for=1)

    # Allow OAuth over http in debug mode for development
    if app.debug or os.environ.get('FLASK_ENV') == 'development':
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    # --- Test users for development ---
    TEST_USERS = ['test1', 'test2', 'test3']
    app.config['TEST_USERS'] = TEST_USERS

    # --- In-memory storage for userteam selections (for Sprint2, replace with DB later) ---
    userteam_selections = defaultdict(dict)  # {team: {user: [dayhours]}}
    app.userteam_selections = userteam_selections

    # --- Session helper ---
    def login_user(username):
        session.clear()
        session['user'] = username
    app.login_user = login_user

    def logout_user():
        if 'user' in session:
            session.pop('user')
        if 'current_team' in session:
            session.pop('current_team')
        session.clear()
    app.logout_user = logout_user

    def get_current_user():
        return session.get('user')
    app.get_current_user = get_current_user

    # Register Flask-Dance Github blueprint
    GITHUB_CLIENT_ID = os.environ.get('GITHUB_OAUTH_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_OAUTH_CLIENT_SECRET')
    
    # Connect to MongoDB
    client = MongoClient(os.environ.get('MONGO_URI'))
    default_db = client.get_default_database()
    db = default_db if default_db is not None else client['scheduler']
    app.db = db

    # Configure MongoDB for session storage
    app.config['SESSION_TYPE'] = 'mongodb'
    app.config['SESSION_MONGODB'] = client
    app.config['SESSION_MONGODB_DB'] = db.name
    app.config['SESSION_MONGODB_COLLECT'] = 'sessions'
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session lifetime
    app.config['SESSION_USE_SIGNER'] = True
    
    # Initialize Flask-Session
    Session(app)
    
    # Configure Flask-Dance to use HTTPS for OAuth callback with custom MongoDB storage
    github_bp = make_github_blueprint(
        client_id=GITHUB_CLIENT_ID,
        client_secret=GITHUB_CLIENT_SECRET,
        redirect_to='github_authorized',
        redirect_url=None,  # Let Flask-Dance build the URL based on app config
        scope='user:email',
        storage=MongoStorage()
    )
    
    # Set OAuth parameters to always prompt for account selection
    github_bp.session.params["prompt"] = "select_account"
    
    app.register_blueprint(github_bp, url_prefix="/login")

    init_db(db)

    # Start the GitHub team recache worker if GITHUB_TEAM is set
    if os.environ.get('GITHUB_TEAM'):
        logger.info("Starting GitHub team recache worker")
        recache_worker = start_recache_worker()
        # Register cleanup handler to stop the worker when the app exits
        atexit.register(stop_recache_worker)
    else:
        logger.info("GITHUB_TEAM not set, recache worker not started")

    app.logger = logger

    return app



def init_db(db):
    # Create collections only if they do not exist
    if 'users' not in db.list_collection_names():
        db.create_collection('users', capped=False)
    if 'userteam' not in db.list_collection_names():
        db.create_collection('userteam', capped=False)
    # Ensure indexes exist
    db.users.create_index('username', unique=True)
    db.userteam.create_index([('user_id', 1), ('team', 1)], unique=True)
    # Add test users if not present
    for username in ['test1', 'test2', 'test3']:
        db.users.update_one({'username': username}, {'$setOnInsert': {'username': username}}, upsert=True)

app = init_app()

# Set up logger
logger = logging.getLogger("scheduler")
logging.basicConfig(level=logging.INFO)


@app.after_request
def after_request(response):
    """
    After request handler to potentially trigger cache refresh.
    This is a placeholder for Sprint 10 implementation.
    """
    # The actual implementation for team membership validation will be in Sprint 10
    return response


@app.before_request
def handle_test_user_login():
    test_user = request.args.get('user')
    if test_user in app.config['TEST_USERS']:
        logger.info(f"Setting test user: {test_user}")
        app.logout_user()
        app.login_user(test_user)
        # Remove the ?user= param and redirect to the same path without it
        url = urlparse(request.url)
        query = parse_qs(url.query)
        query.pop('user', None)
        new_query = urlencode(query, doseq=True)
        # Ensure we use the correct scheme when generating URLs
        scheme = request.headers.get('X-Forwarded-Proto', url.scheme)
        new_url = urlunparse((scheme, url.netloc, url.path, url.params, new_query, url.fragment))
        return redirect(new_url)
    

# Ensure correct URL schemes in generated URLs
@app.before_request
def fix_scheme():
    scheme = request.headers.get('X-Forwarded-Proto')
    if scheme and scheme == 'https':
        request.environ['wsgi.url_scheme'] = 'https'
        # This is important for Flask-Dance OAuth
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '0'
    elif app.debug or os.environ.get('FLASK_ENV') == 'development':
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = app.get_current_user()
        if not user:
            session['next'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def login_required_api(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = app.get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function    # --- Login route override to use Github login ---
@app.route('/login')
def login():
    # Check if already logged in
    user = app.get_current_user()
    if user:
        return redirect(url_for('index'))
    
    # Clear any existing OAuth tokens to force new login
    if hasattr(github, 'token'):
        del github.token
        
    if github.authorized:
        user_resp = github.get('/user')
        if user_resp.ok:
            app.login_user(user_resp.json().get('login'))
            next_url = session.pop('next', url_for('index'))
            return redirect(next_url)
    
    # Redirect to GitHub OAuth login
    return redirect(url_for('github.login'))

# --- After Github OAuth, set session and redirect ---
@app.route('/login/github/auth') # DO NOT CHANGE THIS ROUTE!
def github_authorized():
    if not github.authorized:
        logger.error("GitHub OAuth not authorized in callback")
        return redirect(url_for('github.login'))
    
    try:
        user_resp = github.get('/user')
        if not user_resp.ok:
            logger.error(f"Failed to fetch user from GitHub: {user_resp.text}")
            return 'Failed to fetch user info from Github', 400
        
        github_username = user_resp.json().get('login')
        if not github_username:
            logger.error("No username found in GitHub response")
            return 'No username found in GitHub response', 400
        
            
        logger.info(f"Successful GitHub login for user: {github_username}")
        app.login_user(github_username)
        
        # Store GitHub user in the database
        db = app.db
        db.users.update_one(
            {'username': github_username}, 
            {'$set': {'username': github_username, 'github_data': user_resp.json()}},
            upsert=True
        )
        
        next_url = session.pop('next', url_for('index'))
        return redirect(next_url)
    except Exception as e:
        logger.exception("Error in GitHub authorization callback")
        return f"Error during GitHub login: {str(e)}", 500

# --- Hello route ---
@app.route('/hello')
@login_required
def hello():
    user = app.get_current_user()
    return render_template('hello.html', user=user)

# --- Root route: List teams with user counts ---
@app.route('/')
def index():


    # Get all teams from the database with user counts
    db = app.db
    pipeline = [
        {"$group": {"_id": "$team", "user_count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}  # Sort by team name
    ]
    team_data = list(db.userteam.aggregate(pipeline))
    
    # Format the data for the template
    teams_with_counts = [{"name": team["_id"], "count": team["user_count"]} for team in team_data]
    
    return render_template('index.html', teams=teams_with_counts)

# --- GET and POST /<team>/selections ---
@app.route('/<team>/selections', methods=['GET', 'POST'])
@login_required_api
def team_selections(team):
    user = app.get_current_user()
    db = app.db
    if request.method == 'GET':
        doc = db.userteam.find_one({'user_id': user, 'team': team})
        selections = doc['selections'] if doc and 'selections' in doc else []
        return jsonify(selections)
    # POST: Save selections
    data = request.get_json(force=True)
    if not isinstance(data, list):
        return jsonify({'error': 'Selections must be a list'}), 400
    db.userteam.update_one(
        {'user_id': user, 'team': team},
        {'$set': {'selections': data}},
        upsert=True
    )
    return jsonify({'status': 'ok'})

# --- GET /<team>/info ---
@app.route('/<team>/info', methods=['GET'])
@login_required
def team_info(team):
    db = app.db
    team_docs = list(db.userteam.find({'team': team}))
    users = [doc['user_id'] for doc in team_docs]
    count = len(users)
    dayhours = defaultdict(int)
    for doc in team_docs:
        for dh in doc.get('selections', []):
            dayhours[dh] += 1
    return jsonify({
        'name': team,
        'count': count,
        'users': users,
        'dayhours': dict(dayhours)
    })

# --- Team page stub ---
@app.route('/<team>/', strict_slashes=False)
@login_required
def team_page(team):
    # Store the current team in the session
    session['current_team'] = team

    user = app.get_current_user()
    return render_template('team.html', team=team, user=user)
   


# --- Logout route ---
@app.route('/logout')
def logout():
    # Clear the Flask-Dance OAuth token
    if hasattr(github, 'token'):
        del github.token
    
    # Clear the user session
    app.logout_user()
    
    # Clear any other session data that might remain
    session.clear()
    
    # Create a response that will delete the session cookie
    response = redirect(url_for('index'))
    
    # Delete the session cookie by setting its expiration to immediately
    response.set_cookie('session', '', expires=0)
    
    return response


# In your Flask app, ensure the database is initialized on startup if not present
if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5000, debug=True)
