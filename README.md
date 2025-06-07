# scheduler
An application for picking meeting times.

## Environment Configuration

The application uses different environment files for development and Docker deployment:

- `.env` - Used for local development
- `.env.docker` - Used for Docker deployment

## Docker Deployment

To run the application in production using Docker Compose:

1. Configure your `.env.docker` file with appropriate settings:

   ```
   # Docker environment configuration
   GITHUB_OAUTH_CLIENT_ID=your_client_id
   GITHUB_OAUTH_CLIENT_SECRET=your_client_secret
   FLASK_SECRET_KEY=secure_random_key
   MONGO_URI=mongodb://mongo:27017/scheduler
   EXTERNAL_URL=https://your-domain.com
   ```

2. Start the application and MongoDB:

   ```bash
   just run
   ```

## Development Setup

For local development:

1. Configure your `.env` file with development settings:

   ```
   GITHUB_OAUTH_CLIENT_ID=your_dev_client_id
   GITHUB_OAUTH_CLIENT_SECRET=your_dev_client_secret
   FLASK_SECRET_KEY=dev_key
   MONGO_URI=mongodb://localhost:27017/scheduler
   ```

2. Run the Flask development server:

   ```bash
   just dev
   ```

For development with Docker:

```bash
just dev-docker
```

## Commands

- `just dev` - Run the local Flask development server
- `just run` - Run the application with Docker Compose
- `just run-detached` - Run Docker in detached mode
- `just stop` - Stop Docker containers
- `just dev-docker` - Run Docker with development settings
docker compose down
```

Data is persisted in a Docker volume named `mongo_data`.
