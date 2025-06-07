# scheduler
An application for picking meeting times.

## Docker Deployment

To run the application in production using Docker Compose:

1. Ensure your `.env` file contains the correct `MONGO_URI` for Docker Compose:

   ```
   # For Docker Compose, uncomment the following line:
   # MONGO_URI=mongodb://mongo:27017/scheduler
   ```

2. Build the Docker image:

   ```bash
   just build-docker
   ```

3. Start the application and MongoDB:

   ```bash
   just run-docker
   ```

The Flask app will be available at [http://localhost:8000](http://localhost:8000).

To stop the services:

```bash
docker compose down
```

Data is persisted in a Docker volume named `mongo_data`.
