# Justfile for League Labs Scheduler

# Run the Flask development server
dev:
    flask run --host=0.0.0.0

# Recreate the database (deletes and recreates)
recreate-db: 
    python3 init_db.py

build:
    docker build -t scheduler-app .

# Run the Docker application with all services
run:
    docker compose up --build

# Run Docker in detached mode
run-detached:
    docker compose up -d --build

# Stop Docker containers
stop:
    docker compose down

# Run Docker for development with local MongoDB access
dev-docker:
    docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
