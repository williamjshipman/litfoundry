# Suggested Commands

## Setup & Environment

```powershell
# Create virtual environment (Windows PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Or on bash (Git Bash / WSL)
python -m venv venv
source venv/bin/activate

# Install package in editable mode with dev deps
pip install -e ".[dev]"
```

## Running the Application

```powershell
# Start the server (default: 127.0.0.1:5080)
litfoundry serve --mode server

# Or specify data root
litfoundry serve --data-root C:\path\to\data --mode server

# Check status
litfoundry status

# Initialize data root
litfoundry init
```

## Testing

```powershell
# Full pytest suite (all Python tests)
pytest

# Single test file
pytest tests\test_auth.py

# Single test function
pytest tests\test_auth.py::test_login

# With coverage report
pytest --cov=litfoundry --cov-report=html

# Parallel execution
pytest -n auto

# E2E tests only (Playwright)
pytest tests\e2e\ -v

# Specific marker
pytest -m unit
pytest -m integration
pytest -m e2e
pytest -m slow
```

## Linting, Formatting, Type Checking

```powershell
# Lint with ruff (check only)
ruff check src\ tests\

# Lint with auto-fix
ruff check --fix src\ tests\

# Format with black
black src\ tests\

# Type checking
mypy src\litfoundry\

# All checks together
ruff check src\ tests\ && black src\ tests\ && mypy src\litfoundry\
```

## Database Migrations

```powershell
# Catalogue migrations (Flask-Alembic)
flask db upgrade

# Create new migration
flask db revision -m "description"

# Project migrations are handled programmatically during lifecycle operations
```

## Git & Repository

```powershell
# View git status (non-pager)
git --no-pager status

# View log (non-pager, limited)
git --no-pager log --oneline -10

# Fetch without checkout
git fetch

# Create branch
git checkout -b feature-name

# Stage and commit
git add .
git commit -m "message"
```

## Development Helpers

```powershell
# Clean pycache and build artifacts
rm -r .pytest_cache, .mypy_cache, .ruff_cache, build, dist, *.egg-info

# Activate Serena memory check (project root)
serena memories check
```

## Windows-Specific Notes

- Use `.\venv\Scripts\Activate.ps1` for PowerShell; `.venv\Scripts\activate.bat` for cmd.exe
- Paths use backslashes (`\`); forward slashes in globs work but inconsistent
- PyInstaller output goes to `dist\litfoundry\` (onedir mode)