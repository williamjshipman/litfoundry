# Task Completion Checklist

## Before marking a task done:

### 1. Tests Pass (All)

```powershell
# Full suite with coverage
pytest --cov=litfoundry --cov-report=term-missing

# Exit code 0 = all pass
# Check coverage for new code (aim >80% for new modules)
```

### 2. Linting & Type Checks Pass

```powershell
# Ruff lint (no errors/warnings)
ruff check src\ tests\

# Type checking
mypy src\litfoundry\

# Code format
black --check src\ tests\  # or auto-fix: black src\ tests\
```

### 3. Code Review Points

- ✅ No unrelated refactors (only fixes coupled to this task)
- ✅ Docstrings on public functions/classes (Google-style)
- ✅ Type hints on function signatures
- ✅ Secrets/credentials NOT logged or committed
- ✅ Permission checks on every new API endpoint
- ✅ Audit logging for sensitive operations
- ✅ Database migrations created (if schema changed)
- ✅ Frontend: no SFC, render functions only, no template compiler

### 4. Documentation Updated

- ✅ OpenSpec change `design.md` or `tasks.md` reflects decisions
- ✅ Docstrings/comments for non-obvious logic
- ✅ README/CONTRIBUTING updated if user-facing behavior changed
- ✅ Migration notes if breaking changes to DB schema or API

### 5. Commit Message

```
Brief imperative summary (50 chars max)

Longer explanation if needed (wrap at 72).
- Relates to OpenSpec change: m<N>-<name>
- Lists any breaking changes or migration steps
- References issue/PR if applicable

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```

## By Task Category

### Database/Migration Tasks

1. ✅ Alembic revision created (`flask db revision -m "..."`)
2. ✅ Migration file tested with `pytest`
3. ✅ Schema constraints verified (FK, unique, not null)
4. ✅ Backwards compatibility noted (or breaking change justified in design.md)

### API Endpoint Tasks

1. ✅ Route defined under `/api/v1/*`
2. ✅ Permission check at function start (raise `Forbidden` if denied)
3. ✅ Consistent JSON error envelope (m1-web-foundation spec)
4. ✅ Pytest tests (authorized + unauthorized paths)
5. ✅ Playwright E2E test for user flow (if user-facing)
6. ✅ Audit log entry for sensitive operations

### Frontend Component Tasks

1. ✅ Render function only (no `<template>`, no SFC)
2. ✅ Vue 3 runtime-only ESM (`h()`, no template compiler)
3. ✅ Tailwind classes applied correctly
4. ✅ No CSP violations (no inline scripts, `eval`, unsafe styles)
5. ✅ Playwright E2E test for user interaction

### Configuration/Initialization Tasks

1. ✅ Env vars follow `LITFOUNDRY_*` prefix
2. ✅ Defaults sensible (Windows/Linux/macOS paths)
3. ✅ Validation tests cover invalid inputs
4. ✅ Documented in `.env.example` or code comments

## Final Verification

```powershell
# Run the full check sequence
$env:LITFOUNDRY_MODE = "server"  # or "workstation"
pytest --cov=litfoundry
ruff check src\ tests\
mypy src\litfoundry\
black --check src\ tests\

# If all green, task is complete
echo "✅ Task complete"
```

Exit code 0 from all commands = task ready for review.