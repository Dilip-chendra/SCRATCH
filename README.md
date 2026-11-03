# SCRATCH — AI Growth Operations & Sales Intelligence Platform
## Phase 0: System Foundation, Multi-Tenancy & Architectural Substrate

SCRATCH is a production-oriented, evidence-grounded AI Growth Operations and Sales Intelligence Platform. Phase 0 delivers the foundational architecture: multi-tenant isolation with PostgreSQL Row-Level Security (RLS), Argon2id authentication with refresh token rotation and CSRF protection, Celery-to-Redis background task execution, and a live Next.js system health telemetry shell.

---

## 1. Phase 0 Architecture & Security Design

```
┌────────────────────────────────────────────────────────────────────────┐
│                        NEXT.JS 14 APP ROUTER                           │
│        (TypeScript, Tailwind CSS Dark Theme, Radix UI Primitives)      │
│  - /login & /register (HttpOnly Cookie Auth, CSRF Protected)          │
│  - /health (Live Real-Time Telemetry: DB, Redis, Celery Latency)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ JSON / Cookies over HTTPS
┌───────────────────────────────────▼────────────────────────────────────┐
│                    FASTAPI APPLICATION GATEWAY (Python 3.12)           │
│  - Argon2id Password Hasher (OWASP Recommended: 64MB, 3 iterations)   │
│  - JWT Access Tokens (15 min) + Refresh Token Rotation & Family Reuse  │
│  - Double-Submit Cookie CSRF Defense Middleware                       │
│  - Validated Tenant Context: set_config('app.current_tenant_id', ...)  │
└─────────┬─────────────────────────┬──────────────────────────┬─────────┘
          │                         │                          │
┌─────────▼───────────────┐ ┌───────▼────────────────┐ ┌───────▼─────────┐
│   DATABASE ACCESS ROLES │ │  CELERY DISTRIBUTED    │ │  REDIS 7 BROKER │
│ - scratch_migrator      │ │  - Idempotent Ping     │ │  - Queue:       │
│   (Table Owner, DDL)    │ │    Task with Retries   │ │    'default'    │
│ - scratch_app           │ │  - Soft & Hard Timeouts│ │  - DB 0 (Broker)│
│   (Non-superuser, DML,  │ │  - State in Result     │ │  - DB 1 (Result)│
│    NOBYPASSRLS)         │ │    Backend             │ │                 │
└─────────┬───────────────┘ └───────┬────────────────┘ └─────────────────┘
          │                         │
┌─────────▼─────────────────────────▼────────────────────────────────────┐
│                       POSTGRESQL 16 (RLS ENFORCED)                     │
│  - FORCE ROW LEVEL SECURITY enabled on all tenant-owned tables         │
│  - Parameterized set_config() local to explicit transaction            │
│  - Automatic reset on transaction commit/rollback (No Pool Contam)     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Directory Structure

```
scratch/
├── apps/
│   ├── web/                         # Next.js 14 Frontend Application
│   │   ├── app/
│   │   │   ├── (auth)/              # Real Login & Registration pages
│   │   │   ├── (dashboard)/         # Authenticated shell & Live Health Telemetry
│   │   │   ├── globals.css          # Dark palette (#050505, #0A0A0C, #00D6FF)
│   │   │   └── layout.tsx
│   │   ├── lib/                     # Typed API client, Auth Context, Cookie helpers
│   │   ├── package.json
│   │   ├── tailwind.config.ts
│   │   └── Dockerfile
│   │
│   └── api/                         # FastAPI Backend Application
│       ├── app/
│       │   ├── core/                # Config (Pydantic), Security (Argon2id), DB, RLS
│       │   ├── models/              # SQLAlchemy 2.0 Async Tenancy Models
│       │   ├── schemas/             # Pydantic v2 Contracts
│       │   ├── api/                 # FastAPI Endpoints (/auth, /workspaces, /health)
│       │   ├── workers/             # Celery Worker Application & Tasks
│       │   └── main.py              # Application Entrypoint
│       ├── alembic/                 # Reversible Database Migrations (001_core_tenancy)
│       ├── tests/                   # 11 Automated Test Suites (33 unit/integration tests)
│       ├── requirements.txt
│       ├── pyproject.toml           # Pytest, Ruff, Mypy configurations
│       └── Dockerfile
│
├── docker-compose.yml               # Local Multi-Container Development Topology
├── init-roles.sql                   # Database Role Separation Bootstrap (scratch_app vs migrator)
├── .env.example                     # Exhaustive configuration template
├── .gitignore
└── README.md
```

---

## 3. Local Development Setup

### Option A: Full Docker Compose (Recommended)
1. Ensure **Docker Desktop** is running on your machine.
2. Copy configuration:
   ```bash
   cp .env.example .env
   ```
3. Start the entire containerized topology:
   ```bash
   docker compose up --build
   ```
4. Access services:
   - **Next.js Web Frontend**: [http://localhost:3000](http://localhost:3000)
   - **FastAPI Backend Gateway**: [http://localhost:8000](http://localhost:8000)
   - **Interactive API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Backend Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### Option B: Host Native Execution (Hybrid)
1. **Backend Setup**:
   ```bash
   cd apps/api
   pip install -r requirements.txt
   ```
2. **Database & Migrations**:
   Run database migrations using Alembic:
   ```bash
   alembic upgrade head
   ```
3. **Start FastAPI Gateway**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. **Start Celery Worker**:
   ```bash
   celery -A app.workers.celery_app worker --loglevel=info -Q default
   ```
5. **Frontend Setup**:
   ```bash
   cd ../web
   npm install
   npm run dev
   ```

---

## 4. Running Automated Tests

SCRATCH Phase 0 includes **11 explicit test suites** covering configuration, cryptographic authentication, workspace authorization, PostgreSQL Row-Level Security, connection pool safety, Alembic migrations, Celery worker task execution, and frontend integration.

Run the complete test suite:
```bash
python -m pytest apps/api/tests -v
```

Expected output:
```
apps/api/tests/test_auth.py ...... [ 18%]
apps/api/tests/test_config.py ..... [ 33%]
apps/api/tests/test_frontend_integration.py .. [ 39%]
apps/api/tests/test_health_api.py .. [ 45%]
apps/api/tests/test_migrations.py .. [ 51%]
apps/api/tests/test_missing_context.py ... [ 60%]
apps/api/tests/test_pool_contamination.py .. [ 66%]
apps/api/tests/test_rls_isolation.py .. [ 72%]
apps/api/tests/test_worker_execution.py ... [ 81%]
apps/api/tests/test_worker_faults.py .. [ 87%]
apps/api/tests/test_workspace_access.py .... [100%]

============================= 33 passed in 11.79s =============================
```

---

## 5. Security & Tenancy Verification

1. **Transaction-Scoped Tenant Setting**:
   Instead of unparameterized `SET LOCAL`, the system executes:
   ```sql
   SELECT set_config('app.current_tenant_id', :workspace_id, true);
   ```
   The parameter `true` sets `is_local = true`, guaranteeing that the setting reverts automatically upon transaction commit or rollback.
2. **Dedicated Role Isolation**:
   - `scratch_migrator`: Table owner used exclusively by Alembic for DDL operations.
   - `scratch_app`: Runtime user with `NOSUPERUSER` and `NOBYPASSRLS`. All queries executed by the application are strictly subject to RLS policies.
3. **Double-Submit Cookie CSRF Protection**:
   All state-changing endpoints (`POST`, `PUT`, `DELETE`, `PATCH`) require a matching `X-CSRF-Token` header for cookie-authenticated requests, preventing cross-site request forgery.
4. **Token Reuse Detection**:
   When a refresh token is rotated, the previous token is marked revoked. If a revoked token is presented again, the system detects a token-reuse attack, revokes the entire token family, logs a security audit event, and terminates the session.
