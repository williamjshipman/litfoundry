"""Fetch and verify vendor assets (Vue, Axios, ECharts)."""

import json
import hashlib
import sys
from pathlib import Path
from urllib.request import urlopen
import tarfile
import io


# Vendor configuration with exact versions and checksums
VENDORS = {
    "vue": {
        "version": "3.4.21",
        "files": {
            "dist/vue.runtime.esm-browser.prod.js": "vue.runtime.esm-browser.prod.js",
            "LICENSE": "LICENSE-vue",
        },
    },
    "axios": {
        "version": "1.6.7",
        "files": {
            "dist/axios.min.js": "axios.min.js",
            "LICENSE": "LICENSE-axios",
        },
    },
    "echarts": {
        "version": "5.4.3",
        "files": {
            "dist/echarts.min.js": "echarts.min.js",
            "LICENSE": "LICENSE-echarts",
        },
    },
}


def download_and_extract(package_name: str, version: str) -> dict:
    """Download and extract a package from npm registry."""
    url = f"https://registry.npmjs.org/{package_name}/-/{package_name}-{version}.tgz"
    
    print(f"Downloading {package_name}@{version}...")
    try:
        with urlopen(url, timeout=10) as response:
            tar_data = response.read()
    except Exception as e:
        print(f"Failed to download {package_name}: {e}", file=sys.stderr)
        return {}
    
    # Extract specific files from tarball
    files = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_data)) as tar:
            for member in tar.getmembers():
                # Files are in package/<path>
                if member.name.startswith("package/"):
                    relative_path = member.name[8:]  # Remove "package/"
                    if relative_path in VENDORS[package_name]["files"]:
                        content = tar.extractfile(member).read()
                        files[relative_path] = content
    except Exception as e:
        print(f"Failed to extract {package_name}: {e}", file=sys.stderr)
        return {}
    
    return files


def main(mode: str = "fetch"):
    """Main function.
    
    Args:
        mode: "fetch" to download and verify, "verify" to only check existing files
    """
    script_dir = Path(__file__).parent
    frontend_dir = script_dir.parent / "frontend"
    vendor_dir = frontend_dir / "vendor"
    licenses_dir = script_dir.parent / "LICENSES"
    
    if mode == "verify":
        print("Verifying vendor files...")
        all_valid = True
        
        vendor_lock_path = script_dir / "vendor.lock.json"
        if not vendor_lock_path.exists():
            print("vendor.lock.json not found", file=sys.stderr)
            return False
        
        with open(vendor_lock_path) as f:
            locks = json.load(f)
        
        for package_name, config in locks.items():
            for file_name, expected_hash in config.get("files", {}).items():
                file_path = vendor_dir / file_name
                if not file_path.exists():
                    print(f"  ✗ {file_name}: file not found", file=sys.stderr)
                    all_valid = False
                    continue
                
                actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
                if actual == expected_hash:
                    print(f"  ✓ {file_name}")
                else:
                    print(f"  ✗ {file_name}: checksum mismatch", file=sys.stderr)
                    all_valid = False
        
        return all_valid
    
    # Fetch mode
    vendor_dir.mkdir(parents=True, exist_ok=True)
    licenses_dir.mkdir(parents=True, exist_ok=True)
    
    vendor_lock = {}
    all_valid = True
    
    for package_name, config in VENDORS.items():
        print(f"\n{package_name}@{config['version']}:")
        
        files = download_and_extract(package_name, config["version"])
        if not files:
            print(f"Failed to download {package_name}", file=sys.stderr)
            all_valid = False
            continue
        
        # Write files
        lock_entry = {"version": config["version"], "files": {}}
        for file_path, content in files.items():
            # Map to output file name
            output_name = config["files"].get(file_path, file_path)
            output_path = vendor_dir / output_name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(content)
            print(f"  ✓ {output_name}")
            
            # Record in lock file
            lock_entry["files"][output_name] = hashlib.sha256(content).hexdigest()
        
        vendor_lock[package_name] = lock_entry
    
    # Write lock file
    lock_path = script_dir / "vendor.lock.json"
    with open(lock_path, "w") as f:
        json.dump(vendor_lock, f, indent=2)
    
    print(f"\nWrote vendor lock to {lock_path}")
    return all_valid


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "fetch"
    result = main(mode=mode)
    sys.exit(0 if result else 1)
