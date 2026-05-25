# E-Commerce Backend — Microservices Architecture

![CI Pipeline](https://github.com/Darkblade1995/ecommerce-backend/actions/workflows/ci.yml/badge.svg)

Distributed e-commerce backend built from scratch with production-grade microservices architecture. Features async Python services, a Go WebSocket service, Kubernetes orchestration, distributed tracing, structured logging, and a full CI/CD pipeline.

---

## Architecture

```
Internet
    │
    ▼
Ingress (nginx)
    │
    ▼
API Gateway :8000
    │  JWT validation, RBAC, Rate Limiting
    │
    ├──► User Service :8001
    │      FastAPI + PostgreSQL + JWT
    │
    ├──► Product Service :8002
    │      FastAPI + PostgreSQL + Redis Cache
    │
    └──► Order Service :8003
           FastAPI + PostgreSQL + Kafka
           CQRS + Event Sourcing
               │
               ▼
         Notification Service :8004
               Go + WebSockets + Kafka
```

---

## Services

| Service | Language | Port | Responsibilities |
|---------|----------|------|-----------------|
| api-gateway | Python/FastAPI | 8000 | Single entry point, JWT validation, RBAC, rate limiting |
| user-service | Python/FastAPI | 8001 | Registration, login, JWT access + refresh tokens |
| product-service | Python/FastAPI | 8002 | Product catalog, categories, Redis Cache-Aside pattern |
| order-service | Python/FastAPI | 8003 | Order lifecycle, CQRS, Event Sourcing, Kafka Saga |
| notification-service | Go | 8004 | Real-time WebSocket notifications via Kafka events |

---

## Tech Stack

### Backend
- **FastAPI** — Async REST APIs with Python 3.11
- **Go 1.22** — High-concurrency WebSocket service (goroutines + Hub pattern)
- **SQLAlchemy async** — ORM with asyncpg driver
- **Alembic** — Database migrations

### Infrastructure
- **PostgreSQL 16** — One database per service (database-per-service pattern)
- **Redis 7** — Caching and rate limiting
- **Kafka** — Async event streaming between services
- **Kubernetes** — Container orchestration (minikube)
- **Docker** — Containerization

### Observability
- **Prometheus + Grafana** — Metrics and dashboards
- **Jaeger + OpenTelemetry** — Distributed tracing
- **Structured JSON logging** — python-json-logger

### Security
- **cert-manager** — Automatic TLS certificate management
- **Network Policies** — Pod-level firewall isolation
- **JWT** — Access + refresh token authentication
- **RBAC** — Role-based access control

### CI/CD
- **GitHub Actions** — Tests + Docker build on every push
- **DockerHub** — Container registry

---

## Architecture Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| API Gateway | api-gateway | Single entry point, cross-cutting concerns |
| Repository Pattern | All services | Decouple business logic from data access |
| Service Layer | All services | Orchestrate business operations |
| CQRS | order-service | Separate read/write models for scalability |
| Event Sourcing | order-service | Immutable audit trail of all state changes |
| Cache-Aside | product-service | Redis cache for product reads |
| Saga Pattern | order-service → Kafka | Distributed transaction coordination |
| Hub Pattern | notification-service | Manage 10k+ concurrent WebSocket connections |
| JWT Auth | user-service + gateway | Stateless authentication |
| Rate Limiting | api-gateway | Protect services from abuse |

---

## Kubernetes Infrastructure

```
Namespace: ecommerce
├── Deployments (12)
│   ├── api-gateway (HPA: 2-5 replicas)
│   ├── user-service (HPA: 2-8 replicas)
│   ├── product-service (HPA: 2-8 replicas)
│   ├── order-service (HPA: 2-8 replicas)
│   ├── notification-service
│   ├── user-postgres (PVC: 1Gi)
│   ├── product-postgres (PVC: 1Gi)
│   ├── order-postgres (PVC: 1Gi)
│   ├── redis
│   ├── prometheus
│   ├── grafana
│   └── jaeger
├── Ingress (subdomain routing)
├── Network Policies (5 isolation rules)
├── HPA (CPU-based autoscaling)
└── cert-manager (TLS certificates)
```

---

## Observability URLs (local)

| Service | URL |
|---------|-----|
| API Gateway | http://ecommerce.local:8080 |
| Order Service | http://orders.ecommerce.local:8080 |
| Prometheus | http://monitor.ecommerce.local:8080 |
| Grafana | http://grafana.ecommerce.local:8080 |
| Jaeger UI | http://tracing.ecommerce.local:8080 |

---

## Running on Kubernetes

```bash

minikube start --driver=docker --memory=4096 --cpus=2
minikube addons enable ingress
minikube addons enable metrics-server


kubectl apply -f k8s/namespace/namespace.yaml
kubectl apply -f k8s/configmaps/configmap.yaml
kubectl apply -f k8s/secrets/secrets.yaml
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/network-policies.yaml


kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.4/cert-manager.yaml
kubectl apply -f k8s/cert-manager/issuer.yaml


kubectl port-forward -n ingress-nginx service/ingress-nginx-controller 8080:80 8443:443


kubectl get pods -n ecommerce
curl http://ecommerce.local:8080/health
```

---

## Running Tests

```bash

cd services/user-service
pytest tests/ -v


cd services/product-service
pytest tests/ -v


cd services/order-service
pytest tests/ -v
```

---

## CI/CD Pipeline

Every push to `main` triggers:

```
push to main
    │
    ├── test-user-service    (16 tests)  ──┐
    ├── test-product-service (12 tests)  ──┤── parallel
    └── test-order-service   (12 tests)  ──┘
                │
                ▼ (all pass)
            build job
                │
                ├── build + push user-service → DockerHub
                ├── build + push product-service → DockerHub
                ├── build + push order-service → DockerHub
                ├── build + push notification-service → DockerHub
                └── build + push api-gateway → DockerHub
```

---

## API Documentation

Swagger UI available when `DEBUG=True`:

| Service | URL |
|---------|-----|
| API Gateway | http://localhost:8000/docs |
| User Service | http://localhost:8001/docs |
| Product Service | http://localhost:8002/docs |
| Order Service | http://localhost:8003/docs |

---

## Key Design Decisions

**Why Go for notifications?**
Go goroutines use ~2KB of stack vs Python's heavier coroutine model. For 10,000 concurrent WebSocket connections, Go uses ~20MB vs ~500MB in Python. The Hub pattern with channels provides thread-safe connection management without locks.

**Why CQRS + Event Sourcing for orders?**
Orders are the most critical domain. Event Sourcing provides an immutable audit trail — every state change is recorded. CQRS separates the write model (commands) from the read model (queries), making each independently scalable.

**Why database-per-service?**
Each service owns its data. Services can't directly query each other's databases — they must go through APIs. This enforces loose coupling and allows each service to use the optimal schema for its domain.

**Why Redis Cache-Aside for products?**
Product catalog is read-heavy. Cache-Aside loads data into Redis on first read and invalidates on write. Subsequent reads hit Redis (sub-millisecond) instead of PostgreSQL.


---

## Author

**Luis Fernando Agamez Atehortua**
Backend Developer

[![GitHub](https://img.shields.io/badge/GitHub-Darkblade1995-181717?style=flat&logo=github)](https://github.com/Darkblade1995)