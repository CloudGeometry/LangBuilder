# celeryconfig.py
import os

langbuilder_redis_host = os.environ.get("LANGBUILDER_REDIS_HOST")
langbuilder_redis_port = os.environ.get("LANGBUILDER_REDIS_PORT")
# broker default user

if langbuilder_redis_host and langbuilder_redis_port:
    broker_url = f"redis://{langbuilder_redis_host}:{langbuilder_redis_port}/0"
    result_backend = f"redis://{langbuilder_redis_host}:{langbuilder_redis_port}/0"
else:
    # RabbitMQ
    mq_user = os.environ.get("RABBITMQ_DEFAULT_USER", "langbuilder")
    mq_password = os.environ.get("RABBITMQ_DEFAULT_PASS", "langbuilder")
    broker_url = os.environ.get("BROKER_URL", f"amqp://{mq_user}:{mq_password}@localhost:5672//")
    result_backend = os.environ.get("RESULT_BACKEND", "redis://localhost:6379/0")
# tasks should be json or pickle
accept_content = ["json", "pickle"]
