# E-Commerce Backend — Microservices Architecture

Distributed e-commerce backend built with microservices architecture. Features FastAPI services for users, products, and orders with PostgreSQL, Redis caching, Kafka event streaming, CQRS, Event Sourcing, and a real-time notification service in Go with WebSockets. Deployed on Kubernetes with Docker containers.

## Architecture

```
Client
  │
  ▼
API Gateway :8000 (FastAPI)
  │
  ├── User Service :8001 (FastAPI + PostgreSQL)
  ├── Product Service :8002 (FastAPI + PostgreSQL + Redis)
  ├── Order Service :8003 (FastAPI + PostgreSQL + Kafka)
  └── Notification Service :8004 (Go + WebSockets + Kafka)
```

## Services

| Service | Language | Port | Description |
|---------|----------|------|-------------|
| api-gateway | Python/FastAPI | 8000 | Single entry point, JWT validation, rate limiting |
| user-service | Python/FastAPI | 8001 | Authentication, JWT, user management |
| product-service | Python/FastAPI | 8002 | Product catalog with Redis cache |
| order-service | Python/FastAPI | 8003 | Orders with CQRS and Event Sourcing |
| notification-service | Go | 8004 | Real-time WebSocket notifications |

## Tech Stack

- **FastAPI** — REST APIs with async/await
- **Go** — High-performance WebSocket service
- **PostgreSQL** — Primary database (one per service)
- **Redis** — Caching and rate limiting
- **Kafka** — Async event streaming between services
- **Kubernetes** — Container orchestration
- **Docker** — Containerization
- **GitHub Actions** — CI/CD pipeline

## Patterns Implemented

- Repository Pattern
- Service Layer
- CQRS (Command Query Responsibility Segregation)
- Event Sourcing
- Cache-Aside Pattern
- Saga Pattern
- API Gateway Pattern
- JWT Authentication (access + refresh tokens)
- Rate Limiting
- RBAC (Role Based Access Control)

## Local Development

### Prerequisites
- Python 3.11+
- Go 1.22+
- Docker Desktop
- kubectl + minikube

### Run locally

```bash
# Infrastructure
cd services/user-service && docker-compose up -d
cd services/product-service && docker-compose up -d
cd services/order-service && docker-compose up -d
docker run -d -p 6379:6379 redis:7-alpine

# Services
uvicorn app.main:app --port 8001 --reload  # user-service
uvicorn app.main:app --port 8002 --reload  # product-service
uvicorn app.main:app --port 8003 --reload  # order-service
uvicorn app.main:app --port 8000           # api-gateway
go run . # notification-service
```

### Run on Kubernetes

```bash
minikube start --driver=docker --memory=4096 --cpus=2
kubectl apply -f k8s/namespace/namespace.yaml
kubectl apply -f k8s/configmaps/configmap.yaml
kubectl apply -f k8s/secrets/secrets.yaml
kubectl apply -f k8s/deployments/
kubectl get pods -n ecommerce
```

### Run tests

```bash
cd services/user-service
pytest tests/ -v
```

## CI/CD

Every push to `main` triggers the GitHub Actions pipeline:

1. Runs tests for all services
2. Builds Docker images
3. Pushes to DockerHub

## API Documentation

When running locally, Swagger UI is available at:

- Gateway: `http://localhost:8000/docs`
- User Service: `http://localhost:8001/docs`
- Product Service: `http://localhost:8002/docs`
- Order Service: `http://localhost:8003/docs`

## Environment Variables

Each service requires a `.env` file. See `.env.example` in each service directory.
