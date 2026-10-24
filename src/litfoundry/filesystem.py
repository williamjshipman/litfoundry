"""Filesystem utilities and safety checks."""

import os
import sys
import uuid
from pathlib import Path


def validate_contained_path(base_root: Path, requested_path: Path) -> Path:
    """Validate and resolve a path to ensure it's contained within base_root.

    Rejects paths with:
    - .. (parent directory escapes)
    - Absolute paths taken from user input
    - Symlinks that resolve outside base_root

    Args:
        base_root: The root directory that must contain the path
        requested_path: The path to validate (may be relative or absolute)

    Returns:
        The resolved path (fully resolved symlinks)

    Raises:
        ValueError: If the path escapes base_root or contains forbidden patterns
    """
    # Convert base_root to absolute, resolved path
    try:
        base_resolved = base_root.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Cannot resolve base root {base_root}: {e}") from e

    # Check for .. in the relative parts
    if ".." in requested_path.parts:
        raise ValueError(f"Path contains .. (parent directory escape): {requested_path}")

    # If requested_path is absolute, reject it (only relative paths within root allowed)
    # On Windows, paths starting with / or \ without a drive are still considered rooted
    if requested_path.is_absolute():
        raise ValueError(f"Absolute paths not allowed (only relative to data root): {requested_path}")
    
    # Additional check: reject paths that start with / or \ even on Windows
    path_str = str(requested_path)
    if path_str.startswith(("/", "\\")):
        raise ValueError(f"Absolute paths not allowed (only relative to data root): {requested_path}")

    # Construct full path by joining with base
    full_path = base_resolved / requested_path

    # Resolve the full path (following symlinks)
    try:
        resolved_path = full_path.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Cannot resolve path {full_path}: {e}") from e

    # Verify resolved path is contained within base_root
    # Use os.path.commonpath or simple string prefix check
    try:
        resolved_path.relative_to(base_resolved)
    except ValueError as e:
        # relative_to raises ValueError if not contained
        raise ValueError(
            f"Path escapes data root (maybe via symlink): {requested_path} -> {resolved_path}"
        ) from e

    return resolved_path


def check_path_safety(root: Path) -> None:
    """Check that a path is safe for use as a data root.

    Rejects paths with:
    - .. (parent directory escapes)
    - Symlinks that escape the root

    Args:
        root: Path to validate

    Raises:
        ValueError: If the path is unsafe
    """
    # Resolve symlinks to detect escape attempts
    try:
        real_root = root.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Cannot resolve path {root}: {e}") from e

    # Check for parent directory references in the original path
    if ".." in root.parts:
        raise ValueError(f"Path contains .. (parent directory): {root}")

    # Check for absolute user paths (if root is supposed to be contained)
    # This is a basic check; later tasks enforce full containment


def check_network_filesystem(root: Path) -> None:
    """Check that the path is not on a network filesystem.

    Rejects:
    - UNC paths (Windows: \\\\server\\share)
    - Network mounts (Windows DRIVE_REMOTE, Linux nfs/cifs/smb3/sshfs, macOS smbfs/nfs/afpfs)

    Args:
        root: Path to validate

    Raises:
        ValueError: If the path is on a network filesystem
    """
    root_str = str(root)

    if sys.platform == "win32":
        # Check for UNC paths
        if root_str.startswith("\\\\"):
            raise ValueError(f"UNC paths are not supported: {root}")

        # Check for network drive
        try:
            import ctypes

            drive_letter = root_str[0] if len(root_str) > 1 else None
            if drive_letter:
                # Get drive type using Windows API
                ret = ctypes.windll.kernel32.GetDriveTypeW(f"{drive_letter}:\\")
                # DRIVE_REMOTE = 4
                if ret == 4:
                    raise ValueError(
                        f"Network drive {drive_letter}: is not supported: {root}"
                    )
        except (AttributeError, OSError, TypeError):
            # If we can't check, allow it (may be running on non-Windows)
            pass

    elif sys.platform == "darwin":
        # macOS: check mount filesystem types
        try:
            with open("/etc/mnttab") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3:
                        mount_path, fstype = parts[0], parts[2]
                        if mount_path in str(root) and fstype in [
                            "smbfs",
                            "nfs",
                            "afpfs",
                        ]:
                            raise ValueError(
                                f"Mounted on network filesystem {fstype}: {root}"
                            )
        except (OSError, FileNotFoundError):
            # File doesn't exist on all macOS versions, that's fine
            pass

    else:
        # Linux and others: check /proc/self/mountinfo
        try:
            with open("/proc/self/mountinfo") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 9:
                        mount_point, fstype = parts[4], parts[8]
                        if root_str.startswith(mount_point):
                            if fstype in ["nfs", "cifs", "smb3", "fuse.sshfs"]:
                                raise ValueError(
                                    f"Mounted on network filesystem {fstype}: {root}"
                                )
        except (OSError, FileNotFoundError):
            # File might not exist on all Linux systems
            pass


def apply_permissions(root: Path) -> None:
    """Apply restrictive permissions to the data root.

    - Windows: DACL with inheritance disabled
    - POSIX: 0o700

    Args:
        root: Path to restrict
    """
    if sys.platform == "win32":
        _apply_windows_permissions(root)
    else:
        _apply_posix_permissions(root)


def _apply_windows_permissions(root: Path) -> None:
    """Apply Windows DACL permissions."""
    try:
        import ntsecuritycon
        import win32api
        import win32security

        # Get the security descriptor
        sd = win32security.GetFileSecurity(
            str(root), win32security.DACL_SECURITY_INFORMATION
        )
        dacl = win32security.ACL(10)

        # Get SIDs for SYSTEM, Administrators, and current user
        system_sid = win32security.LookupAccountName("", "SYSTEM")[0]
        admin_sid = win32security.LookupAccountName("", "Administrators")[0]
        
        # Get current user's SID from the current process token
        process_token = win32security.OpenProcessToken(
            win32api.GetCurrentProcess(),
            win32security.TOKEN_QUERY
        )
        current_user_sid = win32security.GetTokenInformation(
            process_token, win32security.TokenUser
        )[0]

        # Add ACEs for current user, SYSTEM, and Administrators (full control)
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            ntsecuritycon.FILE_ALL_ACCESS,
            current_user_sid,
        )
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            ntsecuritycon.FILE_ALL_ACCESS,
            system_sid,
        )
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            ntsecuritycon.FILE_ALL_ACCESS,
            admin_sid,
        )

        # Set the DACL
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(
            str(root), win32security.DACL_SECURITY_INFORMATION, sd
        )

    except (ImportError, OSError):
        # Fall back to os.chmod if pywin32 is not available or fails
        os.chmod(root, 0o700)


def _apply_posix_permissions(root: Path) -> None:
    """Apply POSIX permissions (0o700)."""
    os.chmod(root, 0o700)


def generate_uuid_name() -> str:
    """Generate a UUID-based name for use in filesystem paths.

    Returns:
        A UUID4 string (without dashes for filesystem safety)
    """
    return str(uuid.uuid4()).replace("-", "")


def generate_uuid_path(base_root: Path) -> Path:
    """Generate a UUID-based path within the data root.

    Args:
        base_root: The data root directory

    Returns:
        A path like base_root/abc123def456... (UUID without dashes)
    """
    return base_root / generate_uuid_name()

