# Running LangBuilder with Docker

This guide will help you get LangBuilder up and running using Docker and Docker Compose.

## Prerequisites

- Docker
- Docker Compose

## Steps

1. Clone the LangBuilder repository:

   ```sh
   git clone https://github.com/cloudgeometry/langbuilder.git
   ```

2. Navigate to the `docker_example` directory:

   ```sh
   cd langbuilder/docker_example
   ```

3. Run the Docker Compose file:

   ```sh
   docker compose up
   ```

LangBuilder will now be accessible at [http://localhost:7860/](http://localhost:7860/).

## Docker Compose Configuration

The Docker Compose configuration spins up two services: `langbuilder` and `postgres`.

### LangBuilder Service

The `langbuilder` service uses the `nickchasecg/langbuilder:latest` Docker image and exposes port 7860. It depends on the `postgres` service.

Environment variables:

- `LANGBUILDER_DATABASE_URL`: The connection string for the PostgreSQL database.
- `LANGBUILDER_CONFIG_DIR`: The directory where LangBuilder stores logs, file storage, monitor data, and secret keys.

Volumes:

- `langbuilder-data`: This volume is mapped to `/app/langbuilder` in the container.

### PostgreSQL Service

The `postgres` service uses the `postgres:16` Docker image and exposes port 5432.

Environment variables:

- `POSTGRES_USER`: The username for the PostgreSQL database.
- `POSTGRES_PASSWORD`: The password for the PostgreSQL database.
- `POSTGRES_DB`: The name of the PostgreSQL database.

Volumes:

- `langbuilder-postgres`: This volume is mapped to `/var/lib/postgresql/data` in the container.

## Switching to a Specific LangBuilder Version

If you want to use a specific version of LangBuilder, you can modify the `image` field under the `langbuilder` service in the Docker Compose file. For example, to use version 1.0-alpha, change `nickchasecg/langbuilder:latest` to `nickchasecg/langbuilder:1.0-alpha`.
