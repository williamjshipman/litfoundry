"""Flask application factory."""

from flask import Flask
from flask_alembic import Alembic

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

    # Initialize Flask-Alembic for migrations
    Alembic(app)

    # Register blueprints
    from litfoundry.api import admin, health

    app.register_blueprint(health.bp)
    app.register_blueprint(admin.bp)

    # Register request hooks
    from litfoundry.middleware import before_request_handler

    app.before_request(before_request_handler)

    return app
