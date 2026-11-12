# Conventions

## Code Style

- **Line length:** 100 chars (ruff, black)
- **Target:** Python 3.12+
- **Formatting:** Black (non-negotiable)
- **Linting:** Ruff (E, W, F, I, N, D; ignore D100, D104, D105)
- **Import sorting:** isort (ruff integration; known-first-party `litfoundry`)
- **Type hints:** mypy strict_optional mode, disallow_untyped_defs off

## Naming Conventions

- **Package/module:** lowercase, underscores (`litfoundry`, `test_auth.py`)
- **Classes:** PascalCase (e.g., `AdminBlueprintFactory`, `ConfigManager`)
- **Functions/methods:** snake_case (e.g., `create_app`, `get_user_by_id`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `DEFAULT_PORT`, `MAX_RETRIES`)
- **Private/internal:** leading underscore (e.g., `_internal_helper`)
- **Product name:** Exact "LitFoundry" (capitalization)
- **CLI/env prefix:** `litfoundry` / `LITFOUNDRY_`

## Docstring Conventions

- **Format:** Google-style docstrings (ruff D checks)
- **Module docstrings:** Present (except D100/D104 ignored)
- **Functions:** Brief 1-line description + args/returns if complex
- **Classes:** Brief class description; methods same as functions
- **Exceptions:** Document if non-obvious

Example:
```python
def get_user_by_id(user_id: int) -> User | None:
    """Fetch a user by ID.
    
    Args:
        user_id: The numeric user ID.
    
    Returns:
        User object, or None if not found.
    """
    return db.session.get(User, user_id)
```

## Flask Patterns

- **Application factory:** `create_app(config: dict | None = None) -> Flask`
  - Config passed as dict (e.g., from environment or defaults)
  - Blueprints registered inside factory
  - Alembic initialized in factory
- **Blueprints:** One per API area (e.g., `litfoundry/api/admin.py`, `litfoundry/api/health.py`)
  - Routed to `/api/v1/<resource>` versioning
  - Every endpoint checks permissions before business logic
- **Error handling:** Consistent JSON envelope (defined in m1-web-foundation change)
- **Middleware:** ProxyFix, host allowlist, CORS setup in `setup_middleware()`

## Database Patterns

- **ORM:** SQLAlchemy 2.x declarative models
- **Catalogue migrations:** Flask-Alembic in `migrations/catalog/versions/`
- **Project migrations:** Programmatic Alembic API (per project)
- **Queries:** Use `db.session.execute()` with typed statements, not legacy query API
- **WAL + FK:** SQLite must enable WAL and foreign_keys on every connection

## Vue 3 Frontend Patterns

- **No SFC:** Only plain ES modules with render functions (`h()`)
- **Render function syntax:** `h('tag', { props }, [children])`
- **No template compiler:** `script-src 'self'` CSP enforcement
- **No Vite / Node build:** Static HTML entry point, ES6 imports via `<script type="module">`
- **Vendor paths:** `/vendor/vue.esm.js`, etc. (checksummed)
- **Styling:** Tailwind classes applied to `h()` via className prop or object shorthand

Example component:
```javascript
import { h, ref } from '/vendor/vue.esm.js';

export default {
  setup() {
    const count = ref(0);
    return () => h('button', 
      { onClick: () => count.value++ },
      `Clicked ${count.value} times`
    );
  }
};
```

## Testing Conventions

- **Test organization:** `tests/` mirroring `src/` structure
- **Markers:** `@pytest.mark.unit`, `.integration`, `.e2e`, `.slow`
- **Fixtures:** In `litfoundry/test_helpers/` or conftest.py
- **Mocking:** Mock external APIs (OpenAlex, WoS, LDAP)
- **Permission tests:** Every endpoint must have tests verifying unauthorized access is denied
- **Audit logging:** Sensitive ops verified in audit log assertions

## Secrets & Configuration

- **Config source:** Environment variables only (LITFOUNDRY_* prefix)
- **.env:** Loaded only in development (not committed)
- **Secrets:** Never logged or committed; use redaction filter in logging config
- **Encryption key:** 256-bit random from `secret_material/master.key`
- **Key rotation:** Key ID embedded in ciphertext header

## Comments

- Only comment non-obvious logic or intent
- Avoid restating code or obvious implementations
- Use type hints + docstrings instead of inline type comments