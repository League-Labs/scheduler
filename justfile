# Justfile for League Labs Scheduler

# Run the Flask development server
run:
    flask run --host=0.0.0.0

# Recreate the database (deletes and recreates)
recreate-db:
    rm -f data/scheduler.sqlite3
    python3 init_db.py
