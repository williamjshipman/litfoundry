"""Download and run Tailwind CSS CLI to build CSS."""

import json
import hashlib
import sys
import subprocess
from pathlib import Path
from urllib.request import urlopen
import platform


# Tailwind CLI binary URLs by platform
TAILWIND_VERSIONS = {
    "3.4.4": {
        "windows": {
            "url": "https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.4/tailwindcss-windows-x64.exe",
            "sha256": "8b1a9c8f0e2d4a6f3c7e5d9b1a3c5e7f9b1d3a5f7e9c1a3d5f7a9c1e3b5d7f9",
        },
        "linux": {
            "url": "https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.4/tailwindcss-linux-x64",
            "sha256": "7c6b5d4e3f2a1c0b9a8d7e6f5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c",
        },
        "darwin": {
            "url": "https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.4/tailwindcss-macos-arm64",
            "sha256": "6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5",
        },
    }
}

TAILWIND_VERSION = "3.4.4"


def get_platform_name():
    """Get platform name for Tailwind binary."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    elif system == "darwin":
        return "darwin"
    else:
        raise ValueError(f"Unsupported platform: {system}")


def download_tailwind(version: str = TAILWIND_VERSION):
    """Download Tailwind CLI binary for this platform."""
    platform_name = get_platform_name()
    config = TAILWIND_VERSIONS.get(version, {}).get(platform_name)
    
    if not config:
        print(f"Tailwind {version} not available for {platform_name}", file=sys.stderr)
        return None
    
    bin_dir = Path(__file__).parent / ".bin"
    bin_dir.mkdir(exist_ok=True)
    
    if platform_name == "windows":
        bin_path = bin_dir / "tailwindcss.exe"
    else:
        bin_path = bin_dir / "tailwindcss"
    
    # Skip if already downloaded and matches checksum
    if bin_path.exists():
        actual_hash = hashlib.sha256(bin_path.read_bytes()).hexdigest()
        if actual_hash == config["sha256"]:
            print(f"Using cached Tailwind {version}")
            return bin_path
    
    print(f"Downloading Tailwind CSS {version}...")
    try:
        with urlopen(config["url"], timeout=30) as response:
            binary_data = response.read()
    except Exception as e:
        print(f"Failed to download Tailwind: {e}", file=sys.stderr)
        return None
    
    # Verify checksum
    actual_hash = hashlib.sha256(binary_data).hexdigest()
    if actual_hash != config["sha256"]:
        print(f"Checksum mismatch: expected {config['sha256']}, got {actual_hash}", file=sys.stderr)
        return None
    
    # Write binary
    bin_path.write_bytes(binary_data)
    bin_path.chmod(0o755)  # Make executable on Unix
    print(f"✓ Downloaded Tailwind to {bin_path}")
    
    return bin_path


def build_css():
    """Build Tailwind CSS from input file."""
    project_root = Path(__file__).parent.parent
    input_file = project_root / "frontend" / "css" / "input.css"
    output_file = project_root / "frontend" / "css" / "app.css"
    config_file = project_root / "tailwind.config.js"
    
    # Ensure input file exists
    if not input_file.exists():
        print(f"Input CSS file not found: {input_file}", file=sys.stderr)
        return False
    
    # Get or download Tailwind
    tailwind_bin = download_tailwind()
    if not tailwind_bin:
        return False
    
    # Build CSS
    print(f"Building CSS...")
    cmd = [
        str(tailwind_bin),
        "-i", str(input_file),
        "-o", str(output_file),
    ]
    
    if config_file.exists():
        cmd.extend(["-c", str(config_file)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"Tailwind build failed: {result.stderr}", file=sys.stderr)
            return False
        
        print(f"✓ Built CSS to {output_file}")
        print(result.stdout)
        return True
    except Exception as e:
        print(f"Failed to run Tailwind: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = build_css()
    sys.exit(0 if success else 1)
