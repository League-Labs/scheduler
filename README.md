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
   GITHUB_TOKEN=your_github_personal_access_token
   GITHUB_TEAM=https://github.com/orgs/your-org/teams/your-team
   GITHUB_TEAM_TTL=3600
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
   GITHUB_TOKEN=your_github_personal_access_token
   GITHUB_TEAM=https://github.com/orgs/your-org/teams/your-team
   GITHUB_TEAM_TTL=3600
   FLASK_SECRET_KEY=dev_key
   MONGO_URI=mongodb://localhost:27017/scheduler
   ```

2. Run the Flask development server:

   ```bash
   just dev
   ```

## GitHub Team Integration

The application can restrict access to only members of a specific GitHub team:

1. Set up a GitHub Personal Access Token with `read:org` scope:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate a new token with the `read:org` scope
   - Copy the token to the `GITHUB_TOKEN` environment variable

2. Configure the GitHub team URL in the `GITHUB_TEAM` environment variable:
   - Format: `https://github.com/orgs/your-org/teams/your-team`
   - Only members of this team will be allowed to log in

3. Set the cache TTL for team member data in seconds:
   - `GITHUB_TEAM_TTL=3600` (default: 1 hour)
   - This reduces the number of API calls to GitHub and improves performance

4. CLI commands for working with GitHub teams:
   - List all teams in an organization: `python cli.py teams your-org`
   - List all members of a team: `python cli.py members your-org/your-team`
   - Check cache status: `python cli.py cache-status`

The application caches team membership data in MongoDB with a TTL index to automatically expire old entries.

## Development with Docker

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
