# Justfile for League Labs Scheduler

# Run the Flask development server
dev:
    flask run --host=0.0.0.0

# Recreate the database (deletes and recreates)
recreate-db: 
    python3 init_db.py

build:
    docker build -t scheduler-app .

run:
    docker compose up --build
