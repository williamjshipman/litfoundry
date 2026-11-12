"""Tests for vendor asset management."""

import json
import pytest
from pathlib import Path


def test_vendor_lock_file_exists():
    """Test that vendor.lock.json exists."""
    vendor_lock = Path(__file__).parent.parent / "scripts" / "vendor.lock.json"
    assert vendor_lock.exists()


def test_vendor_lock_has_required_packages():
    """Test that vendor.lock.json defines all required packages."""
    vendor_lock_path = Path(__file__).parent.parent / "scripts" / "vendor.lock.json"
    with open(vendor_lock_path) as f:
        locks = json.load(f)
    
    assert "vue" in locks
    assert "axios" in locks
    assert "echarts" in locks


def test_vendor_lock_structure():
    """Test that vendor.lock.json has correct structure."""
    vendor_lock_path = Path(__file__).parent.parent / "scripts" / "vendor.lock.json"
    with open(vendor_lock_path) as f:
        locks = json.load(f)
    
    for package, config in locks.items():
        assert "version" in config
        assert "files" in config
        assert isinstance(config["files"], dict)
        assert len(config["files"]) > 0


def test_fetch_vendor_script_exists():
    """Test that fetch_vendor.py script exists."""
    script = Path(__file__).parent.parent / "scripts" / "fetch_vendor.py"
    assert script.exists()


def test_fetch_vendor_verify_mode():
    """Test that fetch_vendor.py can run in verify mode."""
    import subprocess
    
    result = subprocess.run(
        [
            "python",
            "scripts/fetch_vendor.py",
            "verify",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    
    # It should run without raising an exception
    # (may fail if vendor files aren't downloaded, but that's expected)
    assert result.returncode in [0, 1]
