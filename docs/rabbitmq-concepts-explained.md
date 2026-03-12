# RabbitMQ Concepts Explained (Beginner-Friendly)

## The Post Office Analogy

Think of RabbitMQ like a post office system:

### 1. **Exchange** = Post Office Sorting Center
- **What it is:** The first place messages arrive when you send them
- **What it does:** Decides which mailbox(es) should receive your message based on rules
- **In our case:** `github_distribution` is the name of our sorting center

**Types of Exchanges:**
- **Direct:** Like addressing a letter to a specific person - exact match required
- **Topic:** Like addressing mail by department (e.g., "engineering.*") - pattern matching
- **Fanout:** Like a mass mailing - sends to everyone
- **Headers:** Routes based on message metadata

**Why we chose Topic Exchange:**
- Flexible routing patterns
- Can add more specific routing later (e.g., `distribution.issue.create`, `distribution.issue.update`)
- Allows filtering by message type

---

### 2. **Queue** = Mailbox
- **What it is:** Where messages wait to be picked up and processed
- **What it does:** Stores messages until a consumer (Migration Service) reads them
- **In our case:** `issue_distribution_queue` is our mailbox name

**Key Properties:**
- **Durable:** Survives RabbitMQ restarts (messages aren't lost)
- **Persistent:** Messages are saved to disk
- **FIFO:** First In, First Out (usually)

**Why we need it:**
- Django publishes messages faster than Migration Service can process them
- Acts as a buffer during high load
- Ensures no messages are lost if Migration Service is temporarily down

---

### 3. **Routing Key** = Address Label
- **What it is:** A label you put on your message when sending it
- **What it does:** Tells the Exchange which Queue(s) should receive this message
- **In our case:** `distribution.issue.create` is our address label

**How it works:**
- Django publishes a message with routing key: `distribution.issue.create`
- Exchange looks at the routing key
- Exchange checks which queues are "subscribed" to that pattern
- Exchange delivers the message to matching queues

**Why this format:**
- Hierarchical naming: `<domain>.<resource>.<action>`
- Easy to extend: Later add `distribution.issue.update`, `distribution.issue.delete`
- Clear intent: Anyone reading the code knows what this message does

---

## How They Work Together

```
┌─────────────────────────────────────────────────────────────────┐
│                         RabbitMQ Broker                         │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. Django publishes message                             │  │
│  │     - routing_key: "distribution.issue.create"           │  │
│  │     - body: {job_id, source_repo, target_repos, ...}     │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  2. Exchange: "github_distribution" (topic)              │  │
│  │     - Receives message                                   │  │
│  │     - Looks at routing key: "distribution.issue.create"  │  │
│  │     - Checks binding rules                               │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  3. Queue: "issue_distribution_queue"                    │  │
│  │     - Bound to exchange with pattern: "distribution.#"   │  │
│  │     - Receives message (matches pattern)                 │  │
│  │     - Stores message until consumed                      │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            ▼
               ┌────────────────────────────┐
               │  4. Migration Service      │
               │     - Consumes message     │
               │     - Processes job        │
               │     - Acknowledges message │
               └────────────────────────────┘
```

---

## Binding: The Missing Piece

**Binding** = Subscription rule that connects a Queue to an Exchange

When you set up RabbitMQ, you create a binding that says:
```
Queue "issue_distribution_queue" 
  should receive messages from 
  Exchange "github_distribution" 
  when routing key matches pattern "distribution.#"
```

The `#` is a wildcard meaning "match anything after this"
- Matches: `distribution.issue.create` ✓
- Matches: `distribution.issue.update` ✓
- Matches: `distribution.anything.else` ✓
- Doesn't match: `notification.issue.create` ✗

---

## Simple Setup for Your Project

### Option 1: Manual Setup (via Management UI)

1. **Start RabbitMQ:** `docker-compose up rabbitmq`
2. **Open Management UI:** http://localhost:15672 (login: guest/guest)
3. **Create Exchange:**
   - Go to "Exchanges" tab
   - Click "Add a new exchange"
   - Name: `github_distribution`
   - Type: `topic`
   - Durability: `Durable`
   - Click "Add exchange"

4. **Create Queue:**
   - Go to "Queues" tab
   - Click "Add a new queue"
   - Name: `issue_distribution_queue`
   - Durability: `Durable`
   - Click "Add queue"

5. **Create Binding:**
   - Click on the queue name `issue_distribution_queue`
   - Scroll to "Bindings" section
   - Under "Add binding from this queue":
     - From exchange: `github_distribution`
     - Routing key: `distribution.#`
   - Click "Bind"

### Option 2: Automated Setup (Python Script)

Create `setup_rabbitmq.py`:
```python
import pika

# Connect to RabbitMQ
connection = pika.BlockingConnection(
    pika.ConnectionParameters('localhost')
)
channel = connection.channel()

# 1. Declare Exchange
channel.exchange_declare(
    exchange='github_distribution',
    exchange_type='topic',
    durable=True
)

# 2. Declare Queue
channel.queue_declare(
    queue='issue_distribution_queue',
    durable=True
)

# 3. Bind Queue to Exchange
channel.queue_bind(
    exchange='github_distribution',
    queue='issue_distribution_queue',
    routing_key='distribution.#'
)

print("✓ RabbitMQ setup complete!")
connection.close()
```

Run once: `python setup_rabbitmq.py`

### Option 3: Setup in Your Application Code

Both Django publisher and Migration Service consumer can declare these resources when they start. RabbitMQ is idempotent - declaring something that already exists is safe.

**In Django (publisher.py):**
```python
channel.exchange_declare(
    exchange='github_distribution',
    exchange_type='topic',
    durable=True
)
```

**In Migration Service (consumer.py):**
```python
channel.exchange_declare(
    exchange='github_distribution',
    exchange_type='topic',
    durable=True
)
channel.queue_declare(
    queue='issue_distribution_queue',
    durable=True
)
channel.queue_bind(
    exchange='github_distribution',
    queue='issue_distribution_queue',
    routing_key='distribution.#'
)
```

---

## Common Patterns

### Pattern 1: Single Queue, Single Consumer (Your Current Setup)
```
Django → Exchange → Queue → Migration Service
```
**Use case:** Simple, one type of job, one processor

### Pattern 2: Multiple Queues, Specialized Consumers
```
Django → Exchange → Queue 1 (high priority) → Fast Consumer
                 → Queue 2 (low priority)  → Slow Consumer
```
**Use case:** Different priority levels

### Pattern 3: Multiple Consumers, Same Queue (Load Balancing)
```
Django → Exchange → Queue → Consumer 1
                         → Consumer 2
                         → Consumer 3
```
**Use case:** Scale horizontally, process jobs faster

---

## Key Concepts Summary

| Concept | Purpose | Your Value |
|---------|---------|------------|
| **Exchange** | Routes messages to queues | `github_distribution` |
| **Queue** | Stores messages for processing | `issue_distribution_queue` |
| **Routing Key** | Label for routing decisions | `distribution.issue.create` |
| **Binding** | Connects queue to exchange | Pattern: `distribution.#` |
| **Publisher** | Sends messages (Django) | Your Django API |
| **Consumer** | Receives messages | Your Migration Service |

---

## Testing Your Setup

### 1. Verify Setup
```bash
# Check exchange exists
curl -u guest:guest http://localhost:15672/api/exchanges/%2F/github_distribution

# Check queue exists
curl -u guest:guest http://localhost:15672/api/queues/%2F/issue_distribution_queue

# Check binding exists
curl -u guest:guest http://localhost:15672/api/bindings/%2F/e/github_distribution/q/issue_distribution_queue
```

### 2. Send Test Message (Python)
```python
import pika
import json

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

message = {
    "version": "1.0",
    "job_id": "test-123",
    "source_repo": {"owner": "test", "name": "template"},
    "target_repos": [{"owner": "student1", "name": "repo"}],
    "issue_ids": [1, 2, 3]
}

channel.basic_publish(
    exchange='github_distribution',
    routing_key='distribution.issue.create',
    body=json.dumps(message)
)

print("✓ Test message sent!")
connection.close()
```

### 3. Check Message in Queue
- Open http://localhost:15672
- Go to "Queues" tab
- Click `issue_distribution_queue`
- You should see "Ready: 1" (one message waiting)
- Click "Get messages" to preview it

---

## Troubleshooting

### Message not appearing in queue?
- Check exchange name matches exactly
- Check routing key matches binding pattern
- Check queue is bound to exchange
- Check message was published successfully

### Consumer not receiving messages?
- Check consumer is connected to correct queue
- Check consumer acknowledged previous messages
- Check queue has messages (Ready > 0)
- Check consumer code is running

### Messages disappearing?
- Check if consumer is auto-acknowledging without processing
- Check if queue is set to durable
- Check if messages are set to persistent

---

## Next Steps

1. **Start simple:** Use the manual setup via Management UI first
2. **Test with Python script:** Send a test message and verify it appears in the queue
3. **Implement Django publisher:** Send real messages from your API
4. **Implement Migration Service consumer:** Process messages from the queue
5. **Add error handling:** Dead letter queues, retries, monitoring

---

*This document is part of the Async GitHub Issue Distribution project*  
*Last Updated: 2026-03-11*
