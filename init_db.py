DATABASE_PATH = '/data/scheduler.sqlite3'

import os
import sqlite3

def get_db():
    if not os.path.exists('/data'):
        os.makedirs('/data')
    db_exists = os.path.exists(DATABASE_PATH)
    conn = sqlite3.connect(DATABASE_PATH)
    if not db_exists:
        create_db(conn)
    return conn

def create_db(conn):
    c = conn.cursor()
    c.execute('''CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL
    )''')
    c.execute('''CREATE TABLE userteam (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        team TEXT NOT NULL,
        selections TEXT NOT NULL,
        UNIQUE(user_id, team)
    )''')
    # Add test users
    for username in ['test1', 'test2', 'test3']:
        c.execute('INSERT INTO users (username) VALUES (?)', (username,))
    conn.commit()

if __name__ == '__main__':
    get_db()
    print('Database initialized at', DATABASE_PATH)
