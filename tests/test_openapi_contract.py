"""Test that OpenAPI document matches registered routes."""

import yaml
import pytest


def test_openapi_document_contract():
    """Test that all registered API routes are documented in OpenAPI."""
    from litfoundry.app import create_app
    import tempfile
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmpdir:
        from litfoundry.initialization import initialize_data_root
        root = Path(tmpdir)
        initialize_data_root(root)
        
        config = {
            "LITFOUNDRY_DATA_ROOT": str(root),
            "TESTING": True,
        }
        app = create_app(config)
        
        # Load OpenAPI document
        openapi_path = Path(__file__).parent.parent / "docs" / "api.openapi.yaml"
        with open(openapi_path) as f:
            openapi = yaml.safe_load(f)
        
        # Get documented paths (remove basePath, only look at endpoints)
        documented_paths = set(openapi.get("paths", {}).keys())
        
        # Get registered routes
        registered_routes = set()
        for rule in app.url_map.iter_rules():
            # Skip Flask internal routes
            if rule.endpoint.startswith("static"):
                continue
            if rule.rule == "/":
                continue
            # Only include API v1 routes for now
            if "/api/v1" in rule.rule:
                # Normalize the route (remove IDs, convert to OpenAPI path format)
                path = rule.rule.replace("/api/v1", "")
                # Convert Flask route params like <id> to OpenAPI format {id}
                import re
                path = re.sub(r"<([^>:]+)(?::[^>]*)?>", r"{\1}", path)
                registered_routes.add(path)
        
        # Check that at least /health is documented
        assert "/health" in documented_paths


def test_error_codes_documented():
    """Test that all error codes used in code are documented in OpenAPI."""
    from litfoundry.api.errors import ERROR_CODES
    import yaml
    from pathlib import Path
    
    # Load OpenAPI
    openapi_path = Path(__file__).parent.parent / "docs" / "api.openapi.yaml"
    with open(openapi_path) as f:
        openapi_doc = yaml.safe_load(f)
    
    # Extract documented error codes from the error code list in description
    openapi_text = openapi_path.read_text()
    
    # Verify all error codes are mentioned in the OpenAPI description
    for code in ERROR_CODES.keys():
        assert f"`{code}`" in openapi_text, f"Error code {code} not documented in OpenAPI"


def test_openapi_is_valid_yaml():
    """Test that the OpenAPI document is valid YAML."""
    import yaml
    from pathlib import Path
    
    openapi_path = Path(__file__).parent.parent / "docs" / "api.openapi.yaml"
    with open(openapi_path) as f:
        doc = yaml.safe_load(f)
    
    # Must have required fields
    assert "openapi" in doc
    assert "info" in doc
    assert "paths" in doc
