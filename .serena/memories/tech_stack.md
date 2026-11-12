# Tech Stack

## Core Languages & Frameworks

- **Python 3.12+** (pyproject.toml `requires-python`)
- **Flask** 3.0+ (application factory + Blueprints)
- **SQLAlchemy** 2.0+ (ORM)
- **SQLite** — WAL mode, foreign keys enabled, busy timeout
  - Central `catalog.sqlite` + `project.sqlite` per project
- **Vue 3** (runtime-only ESM build, `h()` render functions only, no SFC)
- **Tailwind CSS** (compiled via standalone CLI to static CSS)

## Key Dependencies

| Package | Version | Role |
|---------|---------|------|
| flask | ≥3.0.0 | Web framework |
| waitress | ≥2.1.0 | WSGI server (127.0.0.1:5080) |
| sqlalchemy | ≥2.0.0 | ORM |
| flask-alembic | ≥1.0.0 | Catalogue migrations |
| alembic | ≥1.12.0 | Programmatic project migrations |
| cryptography | ≥41.0.0 | AES-256-GCM |
| click | ≥8.1.0 | CLI toolkit |
| flask-jwt-extended | ≥4.5.0 | JWT + cookies |
| flask-cors | ≥4.0.0 | CORS (dev only) |
| ldap3 | ≥2.9.0 | Active Directory (optional) |
| pywin32 | ≥305 | Windows ACLs (Windows only) |

## Dev Dependencies

| Package | Version | Role |
|---------|---------|------|
| pytest | ≥7.4.0 | Test runner |
| pytest-flask | ≥1.2.0 | Flask fixtures |
| pytest-httpx | ≥0.21.0 | HTTP mocking |
| pytest-cov | ≥4.1.0 | Coverage |
| pytest-xdist | ≥3.3.0 | Parallel test runs |
| playwright | ≥1.40.0 | E2E browser automation |
| mypy | ≥1.5.0 | Type checking |
| ruff | ≥0.1.0 | Linting |
| black | ≥23.9.0 | Code formatting |

## Build & Packaging

- **Build backend:** Hatchling (`pyproject.toml` `build-system`)
- **Packaging:** PyInstaller one-folder on Windows (v1); Linux/macOS post-v1
- **Package manager:** pip (no uv, poetry, or conda)

## Frontend Vendor Files

Local, checksum-verified copies in `frontend/vendor/`:
- `vue@3.x` (runtime-only ESM)
- `axios@1.x` (HTTP client)
- `echarts@5.x` (visualizations)

## Naming & Versioning

- **Package:** `litfoundry` (not `brm`, `pybrm`)
- **Version:** `1.0.0` (in `__init__.py`)
- **Python target:** 3.12+ (ruff, mypy configs)