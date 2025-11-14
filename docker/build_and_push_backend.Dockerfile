# syntax=docker/dockerfile:1
# Keep this syntax directive! It's used to enable Docker BuildKit

ARG LANGBUILDER_IMAGE
FROM $LANGBUILDER_IMAGE

RUN rm -rf /app/.venv/langbuilder/frontend

CMD ["python", "-m", "langbuilder", "run", "--host", "0.0.0.0", "--port", "7860", "--backend-only"]
