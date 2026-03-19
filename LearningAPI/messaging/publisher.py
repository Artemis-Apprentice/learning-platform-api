import pika
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def publish_poc_message(job_id, message_data):
    """
    Publish a GitHub issue migration message to RabbitMQ.

    Args:
        job_id: UUID of the job (injected into the outgoing message)
        message_data: Dict containing task_type, source_repo, target_repo, and options

    Returns:
        bool: True if published successfully, False otherwise
    """
    try:
        # Connect to RabbitMQ
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER,
            settings.RABBITMQ_PASSWORD
        )
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                credentials=credentials
            )
        )
        channel = connection.channel()

        # Declare queue (creates if doesn't exist)
        channel.queue_declare(queue='poc_queue', durable=True)

        # Prepare message — flat contract; job_id is injected from the DB record
        message = {
            'job_id': str(job_id),
            **message_data
        }

        # Publish message
        channel.basic_publish(
            exchange='',
            routing_key='poc_queue',
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
            )
        )

        logger.info(f"Published POC message for job {job_id}")
        connection.close()
        return True

    except Exception as e:
        logger.error(f"Failed to publish POC message: {e}")
        return False
