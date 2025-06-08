import json
import logging
import os
from collections import defaultdict
from datetime import datetime
from functools import wraps
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from dotenv import load_dotenv
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for, current_app)
from flask.sessions import SecureCookieSessionInterface
from flask_dance.contrib.github import github, make_github_blueprint
from flask_session import Session
from pymongo import MongoClient

from gh_api import list_team_members, parse_team_url
from mongo import MongoStorage, get_or_new_team
from recache import RecacheWorker

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

    app.github_team = os.environ.get('GITHUB_TEAM')


    # Start initial cache refresh if GITHUB_TEAM is set
    if app.github_team:
        logger.info("Starting initial GitHub team cache refresh")
        app.recache_worker = RecacheWorker(app.github_team)
    else:
        logger.info("GITHUB_TEAM not set, no initial cache refresh")
        app.recache_worker = None

    app.logger = logger

    return app



def init_db(db):
    # Get the list of existing collections first to avoid errors
    existing_collections = db.list_collection_names()
    
    # Create collections only if they do not exist
    if 'users' not in existing_collections:
        db.create_collection('users', capped=False)
    if 'userteam' not in existing_collections:
        db.create_collection('userteam', capped=False)
    
    # Create GitHub team cache collection 
    if 'github_teams_cache' not in existing_collections:
        db.create_collection('github_teams_cache')
    
    # Create cache key index for faster lookups
    db.github_teams_cache.create_index('cache_key', unique=True)
    
    # Ensure other indexes exist
    db.users.create_index('username', unique=True)
    db.userteam.create_index([('user_id', 1), ('team', 1)], unique=True)
    
    # Add test users if not present
    for username in ['test1', 'test2', 'test3']:
        db.users.update_one({'username': username}, {'$setOnInsert': {'username': username}}, upsert=True)

app = init_app()

# Set up logger
logger = logging.getLogger("scheduler")
logging.basicConfig(level=logging.INFO)


def cache_result(ttl=20):
    """
    Decorator to cache function results for a specified number of seconds.
    
    Args:
        ttl: Time to live in seconds (default: 20 seconds)
    """
    def decorator(func):
        cache = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = datetime.now()
            cache_key = str(args) + str(kwargs)
            
            # Check if we have a valid cached result
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if (now - timestamp).total_seconds() < ttl:
                    return result
            
            # Get fresh result
            result = func(*args, **kwargs)
            cache[cache_key] = (result, now)
            return result
            
        return wrapper
    return decorator


@cache_result(ttl=20)
def get_team_members():
    
    logger.info("Fetching team members from cache")
    org, team = parse_team_url(current_app.github_team)
    # Get cached team members from MongoDB
    cache_key = f"{org}/{team}"
    team_cache = app.db.github_teams_cache.find_one({"cache_key": cache_key})

    if team_cache and 'members' in team_cache:
        members = [m['login'] for m in team_cache['members']]
    else:
        members = None

    # Check if the cache is too old and needs refreshing
    if team_cache and 'updated_at' in team_cache:
        cache_age = (datetime.now() - team_cache['updated_at']).total_seconds()
      
        team_ttl = int(os.environ.get('GITHUB_TEAM_TTL', 3600))  # Default to 1 hour
        
        logger.info(f"Team cache age: {cache_age:.1f}s (TTL: {team_ttl}s)")
        
        if cache_age > team_ttl and app.recache_worker:
            logger.info("Cache too old, triggering refresh")
            app.recache_worker.start()

    elif app.recache_worker and members is None:
        # If we have no cached data at all, trigger a refresh
        logger.info("No cache data found, triggering refresh")
        app.recache_worker.start()


    return members




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
            # Get the team_name from the URL if it exists (from route parameters)
            session['next'] = request.url
        
            team_name = kwargs.get('team_name')
            pw = kwargs.get('pw')

            if team_name and pw:
                return redirect(url_for('password_access', team=team_name, pw=pw))
            else:
                return redirect(url_for('login' ))
        
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

        # Check team membership if GITHUB_TEAM is configured
        if app.github_team:
            members = get_team_members()

            if members and github_username not in members:
                logger.warning(f"Unauthorized login attempt by {github_username}")
                # If not a team member, log them out and redirect to homepage
                app.logout_user()
                flash(f"User {github_username} is not authorized to access this application.", 'error')
                return redirect(url_for('index'))


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

# --- GET and POST /<team>/password ---
@app.route('/<team>/password', methods=['GET', 'POST'])
def password_access(team):
    """Handle password access for protected teams"""
  
    team_doc = get_or_new_team(app.db, None, team)

    if team_doc is None:
        flash('Team does not exist.', 'error')
        return redirect(url_for('index'))

    # Store destination in session to redirect after successful password entry
    session['password_redirect'] = url_for('team_page', team_name=team)
    
    if request.method == 'POST':
        email = request.form.get('username')

        if not email or '@' not in email:
            flash('Please enter a valid email address.', 'error')
            return redirect(request.url)
        
        app.login_user(email)
      
        return redirect(url_for('team_page', team_name=team))
    
    else:
        pw = request.args.get('pw')

        if pw != team_doc.get('password'):
            flash('Password required to access this team.', 'warning')
            return redirect(url_for('index'))
        
        return render_template('password_access.html', team=team, url=request.url)


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
@app.route('/<team_name>/', strict_slashes=False)
@login_required
def team_page(team_name):
    # Store the current team in the session

    if team_name == 'favicon.ico':
        return '', 204

    session['current_team'] = team_name
    user = app.get_current_user()

    team = get_or_new_team(app.db, user, team_name)
    
    if team['password']:

        # Check if password is set and add it to the URL
        if team['password']:
            team['url'] = url_for('team_page', team_name=team_name, pw=team['password'], _external=True)
        else:
            team['url'] = None
       

    return render_template('team.html', team=team, user=user)
   
# --- GET and POST /<team>/selections ---
@app.route('/<team_name>/set_passwords', methods=[ 'POST'])
@login_required_api
def set_team_password(team_name):

    user = app.get_current_user()
    team = get_or_new_team(app.db, user, team_name)
    
    # Only the team creator can set/change passwords
    if team.get('creator_id') != user:
        flash('Only the team creator can change password settings.', 'error')
        return redirect(url_for('team_page', team_name=team_name))
        
    # Handle form submissions
    new_password = request.form.get('password')
    require_for_all = 'require_for_all' in request.form
    
    # Update the team in the database
    app.db.teams.update_one(
        {'_id': team['_id']},
        {'$set': {
            'password': new_password,
            'require_for_all': require_for_all
        }}
    )
    
    flash('Password settings updated successfully.', 'success')
    return redirect(url_for('team_page', team_name=team_name))



# In your Flask app, ensure the database is initialized on startup if not present
if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5000, debug=True)
