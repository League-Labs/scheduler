import json
import logging
import os
import random
import string
from collections import defaultdict
from datetime import datetime
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import (Flask, Response, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from flask.sessions import SecureCookieSessionInterface

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

    # Configure client-side session storage
    app.config['SESSION_TYPE'] = 'cookie'
    app.config['SESSION_PERMANENT'] = True
    app.config['SESSION_USE_SIGNER'] = True
    
    # Set up data directory
    app.config['DATA_DIR'] = os.environ.get('DATA_DIR', '/data')
    
    # Ensure data directory exists
    os.makedirs(app.config['DATA_DIR'], exist_ok=True)
    
    app.logger = logger

    return app

# Register custom Jinja2 filters
def to_json(value):
    return json.dumps(value)

app = init_app()
app.jinja_env.filters['to_json'] = to_json

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

def generate_random_id(length=12):
    """Generate a random alphanumeric ID"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_schedule_path(schedule_id):
    """Get the path for a schedule's data file"""
    data_dir = app.config['DATA_DIR']
    return os.path.join(data_dir, f"s_{schedule_id}.json")

def get_user_path(schedule_id, user_id):
    """Get the path for a user's data file"""
    data_dir = app.config['DATA_DIR']
    return os.path.join(data_dir, f"u_{schedule_id}_{user_id}.json")

def get_schedule_data(schedule_id):
    """Get schedule data from file"""
    file_path = get_schedule_path(schedule_id)
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading schedule data: {e}")
        return None

def save_schedule_data(schedule_id, data):
    """Save schedule data to file"""
    file_path = get_schedule_path(schedule_id)
    
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f)
        return True
    except Exception as e:
        logger.error(f"Error saving schedule data: {e}")
        return False

def get_user_data(schedule_id, user_id):
    """Get user data from file"""
    file_path = get_user_path(schedule_id, user_id)
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading user data: {e}")
        return None

def save_user_data(schedule_id, user_id, data):
    """Save user data to file"""
    file_path = get_user_path(schedule_id, user_id)
    
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f)
        return True
    except Exception as e:
        logger.error(f"Error saving user data: {e}")
        return False

def get_all_users_for_schedule(schedule_id):
    """Get all users who have responded to a schedule"""
    data_dir = app.config['DATA_DIR']
    prefix = f"u_{schedule_id}_"
    users = []
    
    try:
        for filename in os.listdir(data_dir):
            if filename.startswith(prefix) and filename.endswith('.json'):
                user_id = filename[len(prefix):-5]  # Remove prefix and .json extension
                user_data = get_user_data(schedule_id, user_id)
                if user_data and 'name' in user_data:
                    users.append({
                        'id': user_id,
                        'name': user_data.get('name', 'Anonymous'),
                        'selections': user_data.get('selections', [])
                    })
        return users
    except Exception as e:
        logger.error(f"Error listing users for schedule: {e}")
        return []

def name_required(f):
    """Decorator to check if user has set a name"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'name' not in session:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Name required'}), 403
            flash('Please enter your name to continue.', 'warning')
            return redirect(url_for('set_name', next=request.path))
        return f(*args, **kwargs)
    return decorated_function




# --- Main page ---
@app.route('/')
def index():
    return render_template('index.html')

# --- Create a new schedule ---
@app.route('/new')
def new_schedule():
    schedule_id = generate_random_id()
    
    # Create a new user ID if one doesn't exist
    if 'user_id' not in session:
        session['user_id'] = generate_random_id()
    
    # Create and save empty schedule data
    schedule_data = {
        'id': schedule_id,
        'created_at': datetime.now().isoformat(),
        'creator_id': session.get('user_id')
    }
    
    save_schedule_data(schedule_id, schedule_data)
    
    # Redirect to the schedule page
    return redirect(url_for('schedule_page', schedule_id=schedule_id))

# --- Set name form ---
@app.route('/set_name', methods=['GET', 'POST'])
def set_name():
    next_url = request.args.get('next', url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('Please enter a name.', 'error')
            return redirect(url_for('set_name', next=next_url))
        
        session['name'] = name
        return redirect(next_url)
    
    return render_template('set_name.html', next=next_url)

# --- Schedule page ---
@app.route('/s/<schedule_id>')
def schedule_page(schedule_id):
    # Get schedule data
    schedule_data = get_schedule_data(schedule_id)
    if not schedule_data:
        flash('Schedule not found.', 'error')
        return redirect(url_for('index'))
    
    # Create a new user ID if one doesn't exist
    if 'user_id' not in session:
        session['user_id'] = generate_random_id()
    
    user_id = session.get('user_id')
    
    # Get all users who have responded
    users = get_all_users_for_schedule(schedule_id)
    
    schedule_url = url_for('schedule_page', schedule_id=schedule_id, _external=True)
    user_url = url_for('user_page', schedule_id=schedule_id, user_id=user_id, _external=True)
    
    return render_template('schedule.html', 
                          schedule=schedule_data, 
                          users=users, 
                          user_id=user_id,
                          schedule_url=schedule_url,
                          user_url=user_url)

# --- User page ---
@app.route('/u/<schedule_id>/<user_id>')
def user_page(schedule_id, user_id):
    # Get schedule data
    schedule_data = get_schedule_data(schedule_id)
    if not schedule_data:
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Schedule not found'}), 404
        # Otherwise show the error page
        flash('Schedule not found.', 'error')
        return redirect(url_for('index'))
    
    # Get user data
    user_data = get_user_data(schedule_id, user_id)
    
    # Get all users who have responded
    users = get_all_users_for_schedule(schedule_id)
    
    current_user_id = session.get('user_id')
    is_owner = (current_user_id == user_id)
    is_read_only_json = json.dumps(not is_owner)
    
    schedule_url = url_for('schedule_page', schedule_id=schedule_id, _external=True)
    
    return render_template('user.html', 
                          schedule=schedule_data, 
                          user_data=user_data,
                          users=users,
                          user_id=user_id,
                          is_owner=is_owner,
                          is_read_only_json=is_read_only_json,
                          schedule_url=schedule_url)

# --- Get schedule info ---
@app.route('/s/<schedule_id>/info', methods=['GET'])
def schedule_info(schedule_id):
    # Use explicit API response headers to ensure JSON content type
    headers = {'Content-Type': 'application/json'}
    
    try:
        app.logger.info(f"schedule_info: Getting info for schedule {schedule_id}")
        
        # Check if schedule exists first
        schedule_path = get_schedule_path(schedule_id)
        if not os.path.exists(schedule_path):
            app.logger.warning(f"Schedule not found: {schedule_id}")
            error_response = json.dumps({"error": "Schedule not found"})
            return Response(error_response, status=404, headers=headers)
        
        # Load schedule data
        schedule_data = get_schedule_data(schedule_id)
        if not schedule_data:
            app.logger.warning(f"Failed to load schedule data: {schedule_id}")
            error_response = json.dumps({"error": "Failed to load schedule data"})
            return Response(error_response, status=500, headers=headers)
        
        # Get users and process data
        users = get_all_users_for_schedule(schedule_id)
        count = len(users)
        
        # Build simple response object
        response_data = {
            'id': schedule_id,
            'count': count,
            'dayhours': {}
        }
        
        # Aggregate all selections
        for user in users:
            for dh in user.get('selections', []):
                if dh not in response_data['dayhours']:
                    response_data['dayhours'][dh] = 0
                response_data['dayhours'][dh] += 1
        
        # Return JSON with proper headers
        success_response = json.dumps(response_data)
        return Response(success_response, status=200, headers=headers)
        
    except Exception as e:
        app.logger.error(f"Error in schedule_info: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        error_response = json.dumps({"error": str(e)})
        return Response(error_response, status=500, headers=headers)
    except Exception as e:
        app.logger.error(f"Error in schedule_info: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return app.response_class(
            response=json.dumps({"error": str(e)}),
            status=500,
            mimetype='application/json'
        )

# --- Get user selections ---
@app.route('/u/<schedule_id>/<user_id>/selections', methods=['GET', 'POST'])
def user_selections(schedule_id, user_id):
    current_user_id = session.get('user_id')
    
    # For GET requests, anyone can view
    if request.method == 'GET':
        user_data = get_user_data(schedule_id, user_id)
        selections = user_data.get('selections', []) if user_data else []
        return jsonify(selections)
    
    # For POST requests, only the owner can update
    if current_user_id != user_id:
        return jsonify({'error': 'Not authorized'}), 403
    
    # Name is required to save selections
    if 'name' not in session:
        return jsonify({'error': 'Name required'}), 403
    
    data = request.get_json(force=True)
    if not isinstance(data, list):
        return jsonify({'error': 'Selections must be a list'}), 400
    
    # Get existing data or create new
    user_data = get_user_data(schedule_id, user_id) or {}
    user_data.update({
        'name': session.get('name'),
        'selections': data,
        'updated_at': datetime.now().isoformat()
    })
    
    save_user_data(schedule_id, user_id, user_data)
    return jsonify({'status': 'ok'})




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
