from flask import Flask, session, redirect, url_for, request, jsonify
from flask.sessions import SecureCookieSessionInterface
import json
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'dev-secret-key'  # For development only

# --- Test users for development ---
TEST_USERS = ['test1', 'test2', 'test3']

# --- In-memory storage for userteam selections (for Sprint2, replace with DB later) ---
userteam_selections = defaultdict(dict)  # {team: {user: [dayhours]}}

# --- Session helper ---
def login_user(username):
    session.clear()
    session['user'] = username

def logout_user():
    session.clear()

def get_current_user():
    return session.get('user')

# --- Login stub ---
@app.route('/login')
def login():
    # This is a stub for Github login
    return 'Login page (stub)', 200

# --- Test user login via query param ---
@app.before_request
def handle_test_user_login():
    test_user = request.args.get('user')
    if test_user in TEST_USERS:
        logout_user()
        login_user(test_user)
        # Remove the ?user= param and redirect to the same path without it
        from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
        url = urlparse(request.url)
        query = parse_qs(url.query)
        query.pop('user', None)
        new_query = urlencode(query, doseq=True)
        new_url = urlunparse((url.scheme, url.netloc, url.path, url.params, new_query, url.fragment))
        return redirect(new_url)

# --- Hello route ---
@app.route('/hello')
def hello():
    user = get_current_user()
    if not user:
        # Save original URL and redirect to login
        session['next'] = request.url
        return redirect(url_for('login'))
    return f"hello {user}", 200

# --- Root route (for completeness, not required in Sprint 1) ---
@app.route('/')
def index():
    return 'League Labs Scheduler Home', 200

# --- GET and POST /<team>/selections ---
@app.route('/<team>/selections', methods=['GET', 'POST'])
def team_selections(team):
    user = get_current_user()
    if not user:
        session['next'] = request.url
        return redirect(url_for('login'))
    if request.method == 'GET':
        selections = userteam_selections[team].get(user, [])
        return jsonify(selections)
    # POST: Save selections
    data = request.get_json(force=True)
    if not isinstance(data, list):
        return jsonify({'error': 'Selections must be a list'}), 400
    userteam_selections[team][user] = data
    return jsonify({'status': 'ok'})

# --- GET /<team>/info ---
@app.route('/<team>/info', methods=['GET'])
def team_info(team):
    team_data = userteam_selections[team]
    users = list(team_data.keys())
    count = len(users)
    dayhours = defaultdict(int)
    for sel in team_data.values():
        for dh in sel:
            dayhours[dh] += 1
    return jsonify({
        'name': team,
        'count': count,
        'users': users,
        'dayhours': dict(dayhours)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
