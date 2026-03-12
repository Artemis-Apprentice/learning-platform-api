# Quick Start Guide: Async GitHub Issue Distribution

> **For Beginners:** This is your starting point. Read this first, then dive into the [full eventing plan](../eventing-plan.md).

---

## 🎯 What You're Building

A system that lets instructors distribute GitHub issues to 50+ student repositories **without waiting**. Instead of a 5-minute loading spinner, they get instant feedback and can watch progress in real-time.

---

## 🏗️ The Big Picture

```
Instructor clicks button
    ↓
Django creates job & sends message to RabbitMQ
    ↓
Django returns job ID immediately (no waiting!)
    ↓
React polls for progress every 2 seconds
    ↓
Migration Service processes job in background
    ↓
Instructor sees: "15 of 50 repos completed..."
```

---

## 📦 What You Need to Learn

### Week 1: Core Concepts
1. **Message Queues** - Like a to-do list between services
   - Read: [RabbitMQ Concepts Explained](rabbitmq-concepts-explained.md) ✅
   - Read: [What is a Message Queue?](message-queue-explained.md)
   
2. **Async vs Sync** - Why we don't wait for things to finish
   - Read: [Sync vs Async Explained](sync-vs-async.md)

3. **Event-Driven Architecture** - Services talk via messages
   - Read: [Event-Driven Architecture Explained](event-driven-architecture.md)

### Week 2-3: Implementation Skills
4. **Publishing Messages** (Django side)
   - Read: [Publishing Messages to RabbitMQ](publishing-messages.md)
   
5. **Consuming Messages** (Migration Service side)
   - Read: [Consuming Messages from RabbitMQ](consuming-messages.md)
   
6. **GitHub API** - Copying issues between repos
   - Read: [GitHub API Best Practices](github-api-best-practices.md)

### Week 4-5: Frontend & Testing
7. **Polling in React** - Checking progress repeatedly
   - Read: [Polling in React](polling-in-react.md)
   
8. **Testing Distributed Systems**
   - Read: [Testing Distributed Systems](testing-distributed-systems.md)

---

## 🚀 Your 6-Week Journey

| Week | What You'll Build | Key Learning |
|------|-------------------|--------------|
| **1** | RabbitMQ + Database setup | Infrastructure basics |
| **2** | Django API endpoints | Publishing messages |
| **3-4** | Migration Service | Consuming messages, GitHub API |
| **5** | React UI | Polling, progress tracking |
| **6** | Deploy & Document | Integration, monitoring |

---

## 👥 Team Roles

### Developer 1: Infrastructure & Messaging
**Weeks 1-4:**
- Set up RabbitMQ
- Build message publisher (Django)
- Build message consumer (Migration Service)
- **Skills to learn:** RabbitMQ, async Python

**Week 5 (React):**
- Build distribution UI components (button, modal, form)
- **Skills to learn:** React forms, API integration

---

### Developer 2: Backend & Database
**Weeks 1-4:**
- Design database schema
- Build Django API endpoints
- Build database layer for Migration Service
- Build orchestration logic
- **Skills to learn:** Django REST, SQLAlchemy

**Week 5 (React):**
- Build progress tracking UI (polling, progress visualization)
- **Skills to learn:** React hooks, polling patterns

---

### Developer 3: Integration & Testing
**Weeks 1-4:**
- Define message schema
- Write tests for Django and Migration Service
- Build GitHub API integration
- **Skills to learn:** Testing, GitHub API, mocking

**Week 5 (React):**
- Write React component tests
- End-to-end testing
- **Skills to learn:** React Testing Library

---

**Week 6:** All three developers work together on integration testing and deployment

---

## 🛠️ Tools You'll Use

### Already Familiar
- ✅ Django (your existing API)
- ✅ PostgreSQL (your existing database)
- ✅ React (your existing frontend)
- ✅ Docker (you're already using it)

### New Tools
- 🆕 **RabbitMQ** - Message broker (runs in Docker)
- 🆕 **FastAPI** - For the Migration Service (similar to Django but simpler)
- 🆕 **Pika** - Python library for RabbitMQ
- 🆕 **PyGithub** - Python library for GitHub API

---

## 📝 Day 1 Checklist

Before you start coding, make sure everyone on the team:

- [ ] Reads this Quick Start Guide
- [ ] Reads [RabbitMQ Concepts Explained](rabbitmq-concepts-explained.md)
- [ ] Understands the system architecture diagram in [eventing-plan.md](../eventing-plan.md)
- [ ] Has Docker running locally
- [ ] Has access to GitHub (for testing)
- [ ] Reviews the [Supporting Documentation Index](supporting-docs-index.md)

---

## 🎓 Learning Path

### If you've never used message queues:
1. Read [What is a Message Queue?](message-queue-explained.md)
2. Read [RabbitMQ Concepts Explained](rabbitmq-concepts-explained.md)
3. Follow [RabbitMQ Setup Guide](rabbitmq-setup-guide.md)
4. Send your first test message using the Management UI

### If you've never built async APIs:
1. Read [Sync vs Async Explained](sync-vs-async.md)
2. Read [Building Async API Endpoints](async-api-endpoints.md)
3. Look at the [API Endpoint Template](api-endpoint-template.md)

### If you've never used FastAPI:
1. Read [FastAPI Quickstart](fastapi-quickstart.md)
2. Follow the official FastAPI tutorial (first 3 chapters)
3. Look at the [Project Structure Template](project-structure-template.md)

### If you've never worked with GitHub API:
1. Read [GitHub API Best Practices](github-api-best-practices.md)
2. Get a Personal Access Token from GitHub
3. Try fetching issues from a test repo using PyGithub

---

## 🆘 When You Get Stuck

### "I don't understand RabbitMQ concepts"
→ Re-read [RabbitMQ Concepts Explained](rabbitmq-concepts-explained.md)  
→ Watch the official RabbitMQ tutorial videos  
→ Draw the flow on a whiteboard with your team

### "My message isn't appearing in the queue"
→ Check RabbitMQ Management UI (http://localhost:15672)  
→ Verify exchange name matches exactly  
→ Verify routing key matches binding pattern  
→ Check Django logs for publish errors

### "Migration Service isn't processing messages"
→ Check if service is running: `docker-compose ps`  
→ Check service logs: `docker-compose logs migration-service`  
→ Verify RabbitMQ connection in logs  
→ Check if consumer is connected in RabbitMQ Management UI

### "Tests are failing"
→ Read [Testing Async Systems](testing-async-systems.md)  
→ Make sure you're mocking external services  
→ Check test database is separate from dev database  
→ Run tests individually to isolate failures

### "GitHub API rate limit hit"
→ Read [Handling Rate Limits](handling-rate-limits.md)  
→ Use GitHub App instead of Personal Access Token (higher limits)  
→ Implement rate limit checking before operations  
→ Add exponential backoff

---

## 💡 Pro Tips

1. **Start Small:** Test with 3 repos before trying 50
2. **Use Management UIs:** RabbitMQ (port 15672) and Grafana (port 3001) are your friends
3. **Log Everything:** You'll thank yourself when debugging
4. **Test Failures:** Intentionally break things to see what happens
5. **Pair Program:** Especially for new concepts like RabbitMQ
6. **Document as You Go:** Future you will appreciate it

---

## 📊 Success Metrics

You'll know you're done when:

- ✅ Instructor can distribute issues to 50 repos
- ✅ API responds in < 1 second (returns job ID)
- ✅ Progress updates every 2 seconds in React
- ✅ Full distribution completes in < 5 minutes
- ✅ Failed repos don't stop the whole job
- ✅ All tests pass
- ✅ System works in staging environment
- ✅ Documentation is complete

---

## 🎉 Milestones to Celebrate

- 🎊 **Week 1:** RabbitMQ running and you sent your first message!
- 🎊 **Week 2:** Django publishes messages and they appear in the queue!
- 🎊 **Week 3:** Migration Service consumes a message and processes it!
- 🎊 **Week 4:** First successful issue copied to GitHub!
- 🎊 **Week 5:** React shows real-time progress!
- 🎊 **Week 6:** Full end-to-end test with 50 repos succeeds!

---

## 📚 Next Steps

1. **Read the full plan:** [eventing-plan.md](../eventing-plan.md)
2. **Review supporting docs:** [supporting-docs-index.md](supporting-docs-index.md)
3. **Set up your environment:** Follow Phase 1, Step 1.1
4. **Have a team kickoff:** Discuss the architecture and assign roles

---

## 🤝 Team Communication

### Daily Standup Questions
- What did you complete yesterday?
- What are you working on today?
- Are you blocked on anything?
- Did you learn something new you want to share?

### Weekly Review Questions
- Did we hit our milestone for this week?
- What went well?
- What was harder than expected?
- What do we need to adjust for next week?

---

**Remember:** Everyone is learning. It's okay to ask questions. It's okay to make mistakes. That's how you grow! 🌱

---

*Ready to start? Head to the [full eventing plan](../eventing-plan.md) and begin with Phase 1!*
