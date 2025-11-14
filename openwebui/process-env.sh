#!/bin/bash

# Script to process .env file and expand environment variables
# This ensures only FRONTEND_PORT and BACKEND_PORT are defined once

ENV_FILE=".env"
PROCESSED_ENV_FILE=".env.processed"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found"
    exit 1
fi

# First, load the port definitions from .env
source "$ENV_FILE"

# Now process the .env file and expand variables
envsubst < "$ENV_FILE" > "$PROCESSED_ENV_FILE"

echo "Environment variables processed. Generated $PROCESSED_ENV_FILE"
echo "FRONTEND_PORT=$FRONTEND_PORT"
echo "BACKEND_PORT=$BACKEND_PORT"