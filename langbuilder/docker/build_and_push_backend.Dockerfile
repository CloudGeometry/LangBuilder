# syntax=docker/dockerfile:1
# Keep this syntax directive! It's used to enable Docker BuildKit

ARG LANGBUILDER_IMAGE
FROM ${LANGBUILDER_IMAGE}

RUN rm -rf /app/src/backend/langflow/frontend

CMD ["python", "-m", "langflow", "run", "--host", "0.0.0.0", "--port", "7860", "--backend-only"]
