# RabbitMQ Event-Driven Architecture: Proof of Concept

## 🧪 1-3 Day Implementation Plan

> **Goal:** Test RabbitMQ integration and validate the async event-driven architecture with minimal code before building the full system.

---

## 📋 What We're Testing

This POC validates:

1. ✅ RabbitMQ can run alongside Django in Docker
2. ✅ Django can publish messages to RabbitMQ
3. ✅ A separate Python process can consume those messages
4. ✅ Database state can be updated by the consumer
5. ✅ Basic async job pattern works end-to-end

**What We're NOT Building:**

- ❌ Full REST API with all endpoints
- ❌ GitHub integration (we'll simulate with dummy data)
- ❌ React frontend (we'll test with curl/Postman)
- ❌ Separate FastAPI service (just a simple Python consumer script)
- ❌ Complex error handling or retry logic

---

## 🎯 Success Criteria

By the end of this POC, you should be able to:

1. Send a POST request to Django
2. See Django create a job record and publish a message to RabbitMQ
3. See a separate Python consumer pick up the message
4. Watch the consumer update the job status in real-time
5. Query Django to see the updated job status

**Time to complete:** 5-10 minutes from setup to working demo

---

## 📊 Simplified Architecture

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐      ┌────────────────────┐
│   Postman   │─────▶│   Django     │─────▶│   RabbitMQ   │─────▶│  Simple Consumer   │
│   /curl     │      │     API      │      │   (Docker)   │      │  (Python Script)   │
└─────────────┘      └──────────────┘      └──────────────┘      └────────────────────┘
                            │                                              │
                            │                                              │
                            ▼                                              ▼
                     ┌──────────────────────────────────────────────────────┐
                     │           Shared PostgreSQL Database                 │
                     │         (Simple job tracking table)                  │
                     └──────────────────────────────────────────────────────┘
```

---

## 🚀 Implementation Steps

### Day 1: Infrastructure & Django Publisher (3-4 hours)

#### Step 1: Add RabbitMQ to Docker (30 minutes)

**File:** [`docker-compose.yml`](../docker-compose.yml)

Add the RabbitMQ service:

```yaml
services:
  # ... existing services ...

  rabbitmq:
    image: rabbitmq:3-management
    container_name: learning-platform-rabbitmq
    environment:
      - RABBITMQ_DEFAULT_USER=admin
      - RABBITMQ_DEFAULT_PASS=admin123
    ports:
      - "5672:5672" # AMQP port
      - "15672:15672" # Management UI
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  lp_data:
  prometheus_data:
  grafana_data:
  rabbitmq_data: # Add this
```

**Test it:**

```bash
docker-compose up rabbitmq
# Visit http://localhost:15672
# Login: admin / admin123
```

---

#### Step 2: Create Minimal Job Model (45 minutes)

**File:** [`LearningAPI/models/coursework/poc_job.py`](../LearningAPI/models/coursework/poc_job.py)

```python
from django.db import models
from django.contrib.auth.models import User
import uuid

class PocJob(models.Model):
    """
    Minimal job model for POC testing.
    Just tracks job ID, status, and message.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    message_data = models.JSONField(default=dict)  # Store the message we sent
    result_data = models.JSONField(default=dict, blank=True)  # Store consumer results
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'poc_jobs'
        ordering = ['-created_at']

    def __str__(self):
        return f"POC Job {self.id} - {self.status}"
```

**File:** [`LearningAPI/models/coursework/__init__.py`](../LearningAPI/models/coursework/__init__.py)

Add to imports:

```python
from .poc_job import PocJob
```

**Run migrations:**

```bash
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
```

---

#### Step 3: Install Pika & Create Publisher (60 minutes)

**File:** [`requirements.txt`](../requirements.txt)

Add:

```txt
pika==1.3.2
```

**File:** [`LearningAPI/messaging/__init__.py`](../LearningAPI/messaging/__init__.py) (create new directory)

```python
# Empty file to make this a package
```

**File:** [`LearningAPI/messaging/publisher.py`](../LearningAPI/messaging/publisher.py)

```python
import pika
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def publish_poc_message(job_id, message_data):
    """
    Publish a simple message to RabbitMQ for POC testing.

    Args:
        job_id: UUID of the job
        message_data: Dictionary to send to consumer

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

        # Prepare message
        message = {
            'job_id': str(job_id),
            'data': message_data
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
```

**File:** [`LearningPlatform/settings.py`](../LearningPlatform/settings.py)

Add at the bottom:

```python
# RabbitMQ Configuration (POC)
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'admin')
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASSWORD', 'admin123')
```

**File:** [`docker-compose.yml`](../docker-compose.yml)

Update the `web` service to add RabbitMQ connection:

```yaml
web:
  # ... existing config ...
  environment:
    # ... existing environment vars ...
    - RABBITMQ_HOST=rabbitmq
    - RABBITMQ_PORT=5672
    - RABBITMQ_USER=admin
    - RABBITMQ_PASSWORD=admin123
  depends_on:
    db:
      condition: service_healthy
    rabbitmq: # Add this
      condition: service_healthy
```

**Rebuild and test:**

```bash
docker-compose down
docker-compose build web
docker-compose up
```

---

#### Step 4: Create Simple API Endpoint (45 minutes)

**File:** [`LearningAPI/views/poc_job_view.py`](../LearningAPI/views/poc_job_view.py)

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from LearningAPI.models.coursework import PocJob
from LearningAPI.messaging.publisher import publish_poc_message
import logging

logger = logging.getLogger(__name__)

class PocJobViewSet(viewsets.ViewSet):
    """
    Simple POC endpoint to test async job creation.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='create')
    def create_job(self, request):
        """
        POST /api/poc-jobs/create/

        Body: {"test_data": "anything you want"}

        Returns: 202 Accepted with job_id
        """
        # Create job record
        job = PocJob.objects.create(
            created_by=request.user,
            status='PENDING',
            message_data=request.data
        )

        # Publish to RabbitMQ
        success = publish_poc_message(
            job_id=job.id,
            message_data=request.data
        )

        if not success:
            job.status = 'FAILED'
            job.result_data = {'error': 'Failed to publish message'}
            job.save()
            return Response(
                {'error': 'Failed to publish to RabbitMQ'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        logger.info(f"Created POC job {job.id}")

        return Response({
            'job_id': str(job.id),
            'status': job.status,
            'message': 'Job created and message published to RabbitMQ'
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['get'], url_path='status')
    def get_status(self, request, pk=None):
        """
        GET /api/poc-jobs/{job_id}/status/

        Returns current job status and results
        """
        try:
            job = PocJob.objects.get(pk=pk)
        except PocJob.DoesNotExist:
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'job_id': str(job.id),
            'status': job.status,
            'message_data': job.message_data,
            'result_data': job.result_data,
            'created_at': job.created_at,
            'updated_at': job.updated_at
        })
```

**File:** [`LearningAPI/views/__init__.py`](../LearningAPI/views/__init__.py)

Add:

```python
from .poc_job_view import PocJobViewSet
```

**File:** [`LearningPlatform/urls.py`](../LearningPlatform/urls.py)

Add to router:

```python
from LearningAPI.views import PocJobViewSet

router = routers.DefaultRouter(trailing_slash=False)
# ... existing routes ...
router.register(r'poc-jobs', PocJobViewSet, basename='poc-job')
```

**Restart Django:**

```bash
docker-compose restart web
```

---

### Day 2: Consumer & End-to-End Test (3-4 hours)

#### Step 5: Create Simple Consumer Script (90 minutes)

**File:** [`consumer_poc.py`](../consumer_poc.py) (in project root)

```python
#!/usr/bin/env python
"""
Simple RabbitMQ consumer for POC testing.
Runs outside Docker for easier debugging.
Connects directly to PostgreSQL - no Django dependency.
"""
import pika
import json
import time
import os
import psycopg2
import psycopg2.extras
from datetime import datetime

# ---------------------------------------------------------------------------
# Standalone settings — no Django imports, no shared settings module
# ---------------------------------------------------------------------------

DB_SETTINGS = {
    'host':     os.environ.get('DB_HOST',     'localhost'),
    'port':     int(os.environ.get('DB_PORT', 5432)),
    'dbname':   os.environ.get('DB_NAME',     'learningplatform'),
    'user':     os.environ.get('DB_USER',     'learningplatform'),
    'password': os.environ.get('DB_PASSWORD', 'learningplatform'),
}

RABBITMQ_SETTINGS = {
    'host':     os.environ.get('RABBITMQ_HOST',     'localhost'),
    'port':     int(os.environ.get('RABBITMQ_PORT', 5672)),
    'user':     os.environ.get('RABBITMQ_USER',     'admin'),
    'password': os.environ.get('RABBITMQ_PASSWORD', 'admin123'),
}

# ---------------------------------------------------------------------------

def get_db_connection():
    """Return a new psycopg2 connection using the standalone DB settings."""
    return psycopg2.connect(**DB_SETTINGS)


def process_message(job_id, data):
    """
    Simulate processing the job.
    In real implementation, this would call GitHub API, etc.
    Updates the poc_jobs table directly via psycopg2.
    """
    print(f"\n{'='*60}")
    print(f"🔄 Processing job: {job_id}")
    print(f"📦 Received data: {data}")
    print(f"{'='*60}\n")

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Verify the job exists
        cur.execute("SELECT id FROM poc_jobs WHERE id = %s", (job_id,))
        if cur.fetchone() is None:
            print(f"❌ Job {job_id} not found in database\n")
            return False

        # Update status to IN_PROGRESS
        cur.execute(
            "UPDATE poc_jobs SET status = %s, updated_at = NOW() WHERE id = %s",
            ('IN_PROGRESS', job_id)
        )
        conn.commit()
        print("✓ Updated job status to IN_PROGRESS")

        # Simulate work (e.g., GitHub API calls)
        print("⏳ Simulating work...")
        for i in range(1, 6):
            time.sleep(1)
            print(f"   Step {i}/5 completed...")

            # Update progress
            result = json.dumps({
                'progress': f'{i}/5',
                'last_update': datetime.now().isoformat()
            })
            cur.execute(
                "UPDATE poc_jobs SET result_data = %s, updated_at = NOW() WHERE id = %s",
                (result, job_id)
            )
            conn.commit()

        # Mark as completed
        final_result = json.dumps({
            'completed_at': datetime.now().isoformat(),
            'processed_data': data,
            'message': 'POC job completed successfully!'
        })
        cur.execute(
            "UPDATE poc_jobs SET status = %s, result_data = %s, updated_at = NOW() WHERE id = %s",
            ('COMPLETED', final_result, job_id)
        )
        conn.commit()

        print(f"✅ Job {job_id} completed successfully!\n")
        return True

    except Exception as e:
        print(f"❌ Error processing job: {e}\n")

        # Try to mark job as failed
        try:
            if conn:
                conn.rollback()
                cur = conn.cursor()
                error_result = json.dumps({'error': str(e)})
                cur.execute(
                    "UPDATE poc_jobs SET status = %s, result_data = %s, updated_at = NOW() WHERE id = %s",
                    ('FAILED', error_result, job_id)
                )
                conn.commit()
        except Exception:
            pass

        return False

    finally:
        if conn:
            conn.close()


def callback(ch, method, properties, body):
    """
    Callback function when message is received.
    """
    print("\n📨 Received message from RabbitMQ")

    try:
        # Parse message
        message = json.loads(body)
        job_id = message['job_id']
        data = message['data']

        # Process the job
        success = process_message(job_id, data)

        # Acknowledge message (remove from queue)
        if success:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print("✓ Message acknowledged and removed from queue")
        else:
            # Reject and don't requeue if processing failed
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            print("⚠ Message rejected (processing failed)")

    except Exception as e:
        print(f"❌ Error in callback: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    """
    Start the consumer and listen for messages.
    """
    print("\n" + "="*60)
    print("🐰 RabbitMQ POC Consumer Starting...")
    print("="*60 + "\n")

    # Connect to RabbitMQ using standalone settings
    credentials = pika.PlainCredentials(
        RABBITMQ_SETTINGS['user'],
        RABBITMQ_SETTINGS['password']
    )
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_SETTINGS['host'],
            port=RABBITMQ_SETTINGS['port'],
            credentials=credentials
        )
    )
    channel = connection.channel()

    # Declare queue (ensure it exists)
    channel.queue_declare(queue='poc_queue', durable=True)

    # Set QoS to process one message at a time
    channel.basic_qos(prefetch_count=1)

    # Set up consumer
    channel.basic_consume(
        queue='poc_queue',
        on_message_callback=callback
    )

    print("👂 Waiting for messages. Press Ctrl+C to exit.\n")

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down consumer...")
        channel.stop_consuming()

    connection.close()
    print("✓ Consumer stopped\n")


if __name__ == '__main__':
    main()
```

**Make it executable:**

```bash
chmod +x consumer_poc.py
```

---

#### Step 6: Run End-to-End Test (30 minutes)

**Install consumer dependencies (one-time):**

```bash
pip install pika psycopg2-binary
```

**Terminal 1 - Start Consumer:**

```bash
# Set DB + RabbitMQ connection env vars, then run the script
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=learningplatform
export DB_USER=learningplatform
export DB_PASSWORD=learningplatform
export RABBITMQ_HOST=localhost
export RABBITMQ_PORT=5672
export RABBITMQ_USER=admin
export RABBITMQ_PASSWORD=admin123

python consumer_poc.py
```

**Terminal 2 - Create a Job:**

```bash
# Get auth token first (adjust URL if needed)
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Use the token to create a POC job
curl -X POST http://localhost:8000/api/poc-jobs/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN_HERE" \
  -d '{"test_data": "Hello from POC!", "extra": "More test data"}'

# You'll get back:
# {
#   "job_id": "abc-123-def-456",
#   "status": "PENDING",
#   "message": "Job created and message published to RabbitMQ"
# }
```

**Terminal 3 - Check Status:**

```bash
# Replace JOB_ID with the one you got back
curl http://localhost:8000/api/poc-jobs/JOB_ID/status/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"

# Watch the status change from PENDING → IN_PROGRESS → COMPLETED
```

**Watch the magic happen:**

1. Terminal 2 gets instant response with job_id
2. Terminal 1 (consumer) shows it processing the job
3. Terminal 3 can query status and see updates in real-time

---

## 🎉 Success Checklist

After completing the POC, you should be able to:

- [x] RabbitMQ running in Docker and accessible at http://localhost:15672
- [x] Create a job via Django API and get instant 202 response
- [x] See the message appear in RabbitMQ queue (via Management UI)
- [x] Consumer picks up and processes the message
- [x] Job status updates from PENDING → IN_PROGRESS → COMPLETED
- [x] Query job status and see results
- [x] Consumer logs show clear processing steps

---

## 📸 Screenshots to Capture

1. **RabbitMQ Management UI** showing the `poc_queue`
2. **Postman/curl** creating a job and getting 202 response
3. **Consumer terminal** showing message processing
4. **Job status response** showing COMPLETED with results
5. **Django admin** showing PocJob records

---

## 🔍 What You Learned

By completing this POC, you've validated:

1. **Message Queue Pattern**: Django publishes, separate process consumes
2. **Async Job Pattern**: Instant response with job_id, background processing
3. **Shared Database**: Multiple processes updating same database
4. **Docker Networking**: Services communicating inside Docker
5. **Real-time Updates**: Consumer updating job status that Django can query

---

## ➡️ Next Steps

Now that the POC works, you can:

1. **Expand the Model**: Add proper DistributionJob and DistributionJobProgress models
2. **Add GitHub Integration**: Replace dummy processing with real GitHub API calls
3. **Create Full REST API**: Add all the endpoints from the full eventing plan
4. **Build Proper Consumer Service**: Convert consumer script to FastAPI service
5. **Add React Frontend**: Build UI for job creation and progress tracking

Refer to [`eventing-plan.md`](eventing-plan.md) for the full implementation plan.

---

## 🐛 Troubleshooting

### Consumer can't connect to RabbitMQ

```bash
# Make sure RabbitMQ is running
docker-compose ps

# Check RabbitMQ logs
docker-compose logs rabbitmq
```

### Django can't publish messages

```bash
# Check environment variables are set
docker-compose exec web env | grep RABBITMQ

# Check Django logs
docker-compose logs web
```

### Job stays in PENDING status

- Check if consumer is running
- Check RabbitMQ Management UI to see if message is in queue
- Check consumer terminal for errors

### Database errors in consumer

```bash
# Make sure migrations are run
docker-compose exec web python manage.py migrate

# Verify the poc_jobs table exists directly in PostgreSQL
docker-compose exec db psql -U learningplatform -c "\dt poc_jobs"

# Check row count without Django
docker-compose exec db psql -U learningplatform -c "SELECT COUNT(*) FROM poc_jobs;"
```

---

## 📚 Files Created

This POC creates these new files:

- [`docker-compose.yml`](../docker-compose.yml) - Modified to add RabbitMQ
- [`LearningAPI/models/coursework/poc_job.py`](../LearningAPI/models/coursework/poc_job.py)
- [`LearningAPI/messaging/__init__.py`](../LearningAPI/messaging/__init__.py)
- [`LearningAPI/messaging/publisher.py`](../LearningAPI/messaging/publisher.py)
- [`LearningAPI/views/poc_job_view.py`](../LearningAPI/views/poc_job_view.py)
- [`consumer_poc.py`](../consumer_poc.py)

**Total Lines of Code:** ~400 (including comments)
**Time to Implement:** 1-3 days
**Time to Demo:** 5-10 minutes once working

---

## 💡 Key Takeaways

1. **RabbitMQ is Simple**: Once set up, it's just publishing and consuming JSON messages
2. **Async is Powerful**: User gets instant response while work happens in background
3. **Decoupling Works**: Django and consumer don't know about each other's implementation
4. **Testing is Easy**: Can test each piece independently before integration

This POC proves the architecture works before investing in the full implementation! 🚀
