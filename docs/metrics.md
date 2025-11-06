# Prometheus Metrics Implementation Guide

## Overview

This document provides a simplified approach to implementing Prometheus metrics in the Learning Platform API. The focus is on **basic performance monitoring** to ensure your critical operations are working correctly and performing at reasonable speeds.

## Goals

1. **Track operation speed** - How long do critical operations take?
2. **Monitor success rates** - Are operations completing successfully?
3. **Measure throughput** - How often are operations happening?

---

## Prerequisites

### Required Dependencies

```python
# Add to requirements.txt
prometheus-client==0.19.0
django-prometheus==2.3.1
```

### Docker Setup (Recommended)

Since this project uses Docker for the development environment, follow these steps:

1. **Add Dependencies to requirements.txt**
   
   Add the following lines to your [`requirements.txt`](../requirements.txt):
   ```
   prometheus-client==0.19.0
   django-prometheus==2.3.1
   ```

2. **Configure Django Settings** ([`LearningPlatform/settings.py`](../LearningPlatform/settings.py))
   ```python
   INSTALLED_APPS = [
       'django_prometheus',  # Add at the top
       # ... other apps
   ]

   MIDDLEWARE = [
       'django_prometheus.middleware.PrometheusBeforeMiddleware',  # First
       # ... other middleware
       'django_prometheus.middleware.PrometheusAfterMiddleware',   # Last
   ]
   ```

3. **Add Metrics Endpoint** ([`LearningPlatform/urls.py`](../LearningPlatform/urls.py))
   ```python
   from django.urls import path, include
   
   urlpatterns = [
       path('', include('django_prometheus.urls')),  # Exposes /metrics
       # ... other patterns
   ]
   ```

4. **Rebuild Docker Containers**
   
   After adding the dependencies and configuration, rebuild your Docker containers:
   ```bash
   docker compose down
   docker compose up --build
   ```
   
   The dependencies will be automatically installed when the container builds (see [`docker-compose.yml`](../docker-compose.yml) line 56).

5. **Verify Metrics Endpoint**
   
   Once the containers are running, verify the metrics endpoint is accessible:
   ```bash
   curl http://localhost:8000/metrics
   ```
   
   You should see Prometheus metrics output.

### Alternative: Local Development Setup

If you're not using Docker:

1. **Install Dependencies Locally**
   ```bash
   pip install prometheus-client django-prometheus
   ```

2. Follow steps 2-3 above for Django configuration

3. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

---

## Simple Metrics for Critical Operations

We'll add just **two metrics per operation**:
1. **Duration** - How long it takes
2. **Counter** - Success vs failure count

---

## Metric 1: Student Project Moves

### Location
[`LearningAPI/views/student_view.py:260-283`](../LearningAPI/views/student_view.py:260) - [`project()` action](../LearningAPI/views/student_view.py:260)

### Metrics Definition

```python
from prometheus_client import Counter, Histogram
import time

# Add at module level in student_view.py after logger initialization (line 28)
student_project_move_duration = Histogram(
    'learning_api_student_project_move_seconds',
    'Time to move student to different project',
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

student_project_move_total = Counter(
    'learning_api_student_project_move_total',
    'Total student project moves',
    ['status']  # 'success' or 'error'
)
```

### Implementation

```python
@method_decorator(is_instructor())
@action(methods=['post'], detail=True)
def project(self, request, pk):
    """Add to the list of projects being worked on by student"""
    
    if request.method == "POST":
        start_time = time.time()
        
        try:
            student_project = StudentProject()
            student_project.student = NssUser.objects.get(pk=pk)
            student_project.project = Project.objects.get(
                pk=int(request.data['projectId']))
            student_project.save()
            
            # Record metrics
            duration = time.time() - start_time
            student_project_move_duration.observe(duration)
            student_project_move_total.labels(status='success').inc()
            
            logger.info(
                "Student moved successfully",
                student_id=student_project.student.id, 
                project=student_project.project.id, 
                moved_by=request.auth.user.username if request.auth.user.is_authenticated else 'anonymous',
            )
            return Response({'message': 'Success'}, status=status.HTTP_201_CREATED)
            
        except Exception as ex:
            # Record failure
            duration = time.time() - start_time
            student_project_move_duration.observe(duration)
            student_project_move_total.labels(status='error').inc()
            
            logger.error(
                "Moving student failed",
                message=ex.args[0],
            )
            return Response({'message': ex.args[0]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

---

## Metric 2: Core Skill Updates

### Location
[`LearningAPI/views/core_skill_record_view.py:65-95`](../LearningAPI/views/core_skill_record_view.py:65) - [`update()` method](../LearningAPI/views/core_skill_record_view.py:65)

### Metrics Definition

```python
from prometheus_client import Counter, Histogram
import time

# Add at module level in core_skill_record_view.py after logger initialization (line 11)
core_skill_update_duration = Histogram(
    'learning_api_core_skill_update_seconds',
    'Time to update core skill level',
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0)
)

core_skill_update_total = Counter(
    'learning_api_core_skill_update_total',
    'Total core skill updates',
    ['status']  # 'success' or 'error'
)
```

### Implementation

```python
def update(self, request, pk=None):
    """Handle PUT requests to update core skill level"""
    start_time = time.time()
    
    try:
        record = CoreSkillRecord.objects.get(pk=pk)
        
        if request.auth.user.is_staff:
            record.level = request.data["level"]
            record.save()
            
            # Record metrics
            duration = time.time() - start_time
            core_skill_update_duration.observe(duration)
            core_skill_update_total.labels(status='success').inc()
            
            logger.info(
                "Skill level successfully updated",
                record_level=record.level,
                skill_id=request.data["skill_id"],
                student_id=request.data["student_id"],
            )
            return Response(None, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(None, status=status.HTTP_401_UNAUTHORIZED)
    
    except CoreSkillRecord.DoesNotExist:
        duration = time.time() - start_time
        core_skill_update_duration.observe(duration)
        core_skill_update_total.labels(status='error').inc()
        
        logger.error(
            f"Core skill record of {pk} could not be found",
        )
        return Response(None, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as ex:
        duration = time.time() - start_time
        core_skill_update_duration.observe(duration)
        core_skill_update_total.labels(status='error').inc()
        
        logger.error(
            "Skill update failed",
            message=ex.args[0],
        )
        return HttpResponseServerError(ex)
```

---

## Metric 3: Team Assignments

### Location
[`LearningAPI/views/student_view.py:285-316`](../LearningAPI/views/student_view.py:285) - [`teams()` action](../LearningAPI/views/student_view.py:287)

### Metrics Definition

```python
from prometheus_client import Counter, Histogram
import time

# Add at module level in student_view.py (with other metrics)
team_assignment_duration = Histogram(
    'learning_api_team_assignment_seconds',
    'Time to assign students to teams',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

team_assignment_total = Counter(
    'learning_api_team_assignment_total',
    'Total team assignments',
    ['status']  # 'success' or 'error'
)
```

### Implementation

```python
@method_decorator(is_instructor())
@action(methods=['post'], detail=False)
def teams(self, request):
    """Add/remove student tag for teams"""
    
    if request.method == "POST":
        start_time = time.time()
        combos = request.data.get('combos', None)
        
        for combo in combos:
            try:
                student = NssUser.objects.get(pk=combo['student'])
                
                try:
                    tag = Tag.objects.get(name=combo['team'])
                except Tag.DoesNotExist:
                    tag = Tag.objects.create(name=combo['team'])
                
                try:
                    StudentTag.objects.create(student=student, tag=tag)
                    team_assignment_total.labels(status='success').inc()
                    
                    logger.info(
                        "Team updated successfully",
                        tag=tag.name, 
                        moved_by=request.auth.user.username if request.auth.user.is_authenticated else 'anonymous',
                    )
                
                except Exception as ex:
                    team_assignment_total.labels(status='error').inc()
                    
                    logger.error(
                        "Updating team failed",
                        message=ex.args[0],
                    )
            
            except NssUser.DoesNotExist:
                team_assignment_total.labels(status='error').inc()
        
        # Record total duration for batch
        duration = time.time() - start_time
        team_assignment_duration.observe(duration)
        
        return Response(None, status=status.HTTP_201_CREATED)
```

---

## Metric 4: Slack Channel Creation

### Location
[`LearningAPI/views/slack.py:14-48`](../LearningAPI/views/slack.py:14) - [`create()` method](../LearningAPI/views/slack.py:14)

### Metrics Definition

```python
from prometheus_client import Counter, Histogram
import time

# Add at module level in slack.py after logger initialization (line 10)
slack_channel_create_duration = Histogram(
    'learning_api_slack_channel_create_seconds',
    'Time to create Slack channel',
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0)
)

slack_channel_create_total = Counter(
    'learning_api_slack_channel_create_total',
    'Total Slack channel creations',
    ['status']  # 'success' or 'error'
)
```

### Implementation

```python
def create(self, request):
    """Handle POST requests to create team Slack channels"""
    start_time = time.time()
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    channel_payload = {
        "name": request.data["name"],
        "token": os.getenv("SLACK_BOT_TOKEN")
    }
    
    student_slack_ids = set()
    for student_id in request.data["students"]:
        student = NssUser.objects.get(pk=student_id)
        if student.slack_handle is not None:
            student_slack_ids.add(student.slack_handle)
    
    try:
        res = requests.post(
            "https://slack.com/api/conversations.create",
            timeout=10,
            data=channel_payload,
            headers=headers
        )
        channel_res = res.json()
        
        if channel_res['ok']:
            # Record success
            duration = time.time() - start_time
            slack_channel_create_duration.observe(duration)
            slack_channel_create_total.labels(status='success').inc()
            
            logger.info(
                "slack_channel_created_successfully",
                channel_name=request.data["name"],
                students=student_slack_ids,
                slack_response=channel_res
            )
        else:
            # Record failure
            duration = time.time() - start_time
            slack_channel_create_duration.observe(duration)
            slack_channel_create_total.labels(status='error').inc()
            
            logger.error(
                "slack_channel_creation_failed",
                channel_name=request.data["name"],
                slack_response=channel_res
            )
            return Response(channel_res, status=status.HTTP_502_BAD_GATEWAY)
        
        # Continue with student invitations...
        invitation_payload = {
            "channel": channel_res["channel"]["id"],
            "users": ",".join(list(student_slack_ids)),
            "token": os.getenv("SLACK_BOT_TOKEN")
        }
        
        res = requests.post(
            "https://slack.com/api/conversations.invite",
            timeout=10,
            data=invitation_payload,
            headers=headers
        )
        students_res = res.json()
        
        if res.status_code == 200:
            logger.info(
                "slack_students_invited_successfully",
                channel_name=request.data["name"],
                channel_id=channel_res["channel"]["id"],
                student_count=len(student_slack_ids)
            )
        else:
            logger.warning(
                "Slack Student Invitation Failed",
                channel_name=request.data["name"],
                channel_id=channel_res["channel"]["id"],
                student_count=len(student_slack_ids),
                error=students_res.get("error")
            )
        
        combined_response = {
            "channel": channel_res,
            "invitations": students_res
        }
        
        return Response(combined_response, status=status.HTTP_201_CREATED)
        
    except Exception as ex:
        # Record exception
        duration = time.time() - start_time
        slack_channel_create_duration.observe(duration)
        slack_channel_create_total.labels(status='error').inc()
        
        logger.error(
            "slack_channel_creation_failed",
            reason=str(ex),
            channel_name=request.data.get("name"),
            created_by=request.auth.user.username if request.auth.user.is_authenticated else 'anonymous',
            exc_info=True
        )
        return Response({"reason": ex.args[0]}, status=status.HTTP_400_BAD_REQUEST)
```

---

## Metric 5: Slack Student Invitations

### Location
[`LearningAPI/views/slack.py:49-73`](../LearningAPI/views/slack.py:49) - Student invitation section

### Metrics Definition

```python
# Add to slack.py with other metrics
slack_invitation_duration = Histogram(
    'learning_api_slack_invitation_seconds',
    'Time to invite students to Slack channel',
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0)
)

slack_invitation_total = Counter(
    'learning_api_slack_invitation_total',
    'Total Slack student invitations',
    ['status']  # 'success' or 'error'
)
```

### Implementation

```python
# In the create() method, after channel creation:

        # Add students to Slack channel
        invitation_start = time.time()
        
        invitation_payload = {
            "channel": channel_res["channel"]["id"],
            "users": ",".join(list(student_slack_ids)),
            "token": os.getenv("SLACK_BOT_TOKEN")
        }
        
        res = requests.post(
            "https://slack.com/api/conversations.invite",
            timeout=10,
            data=invitation_payload,
            headers=headers
        )
        students_res = res.json()
        
        # Record invitation metrics
        invitation_duration = time.time() - invitation_start
        slack_invitation_duration.observe(invitation_duration)
        
        if res.status_code == 200:
            slack_invitation_total.labels(status='success').inc()
            
            logger.info(
                "slack_students_invited_successfully",
                channel_name=request.data["name"],
                channel_id=channel_res["channel"]["id"],
                student_count=len(student_slack_ids)
            )
        else:
            slack_invitation_total.labels(status='error').inc()
            
            logger.warning(
                "Slack Student Invitation Failed",
                channel_name=request.data["name"],
                channel_id=channel_res["channel"]["id"],
                student_count=len(student_slack_ids),
                error=students_res.get("error")
            )
```

---

## Summary of Metrics

| Operation | Duration Metric | Counter Metric |
|-----------|----------------|----------------|
| Student Project Moves | `learning_api_student_project_move_seconds` | `learning_api_student_project_move_total` |
| Core Skill Updates | `learning_api_core_skill_update_seconds` | `learning_api_core_skill_update_total` |
| Team Assignments | `learning_api_team_assignment_seconds` | `learning_api_team_assignment_total` |
| Slack Channel Creation | `learning_api_slack_channel_create_seconds` | `learning_api_slack_channel_create_total` |
| Slack Invitations | `learning_api_slack_invitation_seconds` | `learning_api_slack_invitation_total` |

---

## Viewing Metrics

### Access the Metrics Endpoint

Once implemented, visit: `http://localhost:8000/metrics`

You'll see output like:
```
# HELP learning_api_student_project_move_seconds Time to move student to different project
# TYPE learning_api_student_project_move_seconds histogram
learning_api_student_project_move_seconds_bucket{le="0.1"} 45.0
learning_api_student_project_move_seconds_bucket{le="0.25"} 89.0
learning_api_student_project_move_seconds_bucket{le="0.5"} 120.0
learning_api_student_project_move_seconds_sum 45.2
learning_api_student_project_move_seconds_count 125.0

# HELP learning_api_student_project_move_total Total student project moves
# TYPE learning_api_student_project_move_total counter
learning_api_student_project_move_total{status="success"} 120.0
learning_api_student_project_move_total{status="error"} 5.0
```

---

## Simple Grafana Queries

### Check Operation Speed (Average Duration)

```promql
# Average time for student project moves
rate(learning_api_student_project_move_seconds_sum[5m]) /
rate(learning_api_student_project_move_seconds_count[5m])

# Average time for core skill updates
rate(learning_api_core_skill_update_seconds_sum[5m]) /
rate(learning_api_core_skill_update_seconds_count[5m])

# Average time for team assignments
rate(learning_api_team_assignment_seconds_sum[5m]) /
rate(learning_api_team_assignment_seconds_count[5m])

# Average time for Slack channel creation
rate(learning_api_slack_channel_create_seconds_sum[5m]) /
rate(learning_api_slack_channel_create_seconds_count[5m])

# Average time for Slack invitations
rate(learning_api_slack_invitation_seconds_sum[5m]) /
rate(learning_api_slack_invitation_seconds_count[5m])
```

### Check Success Rate

```promql
# Student project move success rate
rate(learning_api_student_project_move_total{status="success"}[5m]) /
rate(learning_api_student_project_move_total[5m])

# Core skill update success rate
rate(learning_api_core_skill_update_total{status="success"}[5m]) /
rate(learning_api_core_skill_update_total[5m])

# Team assignment success rate
rate(learning_api_team_assignment_total{status="success"}[5m]) /
rate(learning_api_team_assignment_total[5m])

# Slack channel creation success rate
rate(learning_api_slack_channel_create_total{status="success"}[5m]) /
rate(learning_api_slack_channel_create_total[5m])

# Slack invitation success rate
rate(learning_api_slack_invitation_total{status="success"}[5m]) /
rate(learning_api_slack_invitation_total[5m])
```

### Check Operation Rate (How Often)

```promql
# Student moves per minute
rate(learning_api_student_project_move_total[1m]) * 60

# Skill updates per minute
rate(learning_api_core_skill_update_total[1m]) * 60

# Team assignments per minute
rate(learning_api_team_assignment_total[1m]) * 60

# Slack channels created per hour
rate(learning_api_slack_channel_create_total[1h]) * 3600
```

---

## Simple Alerts

```yaml
# alerts.yml
groups:
  - name: learning_api_performance
    interval: 1m
    rules:
      # Alert if operations are slow
      - alert: SlowStudentMoves
        expr: |
          rate(learning_api_student_project_move_seconds_sum[5m]) /
          rate(learning_api_student_project_move_seconds_count[5m]) > 2.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Student project moves are slow"
          description: "Average duration is {{ $value }}s"
      
      # Alert if operations are failing
      - alert: StudentMoveFailures
        expr: |
          rate(learning_api_student_project_move_total{status="error"}[5m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Student project moves are failing"
          description: "{{ $value }} failures per second"
      
      # Alert if Slack is slow
      - alert: SlowSlackOperations
        expr: |
          rate(learning_api_slack_channel_create_seconds_sum[5m]) /
          rate(learning_api_slack_channel_create_seconds_count[5m]) > 5.0
        for: 5m
        labels:
          severity: warning
        annotations:
          description: "Average duration is {{ $value }}s"
```

---

## Optional: Running Prometheus in Docker Compose

### Benefits of Docker Compose Integration

Adding Prometheus as a service in your [`docker-compose.yml`](../docker-compose.yml) provides several advantages:

1. **Integrated Development Environment** - Everything starts with one `docker compose up` command
2. **Automatic Service Discovery** - Prometheus can scrape your API using Docker's internal networking
3. **Data Persistence** - Metrics data survives container restarts
4. **Production-Like Setup** - Mirrors production deployment architecture
5. **Easy to Add Grafana** - Can add visualization dashboards later

### Recommended Docker Compose Configuration

Add the following services to your [`docker-compose.yml`](../docker-compose.yml):

```yaml
services:
  # ... existing db and web services ...

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    depends_on:
      - web
    restart: unless-stopped

  # Optional: Add Grafana for visualization
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  lp_data:
  prometheus_data:  # Add this
  grafana_data:     # Add this if using Grafana
```

### Create Prometheus Configuration File

Create a `prometheus.yml` file in your project root:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'learning-platform-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['web:8000']  # Uses Docker internal networking
    metrics_path: '/metrics'
```

### Starting the Full Stack

```bash
# Start all services including Prometheus
docker compose up --build

# Or run in detached mode
docker compose up -d --build
```

### Accessing the Services

- **Django API**: http://localhost:8000
- **Metrics Endpoint**: http://localhost:8000/metrics
- **Prometheus UI**: http://localhost:9090
- **Grafana** (if added): http://localhost:3001 (admin/admin)

### Verifying Prometheus is Scraping

1. Visit http://localhost:9090
2. Go to **Status** → **Targets**
3. You should see `learning-platform-api` with state "UP"
4. Try a query like: `learning_api_student_project_move_total`

### Adding Grafana Dashboards

If you added Grafana:

1. Visit http://localhost:3001 and login (admin/admin)
2. Add Prometheus as a data source:
   - URL: `http://prometheus:9090`
   - Access: Server (default)
3. Import or create dashboards using the PromQL queries from this document

### Stopping Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (clears all data)
docker compose down -v
```

---

## Implementation Checklist
          summary: "Slack operations are slow"
          description: "Average duration is {{ $value }}s"
```

---

## Implementation Checklist

- [ ] Install `prometheus-client` and `django-prometheus`
- [ ] Add to `INSTALLED_APPS` and `MIDDLEWARE` in settings
- [ ] Add `/metrics` endpoint to URLs
- [ ] Add metrics to [`student_view.py`](../LearningAPI/views/student_view.py) (Metrics 1 & 3)
- [ ] Add metrics to [`core_skill_record_view.py`](../LearningAPI/views/core_skill_record_view.py) (Metric 2)
- [ ] Add metrics to [`slack.py`](../LearningAPI/views/slack.py) (Metrics 4 & 5)
- [ ] Test by visiting `/metrics` endpoint
- [ ] Set up Prometheus to scrape the endpoint
- [ ] Create basic Grafana dashboard
- [ ] Set up simple alerts

---

## What These Metrics Tell You

1. **Duration metrics** answer: "How fast are my operations?"
2. **Counter metrics** answer: "Are my operations succeeding?"
3. **Rate calculations** answer: "How often are operations happening?"

This simple approach gives you the essential performance data you need without complexity.