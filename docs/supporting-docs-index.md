# Supporting Documentation Index

This document lists all supporting documentation referenced in the [Eventing Plan](../eventing-plan.md). Documents marked with ✅ have been created. Others will be created as needed during implementation.

## 📚 Core Concepts

- [What is a Message Queue?](message-queue-explained.md) - Introduction to message queues and why we use them
- [Event-Driven Architecture Explained](event-driven-architecture.md) - Understanding event-driven systems
- ✅ [RabbitMQ Concepts Explained](rabbitmq-concepts-explained.md) - Exchanges, queues, routing keys explained
- [Sync vs Async Explained](sync-vs-async.md) - Difference between synchronous and asynchronous processing
- [Microservices Explained](microservices-explained.md) - What microservices are and why we use them

## 🛠️ Setup Guides

- [RabbitMQ Setup Guide](rabbitmq-setup-guide.md) - Step-by-step RabbitMQ configuration
- [Database Design for Job Tracking](database-design-explained.md) - How to design job tracking tables
- [Message Schema Design](message-schema-design.md) - Designing message formats
- [FastAPI Quickstart](fastapi-quickstart.md) - Getting started with FastAPI
- [CloudAMQP Setup Guide](cloudamqp-setup-guide.md) - Setting up managed RabbitMQ

## 💻 Implementation Guides

### Django/Python
- [Publishing Messages to RabbitMQ](publishing-messages.md) - How to send messages from Django
- [Consuming Messages from RabbitMQ](consuming-messages.md) - How to receive and process messages
- [Building Async API Endpoints](async-api-endpoints.md) - Creating endpoints that return immediately
- [Sharing Databases Between Services](sharing-databases.md) - Multiple services, one database

### GitHub Integration
- [GitHub API Best Practices](github-api-best-practices.md) - Working with GitHub API effectively
- [Handling Rate Limits](handling-rate-limits.md) - Dealing with API rate limits

### Architecture
- [Orchestration Patterns](orchestration-patterns.md) - Coordinating multi-step processes
- [Error Handling Strategies](error-handling-strategies.md) - How to handle errors in distributed systems

### Frontend
- [Polling in React](polling-in-react.md) - Implementing polling for real-time updates
- [React Forms Best Practices](react-forms-best-practices.md) - Building good forms
- [Progress Visualization Examples](progress-visualization-examples.md) - UI patterns for showing progress

## 🧪 Testing Guides

- [Testing Async Systems](testing-async-systems.md) - Testing asynchronous code
- [Testing Async Services](testing-async-services.md) - Testing FastAPI services
- [Testing React Components](testing-react-components.md) - Testing React UI
- [Testing Distributed Systems](testing-distributed-systems.md) - End-to-end testing
- [Mocking External Services](mocking-external-services.md) - How to mock RabbitMQ, databases, etc.
- [Mocking GitHub API](mocking-github-api.md) - Testing without hitting real GitHub

## 📋 Code Templates

### Backend Templates
- [Model Template](model-template.md) - Django model example
- [Schema Template](schema-template.md) - Pydantic schema example
- [RabbitMQ Client Template](rabbitmq-client-template.md) - Connection manager code
- [Publisher Template](publisher-template.md) - Message publisher code
- [Consumer Template](consumer-template.md) - Message consumer code
- [API Endpoint Template](api-endpoint-template.md) - Django REST endpoint code
- [GitHub Service Template](github-service-template.md) - GitHub API integration code
- [Orchestrator Template](orchestrator-template.md) - Job orchestration code
- [Database Connection Template](database-connection-template.md) - SQLAlchemy setup
- [SQLAlchemy Models Template](sqlalchemy-models-template.md) - SQLAlchemy model examples
- [Repository Pattern Template](repository-pattern-template.md) - Data access layer code

### Infrastructure Templates
- [Dockerfile Template](dockerfile-template.md) - Docker container configuration
- [Project Structure Template](project-structure-template.md) - How to organize code
- [Docker Compose Multi-Service Setup](docker-compose-multi-service.md) - Running multiple services

### Frontend Templates
- [Button Component Template](button-component-template.md) - React button component
- [Modal Component Template](modal-component-template.md) - React modal component
- [Progress Page Template](progress-page-template.md) - Progress tracking page

### Deployment Templates
- [Deployment Template](deployment-template.md) - Deployment configuration
- [CI/CD Template](cicd-template.md) - Continuous integration/deployment
- [Runbook Template](runbook-template.md) - Operations runbook

## 🚀 Advanced Topics

- [Async Python Tutorial](async-python-tutorial.md) - Understanding async/await in Python
- [Debugging Distributed Systems](debugging-distributed-systems.md) - Troubleshooting techniques
- [Deploying Microservices](deploying-microservices.md) - Deployment strategies
- [Secrets Management Best Practices](secrets-management.md) - Securing credentials
- [Monitoring Distributed Systems](monitoring-distributed-systems.md) - Observability and monitoring
- [Securing Connection Strings](securing-connection-strings.md) - Protecting sensitive data
- [Technical Documentation Best Practices](technical-documentation-best-practices.md) - Writing good docs

---

## 📝 Creating New Documentation

When creating a new supporting document:

1. **Use clear, beginner-friendly language**
2. **Include code examples**
3. **Add diagrams where helpful**
4. **Provide "Why" explanations, not just "How"**
5. **Link to official documentation for deeper learning**
6. **Test all code examples**

### Document Template

```markdown
# [Topic Name]

## What is it?
[Plain English explanation]

## Why do we need it?
[Explain the problem it solves]

## How does it work?
[Step-by-step explanation with diagrams]

## Code Example
[Working code with comments]

## Common Pitfalls
[Things beginners often get wrong]

## Further Reading
[Links to official docs, tutorials]
```

---

*Last Updated: 2026-03-12*
