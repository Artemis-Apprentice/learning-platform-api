# Eventing Plan: Async GitHub Issue Distribution System
## 🎓 Beginner-Friendly Guide for a 3-Person Team

> **Note:** This plan assumes you're new to message queues, event-driven architecture, and microservices. We've included links to supporting documentation throughout. Read those first if you encounter unfamiliar terms!

---

## 📚 Table of Contents
1. [What We're Building (Plain English)](#what-were-building-plain-english)
2. [Why We Need This Architecture](#why-we-need-this-architecture)
3. [Key Concepts Explained](#key-concepts-explained)
4. [System Architecture](#system-architecture)
5. [Implementation Steps](#implementation-steps)
6. [Supporting Documentation](#supporting-documentation)

---

## What We're Building (Plain English)

**The Problem:**  
Instructors need to copy GitHub issues from a template repository to 50+ student repositories. Doing this synchronously (waiting for each copy to finish) would take 5+ minutes, causing the API request to timeout and the instructor to stare at a loading spinner.

**The Solution:**  
We're building a system where:
1. Instructor clicks "Distribute Issues" button in React
2. Django API immediately responds "Got it! Here's your job ID: abc-123"
3. A separate background service (Migration Service) does the actual copying
4. React polls every 2 seconds to show progress: "Completed 15 of 50 repos..."
5. Instructor sees real-time updates without waiting

**The Magic Ingredient:**  
A **message queue** (RabbitMQ) that acts like a to-do list between Django and the Migration Service.

📖 **Learn More:** [What is a Message Queue?](docs/message-queue-explained.md)

---

## Why We Need This Architecture

### ❌ What We Rejected and Why

| Approach | Why We Rejected It |
|----------|-------------------|
| **Synchronous Processing** | API request would timeout after 30-60 seconds, but job takes 5+ minutes |
| **GitHub Actions** | Requires managing workflow files, harder to track progress, less control |
| **Celery (Task Queue)** | Adds complexity, tightly coupled to Django, requires Redis/RabbitMQ anyway |

### ✅ What We Chose: Event-Driven Architecture

**Event-Driven Architecture** means services communicate by sending messages (events) rather than calling each other directly.

**Benefits:**
- **Decoupled:** Django and Migration Service don't need to know about each other's internals
- **Scalable:** Can run multiple Migration Services to process jobs faster
- **Resilient:** If Migration Service crashes, messages wait in the queue
- **Flexible:** Easy to add new services that react to the same events

📖 **Learn More:** [Event-Driven Architecture Explained](docs/event-driven-architecture.md)

---

## Key Concepts Explained

### 🐰 RabbitMQ (Message Broker)
**What it is:** A service that receives messages from one application and delivers them to another.

**Think of it like:** A post office that holds mail until the recipient picks it up.

**In our system:**
- Django sends a message: "Please distribute issues for job abc-123"
- RabbitMQ stores it in a queue
- Migration Service picks it up when ready and processes it

📖 **Learn More:** [RabbitMQ Concepts Explained](docs/rabbitmq-concepts-explained.md)

---

### 🔄 Asynchronous Processing
**What it means:** Starting a task and continuing without waiting for it to finish.

**Synchronous (old way):**
```
Instructor clicks button → Wait 5 minutes → See result
```

**Asynchronous (new way):**
```
Instructor clicks button → Get job ID instantly → Check progress whenever you want
```

📖 **Learn More:** [Sync vs Async Explained](docs/sync-vs-async.md)

---

### 🏗️ Microservices
**What it is:** Breaking your application into smaller, independent services that each do one thing well.

**In our system:**
- **Django API:** Handles web requests, manages data
- **Migration Service:** Only does GitHub issue distribution
- **RabbitMQ:** Only handles message delivery

**Benefits:**
- Each service can be updated independently
- Easier to test and debug
- Can scale services independently

📖 **Learn More:** [Microservices Explained](docs/microservices-explained.md)

---

### 📊 Polling
**What it is:** Repeatedly asking "Are you done yet?" at regular intervals.

**In our system:**
- React asks Django every 2 seconds: "What's the status of job abc-123?"
- Django checks the database and responds: "15 of 50 repos completed"
- React updates the progress bar

**Alternative (not using):** WebSockets (real-time push), but polling is simpler for beginners.

---

## System Architecture

### Visual Overview

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐      ┌────────────────────┐
│   React     │─────▶│   Django     │─────▶│   RabbitMQ   │─────▶│ Migration Service  │
│  Frontend   │      │     API      │      │   (Broker)   │      │   (New Service)    │
└─────────────┘      └──────────────┘      └──────────────┘      └────────────────────┘
       │                     │                                              │
       │                     │                                              │
       │ (polls every 2s)    │                                              │
       └─────────────────────┤                                              │
                             │                                              │
                             ▼                                              ▼
                      ┌──────────────────────────────────────────────────────┐
                      │           Shared PostgreSQL Database                 │
                      │     (Job Status & Progress Tracking)                 │
                      │                                                      │
                      │  Django: Writes jobs, Reads progress                 │
                      │  Migration Service: Writes progress updates          │
                      └──────────────────────────────────────────────────────┘
```

### Step-by-Step Flow

**Step 1: Instructor Initiates Distribution**
```
Instructor clicks "Distribute Issues" button
  ↓
React sends POST request to Django: /api/distribution-jobs/
  ↓
Django receives request
```

**Step 2: Django Creates Job and Publishes Message**
```
Django creates database record:
  - job_id: "abc-123"
  - status: "PENDING"
  - source_repo: "template-repo"
  - target_repos: ["student1-repo", "student2-repo", ...]
  ↓
Django publishes message to RabbitMQ:
  - routing_key: "distribution.issue.create"
  - body: {job_id, source_repo, target_repos, issue_ids}
  ↓
Django responds to React immediately:
  - HTTP 202 Accepted
  - body: {job_id: "abc-123"}
```

**Step 3: React Starts Polling**
```
React receives job_id: "abc-123"
  ↓
Every 2 seconds, React sends GET request:
  /api/distribution-jobs/abc-123/progress/
  ↓
Django queries database and returns current status
  ↓
React updates UI with progress
```

**Step 4: Migration Service Processes Job**
```
Migration Service is listening to RabbitMQ queue
  ↓
Receives message for job "abc-123"
  ↓
Updates database: status = "IN_PROGRESS"
  ↓
For each target repo:
  - Fetch issues from source repo
  - Copy issues to target repo
  - Update progress in database: "15 of 50 completed"
  ↓
Updates database: status = "COMPLETED"
  ↓
Acknowledges message to RabbitMQ (removes from queue)
```

**Step 5: Instructor Sees Completion**
```
React's next poll sees status = "COMPLETED"
  ↓
React stops polling
  ↓
Shows success message: "✓ Issues distributed to 50 repositories!"
```

---

## Implementation Steps

### 📅 Timeline Overview

| Week | Phase | Focus |
|------|-------|-------|
| Week 1 | Infrastructure | Set up RabbitMQ, database, learn concepts |
| Week 2 | Django API | Build endpoints, message publishing |
| Week 3-4 | Migration Service | Build new service, GitHub integration |
| Week 5 | React Frontend | Build UI, progress tracking |
| Week 6 | Integration | Test everything together, deploy |

---

### 🏗️ Phase 1: Infrastructure Setup (Week 1)

> **Goal:** Set up the foundation - RabbitMQ, database tables, and understand how messages work

#### Step 1.1: RabbitMQ Setup (Days 1-2)
**Owner:** Developer 1  
**Difficulty:** ⭐⭐ (Moderate - new concepts but well-documented)

**What you'll learn:**
- How to run RabbitMQ in Docker
- What exchanges, queues, and routing keys are
- How to use the RabbitMQ Management UI

**Tasks:**
- [ ] Read [RabbitMQ Concepts Explained](docs/rabbitmq-concepts-explained.md) (30 minutes)
- [ ] Add RabbitMQ service to [`docker-compose.yml`](docker-compose.yml):
  ```yaml
  rabbitmq:
    image: rabbitmq:3-management
    container_name: learning-platform-rabbitmq
    environment:
      - RABBITMQ_DEFAULT_USER=admin
      - RABBITMQ_DEFAULT_PASS=admin123
    ports:
      - "5672:5672"    # AMQP port (for applications)
      - "15672:15672"  # Management UI (for humans)
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
  ```
- [ ] Add volume to bottom of [`docker-compose.yml`](docker-compose.yml):
  ```yaml
  volumes:
    lp_data:
    prometheus_data:
    grafana_data:
    rabbitmq_data:  # Add this line
  ```
- [ ] Start RabbitMQ: `docker-compose up rabbitmq`
- [ ] Open Management UI: http://localhost:15672 (login: admin/admin123)
- [ ] Follow [RabbitMQ Setup Guide](docs/rabbitmq-setup-guide.md) to create:
  - Exchange: `github_distribution`
  - Queue: `issue_distribution_queue`
  - Binding between them
- [ ] Test by sending a message using the Management UI
- [ ] Take screenshots and document what you learned

**Deliverables:**
- ✅ Updated [`docker-compose.yml`](docker-compose.yml)
- ✅ RabbitMQ running and accessible
- ✅ Exchange, queue, and binding created
- ✅ [`docs/rabbitmq-setup-guide.md`](docs/rabbitmq-setup-guide.md) with screenshots

**Help Resources:**
- [RabbitMQ Concepts Explained](docs/rabbitmq-concepts-explained.md)
- [RabbitMQ Official Tutorial](https://www.rabbitmq.com/getstarted.html)

---

#### Step 1.2: Database Schema for Job Tracking (Days 2-3)
**Owner:** Developer 2  
**Difficulty:** ⭐ (Easy - standard Django models)

**What you'll learn:**
- How to design database tables for job tracking
- Django migrations
- JSONField for flexible data storage

**Tasks:**
- [ ] Read [Database Design for Job Tracking](docs/database-design-explained.md) (20 minutes)
- [ ] Create new file: `LearningAPI/models/coursework/distribution_job.py`
- [ ] Define two models (see [Model Template](docs/model-template.md)):
  
  **Model 1: DistributionJob** (stores overall job info)
  - `id` - Unique identifier (UUID)
  - `created_by` - Which instructor started this job
  - `source_repo` - Template repository URL
  - `target_repos` - List of student repository URLs (JSON)
  - `issue_ids` - Which issues to copy (JSON array)
  - `status` - Current status: PENDING, IN_PROGRESS, COMPLETED, FAILED
  - `created_at` - When job was created
  - `updated_at` - Last update time
  - `metadata` - Any extra info (JSON)

  **Model 2: DistributionJobProgress** (tracks each repo's progress)
  - `id` - Unique identifier
  - `job` - Link to DistributionJob
  - `target_repo` - Which student repo
  - `status` - PENDING, IN_PROGRESS, SUCCESS, FAILED
  - `issues_created` - How many issues copied so far
  - `total_issues` - Total issues to copy
  - `error_message` - If failed, why?
  - `updated_at` - Last update time

- [ ] Add models to `LearningAPI/models/coursework/__init__.py`
- [ ] Create migration: `python manage.py makemigrations`
- [ ] Review migration file to understand what it does
- [ ] Run migration: `python manage.py migrate`
- [ ] Create serializers in `LearningAPI/serializers/distribution_job_serializer.py`
- [ ] Test in Django shell:
  ```python
  from LearningAPI.models import DistributionJob
  job = DistributionJob.objects.create(
      created_by=user,
      source_repo="https://github.com/org/template",
      target_repos=["https://github.com/student1/repo"],
      issue_ids=[1, 2, 3],
      status="PENDING"
  )
  print(job.id)  # Should print a UUID
  ```

**Deliverables:**
- ✅ `LearningAPI/models/coursework/distribution_job.py`
- ✅ `LearningAPI/serializers/distribution_job_serializer.py`
- ✅ Migration file created and run
- ✅ Test data created successfully

**Help Resources:**
- [Database Design for Job Tracking](docs/database-design-explained.md)
- [Django Models Documentation](https://docs.djangoproject.com/en/stable/topics/db/models/)
- [Model Template](docs/model-template.md)

---

#### Step 1.3: Message Schema Definition (Day 3)
**Owner:** Developer 3  
**Difficulty:** ⭐ (Easy - just documentation and validation)

**What you'll learn:**
- How to design a message format
- Why message schemas are important
- How to validate messages

**Tasks:**
- [ ] Read [Message Schema Design](docs/message-schema-design.md) (15 minutes)
- [ ] Create `docs/message-schema.md` documenting the message format:
  ```json
  {
    "version": "1.0",
    "job_id": "abc-123-def-456",
    "source_repo": {
      "owner": "nashville-software-school",
      "name": "template-repo",
      "url": "https://github.com/nashville-software-school/template-repo"
    },
    "target_repos": [
      {
        "owner": "student1",
        "name": "project-repo",
        "url": "https://github.com/student1/project-repo"
      }
    ],
    "issue_ids": [1, 2, 3, 4, 5],
    "metadata": {
      "instructor_id": 42,
      "cohort_id": 15,
      "timestamp": "2026-03-12T10:30:00Z"
    }
  }
  ```
- [ ] Create validation schema using Pydantic:
  - File: `LearningAPI/schemas/distribution_message.py`
  - Define Pydantic models for each part of the message
  - Add validation rules (e.g., issue_ids must be non-empty)
- [ ] Write tests for validation:
  - Valid message passes
  - Invalid message (missing field) fails
  - Invalid message (wrong type) fails
- [ ] Document versioning strategy: what happens when we need to change the schema?

**Deliverables:**
- ✅ `docs/message-schema.md` with examples
- ✅ `LearningAPI/schemas/distribution_message.py` with Pydantic models
- ✅ Tests for validation
- ✅ Versioning strategy documented

**Help Resources:**
- [Message Schema Design](docs/message-schema-design.md)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Schema Template](docs/schema-template.md)

---

### 🔧 Phase 2: Django API Implementation (Week 2)

> **Goal:** Build the Django endpoints that create jobs and publish messages to RabbitMQ

#### Step 2.1: RabbitMQ Publisher Integration (Days 1-2)
**Owner:** Developer 1  
**Difficulty:** ⭐⭐⭐ (Challenging - new library and concepts)

**What you'll learn:**
- How to connect to RabbitMQ from Python
- How to publish messages
- Error handling for network services

**Tasks:**
- [ ] Read [Publishing Messages to RabbitMQ](docs/publishing-messages.md) (30 minutes)
- [ ] Install Pika library: `pip install pika` and add to `requirements.txt`
- [ ] Create `LearningAPI/messaging/` directory
- [ ] Create `LearningAPI/messaging/rabbitmq_client.py`:
  - Connection manager class
  - Handle connection failures gracefully
  - Connection pooling (reuse connections)
  - See [RabbitMQ Client Template](docs/rabbitmq-client-template.md)
- [ ] Create `LearningAPI/messaging/publisher.py`:
  - `publish_distribution_job(job_data)` function
  - Validate message before publishing
  - Log all publish operations
  - Handle publish failures
  - See [Publisher Template](docs/publisher-template.md)
- [ ] Add RabbitMQ settings to [`LearningPlatform/settings.py`](LearningPlatform/settings.py):
  ```python
  # RabbitMQ Configuration
  RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
  RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
  RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'admin')
  RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASSWORD', 'admin123')
  RABBITMQ_EXCHANGE = 'github_distribution'
  RABBITMQ_ROUTING_KEY = 'distribution.issue.create'
  ```
- [ ] Update [`docker-compose.yml`](docker-compose.yml) to add RabbitMQ env vars to `web` service:
  ```yaml
  web:
    environment:
      # ... existing vars ...
      - RABBITMQ_HOST=rabbitmq
      - RABBITMQ_PORT=5672
      - RABBITMQ_USER=admin
      - RABBITMQ_PASSWORD=admin123
    depends_on:
      db:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
  ```
- [ ] Test publishing from Django shell:
  ```python
  from LearningAPI.messaging.publisher import publish_distribution_job
  publish_distribution_job({
      "version": "1.0",
      "job_id": "test-123",
      "source_repo": {"owner": "test", "name": "repo"},
      "target_repos": [],
      "issue_ids": [1]
  })
  ```
- [ ] Check RabbitMQ Management UI to see message in queue

**Deliverables:**
- ✅ `LearningAPI/messaging/rabbitmq_client.py`
- ✅ `LearningAPI/messaging/publisher.py`
- ✅ Updated [`LearningPlatform/settings.py`](LearningPlatform/settings.py)
- ✅ Updated [`docker-compose.yml`](docker-compose.yml)
- ✅ Successful test message in RabbitMQ

**Help Resources:**
- [Publishing Messages to RabbitMQ](docs/publishing-messages.md)
- [RabbitMQ Client Template](docs/rabbitmq-client-template.md)
- [Publisher Template](docs/publisher-template.md)
- [Pika Documentation](https://pika.readthedocs.io/)

---

#### Step 2.2: Distribution Job API Endpoints (Days 2-4)
**Owner:** Developer 2  
**Difficulty:** ⭐⭐ (Moderate - standard Django REST views)

**What you'll learn:**
- Building REST API endpoints
- Async job creation pattern
- Returning 202 Accepted status

**Tasks:**
- [ ] Read [Building Async API Endpoints](docs/async-api-endpoints.md) (20 minutes)
- [ ] Create `LearningAPI/views/distribution_job_view.py`
- [ ] Implement **Endpoint 1: Create Distribution Job**
  ```
  POST /api/distribution-jobs/
  
  Request Body:
  {
    "source_repo": "https://github.com/org/template",
    "target_repos": ["https://github.com/student1/repo", ...],
    "issue_ids": [1, 2, 3]
  }
  
  Response: 202 Accepted
  {
    "job_id": "abc-123-def-456",
    "status": "PENDING",
    "message": "Job created successfully. Use job_id to check progress."
  }
  ```
  
  **Logic:**
  1. Validate instructor is authenticated
  2. Validate request data
  3. Create `DistributionJob` record (status=PENDING)
  4. Create `DistributionJobProgress` records for each target repo
  5. Publish message to RabbitMQ
  6. Return job_id immediately (don't wait for processing)

- [ ] Implement **Endpoint 2: Get Job Status**
  ```
  GET /api/distribution-jobs/{job_id}/
  
  Response: 200 OK
  {
    "job_id": "abc-123-def-456",
    "status": "IN_PROGRESS",
    "created_at": "2026-03-12T10:30:00Z",
    "updated_at": "2026-03-12T10:32:15Z",
    "source_repo": "...",
    "total_repos": 50,
    "completed_repos": 15,
    "failed_repos": 0
  }
  ```

- [ ] Implement **Endpoint 3: Get Detailed Progress**
  ```
  GET /api/distribution-jobs/{job_id}/progress/
  
  Response: 200 OK
  {
    "job_id": "abc-123-def-456",
    "overall_status": "IN_PROGRESS",
    "progress": [
      {
        "target_repo": "https://github.com/student1/repo",
        "status": "SUCCESS",
        "issues_created": 5,
        "total_issues": 5
      },
      {
        "target_repo": "https://github.com/student2/repo",
        "status": "IN_PROGRESS",
        "issues_created": 3,
        "total_issues": 5
      },
      {
        "target_repo": "https://github.com/student3/repo",
        "status": "FAILED",
        "error_message": "Repository not found"
      }
    ]
  }
  ```

- [ ] Add URL routes to [`LearningPlatform/urls.py`](LearningPlatform/urls.py)
- [ ] Add permission checks (only instructors can create jobs)
- [ ] Add comprehensive error handling
- [ ] Test with Postman or curl

**Deliverables:**
- ✅ `LearningAPI/views/distribution_job_view.py`
- ✅ Updated [`LearningPlatform/urls.py`](LearningPlatform/urls.py)
- ✅ All three endpoints working
- ✅ Postman collection with example requests

**Help Resources:**
- [Building Async API Endpoints](docs/async-api-endpoints.md)
- [Django REST Framework Views](https://www.django-rest-framework.org/api-guide/views/)
- [API Endpoint Template](docs/api-endpoint-template.md)

---

#### Step 2.3: Django Testing (Days 4-5)
**Owner:** Developer 3  
**Difficulty:** ⭐⭐ (Moderate - testing async behavior)

**What you'll learn:**
- Testing API endpoints
- Mocking external services (RabbitMQ)
- Testing database transactions

**Tasks:**
- [ ] Read [Testing Async Systems](docs/testing-async-systems.md) (20 minutes)
- [ ] Create `LearningAPI/tests/test_distribution_jobs.py`
- [ ] Write tests for job creation endpoint:
  - ✅ Authenticated instructor can create job
  - ✅ Job record created in database
  - ✅ Progress records created for each target repo
  - ✅ Message published to RabbitMQ (mocked)
  - ✅ Returns 202 with job_id
  - ❌ Unauthenticated user gets 401
  - ❌ Non-instructor gets 403
  - ❌ Invalid data gets 400
- [ ] Write tests for status endpoints:
  - ✅ Can retrieve job status
  - ✅ Can retrieve detailed progress
  - ❌ Non-existent job_id gets 404
- [ ] Create `LearningAPI/tests/test_rabbitmq_publisher.py`
- [ ] Write tests for publisher:
  - ✅ Valid message publishes successfully
  - ✅ Invalid message raises validation error
  - ✅ Connection failure handled gracefully
- [ ] Run all tests: `python manage.py test`
- [ ] Aim for >80% code coverage

**Deliverables:**
- ✅ `LearningAPI/tests/test_distribution_jobs.py`
- ✅ `LearningAPI/tests/test_rabbitmq_publisher.py`
- ✅ All tests passing
- ✅ Coverage report

**Help Resources:**
- [Testing Async Systems](docs/testing-async-systems.md)
- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Mocking External Services](docs/mocking-external-services.md)

---

### 🚀 Phase 3: Migration Service Implementation (Weeks 3-4)

> **Goal:** Build a brand new Python service that consumes messages and distributes GitHub issues

#### Step 3.1: Migration Service Scaffolding (Days 1-2)
**Owner:** Developer 1  
**Difficulty:** ⭐⭐ (Moderate - new project setup)

**What you'll learn:**
- Setting up a FastAPI project from scratch
- Project structure best practices
- Docker containerization

**Tasks:**
- [ ] Read [FastAPI Quickstart](docs/fastapi-quickstart.md) (30 minutes)
- [ ] Create new directory: `github-migration-service/` (sibling to learning-platform-api)
- [ ] Initialize project structure:
  ```
  github-migration-service/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py              # FastAPI app entry point
  │   ├── config.py            # Configuration management
  │   ├── models/              # Database models (SQLAlchemy)
  │   │   └── __init__.py
  │   ├── services/            # Business logic
  │   │   └── __init__.py
  │   ├── consumers/           # RabbitMQ consumers
  │   │   └── __init__.py
  │   └── database/            # Database connection
  │       └── __init__.py
  ├── tests/
  │   └── __init__.py
  ├── Dockerfile
  ├── docker-compose.yml
  ├── requirements.txt
  ├── .env.example
  └── README.md
  ```
- [ ] Create `requirements.txt`:
  ```
  fastapi==0.109.0
  uvicorn[standard]==0.27.0
  pydantic==2.5.0
  pydantic-settings==2.1.0
  sqlalchemy==2.0.25
  psycopg2-binary==2.9.9
  aio-pika==9.3.1
  PyGithub==2.1.1
  python-dotenv==1.0.0
  ```
- [ ] Create basic FastAPI app in `app/main.py`:
  ```python
  from fastapi import FastAPI
  
  app = FastAPI(title="GitHub Migration Service")
  
  @app.get("/health")
  def health_check():
      return {"status": "healthy"}
  ```
- [ ] Create `Dockerfile` (see [Dockerfile Template](docs/dockerfile-template.md))
- [ ] Create `docker-compose.yml` for local development
- [ ] Test: `uvicorn app.main:app --reload`
- [ ] Visit http://localhost:8001/health (should return {"status": "healthy"})
- [ ] Visit http://localhost:8001/docs (FastAPI auto-generated docs)

**Deliverables:**
- ✅ New `github-migration-service/` project
- ✅ Basic FastAPI app running
- ✅ Health check endpoint working
- ✅ Dockerfile created
- ✅ README with setup instructions

**Help Resources:**
- [FastAPI Quickstart](docs/fastapi-quickstart.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Project Structure Template](docs/project-structure-template.md)

---

#### Step 3.2: Database Connection (Days 2-3)
**Owner:** Developer 2  
**Difficulty:** ⭐⭐ (Moderate - SQLAlchemy setup)

**What you'll learn:**
- Connecting to PostgreSQL from FastAPI
- SQLAlchemy ORM basics
- Sharing a database between services

**Tasks:**
- [ ] Read [Sharing Databases Between Services](docs/sharing-databases.md) (20 minutes)
- [ ] Create `app/database/connection.py`:
  - Database URL configuration
  - SQLAlchemy engine setup
  - Session management
  - Connection pooling
  - See [Database Connection Template](docs/database-connection-template.md)
- [ ] Create `app/models/distribution_job.py`:
  - SQLAlchemy models matching Django models
  - **Important:** Read-only for `DistributionJob`, read-write for `DistributionJobProgress`
  - See [SQLAlchemy Models Template](docs/sqlalchemy-models-template.md)
- [ ] Create `app/database/repositories/job_repository.py`:
  - `get_job(job_id)` - Fetch job details
  - `update_job_status(job_id, status)` - Update overall job status
  - `update_progress(job_id, repo_url, status, issues_created, error_msg)` - Update repo progress
  - See [Repository Pattern Template](docs/repository-pattern-template.md)
- [ ] Add database config to `app/config.py`:
  ```python
  from pydantic_settings import BaseSettings
  
  class Settings(BaseSettings):
      database_url: str
      rabbitmq_url: str
      github_token: str
      
      class Config:
          env_file = ".env"
  ```
- [ ] Create `.env.example` file
- [ ] Test database connection
