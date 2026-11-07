"""Flask application factory."""

from flask import Flask
from flask_alembic import Alembic
from flask_jwt_extended import JWTManager

from litfoundry import __description__, __tagline__, __title__, __version__


def create_app(config: dict | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Set metadata
    app.config["LITFOUNDRY_VERSION"] = __version__
    app.config["LITFOUNDRY_TITLE"] = __title__
    app.config["LITFOUNDRY_TAGLINE"] = __tagline__
    app.config["LITFOUNDRY_DESCRIPTION"] = __description__

    # Apply custom configuration
    if config:
        app.config.update(config)

    # Set request size limits (default 16MB for JSON, 512MB for uploads)
    app.config.setdefault("MAX_CONTENT_LENGTH", 512 * 1024 * 1024)  # 512MB for uploads
    app.config.setdefault("JSON_PAYLOAD_MAX_SIZE", 16 * 1024 * 1024)  # 16MB for JSON

    # Configure database session factory if DATA_ROOT is provided
    from pathlib import Path
    from litfoundry.catalog import create_catalog_engine, Base
    from sqlalchemy.orm import sessionmaker, scoped_session
    
    if "DATA_ROOT" in app.config or "LITFOUNDRY_DATA_ROOT" in app.config:
        data_root = app.config.get("DATA_ROOT") or app.config.get("LITFOUNDRY_DATA_ROOT")
        if isinstance(data_root, str):
            data_root = Path(data_root)
        
        catalog_path = Path(data_root) / "catalog.sqlite"
        engine = create_catalog_engine(catalog_path)
        Base.metadata.create_all(engine)  # Ensure tables exist
        
        Session = sessionmaker(bind=engine)
        app.config["DB_SESSION_FACTORY"] = scoped_session(Session)
        app.config["DATA_ROOT"] = Path(data_root)

    # Configure JWT
    app.config.setdefault("JWT_SECRET_KEY", app.config.get("SECRET_KEY", "dev-key-change-in-production"))
    app.config.setdefault("JWT_TOKEN_LOCATION", ["cookies"])
    app.config.setdefault("JWT_COOKIE_SECURE", True)  # HTTPS only
    app.config.setdefault("JWT_COOKIE_CSRF_PROTECT", True)
    app.config.setdefault("JWT_COOKIE_SAMESITE", "Lax")
    app.config.setdefault("JWT_COOKIE_HTTPONLY", True)
    app.config.setdefault("JWT_ALGORITHM", "HS256")
    app.config.setdefault("JWT_ACCESS_TOKEN_EXPIRES", 15 * 60)  # 15 minutes
    
    # In testing mode, allow insecure cookies
    if app.config.get("TESTING"):
        app.config["JWT_COOKIE_SECURE"] = False

    # Initialize JWT
    JWTManager(app)

    # Use custom JSON encoder for UUID and datetime serialization
    from litfoundry.api.serialization import LitFoundryJSONEncoder
    
    app.json_encoder_class = LitFoundryJSONEncoder

    # Initialize Flask-Alembic for migrations
    Alembic(app)

    # Setup error handlers (must be before middleware and blueprints)
    from litfoundry.api.errors import setup_error_handlers
    
    setup_error_handlers(app)

    # Setup security middleware (before blueprints)
    from litfoundry.api.security import setup_security_middleware
    
    setup_security_middleware(app)

    # Register blueprints
    from litfoundry.api import admin, health, auth, ad_directory

    app.register_blueprint(health.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(ad_directory.bp)
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(auth.setup_bp)

    # Setup middleware (proxy handling, host allowlist, and CORS)
    from litfoundry.middleware import setup_middleware
    
    # Parse trusted proxies and allowed hosts from config
    trusted_proxies = app.config.get("LITFOUNDRY_TRUSTED_PROXIES", "")
    if isinstance(trusted_proxies, str):
        trusted_proxies = [ip.strip() for ip in trusted_proxies.split(",") if ip.strip()]
    
    allowed_hosts = app.config.get("LITFOUNDRY_ALLOWED_HOSTS", "")
    if isinstance(allowed_hosts, str):
        allowed_hosts = [host.strip() for host in allowed_hosts.split(",") if host.strip()]
    
    # Parse CORS origins from config
    cors_origins = app.config.get("LITFOUNDRY_CORS_ORIGINS", "")
    if isinstance(cors_origins, str):
        cors_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
    
    setup_middleware(
        app,
        trusted_proxies=trusted_proxies or None,
        host_allowlist=allowed_hosts or None,
        cors_origins=cors_origins or None,
    )

    return app

