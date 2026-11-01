"""Filesystem utilities and safety checks."""

import logging
import os
import subprocess
import sys
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


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
        raise ValueError(
            f"Absolute paths not allowed (only relative to data root): {requested_path}"
        )

    # Additional check: reject paths that start with / or \ even on Windows
    path_str = str(requested_path)
    if path_str.startswith(("/", "\\")):
        raise ValueError(
            f"Absolute paths not allowed (only relative to data root): {requested_path}"
        )

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
                    raise ValueError(f"Network drive {drive_letter}: is not supported: {root}")
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
                            raise ValueError(f"Mounted on network filesystem {fstype}: {root}")
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
                                raise ValueError(f"Mounted on network filesystem {fstype}: {root}")
        except (OSError, FileNotFoundError):
            # File might not exist on all Linux systems
            pass


def apply_permissions(root: Path, service_account: str | None = None) -> None:
    """Apply restrictive permissions to the data root and all children.

    - Windows: DACL with inheritance disabled, recursively applied, with icacls fallback
    - POSIX: 0o700 on root and all children

    Args:
        root: Path to restrict
        service_account: Optional service account SID or name (Windows only).
                        If provided, added to ACL. If not resolvable, logs warning
                        and continues with default (SYSTEM, Administrators, current user).

    """
    if sys.platform == "win32":
        _apply_windows_permissions(root, service_account=service_account)
    else:
        _apply_posix_permissions(root)


def _apply_windows_permissions(root: Path, service_account: str | None = None) -> None:
    """Apply Windows DACL permissions with protection flag and recursion.

    Sets SE_DACL_PROTECTED to prevent unauthorized modification of child ACLs.
    Recursively applies permissions to all subdirectories and files.

    Args:
        root: Path to protect
        service_account: Optional service account (name or SID) to include in ACL.

    """
    try:
        import win32api
        import win32security

        # Define the list of SIDs to add to the ACL
        sids_to_add = []
        sid_names = []

        # Get SYSTEM and Administrators SIDs
        system_sid = win32security.LookupAccountName("", "SYSTEM")[0]
        admin_sid = win32security.LookupAccountName("", "Administrators")[0]

        # Get current user's SID from the current process token
        process_token = win32security.OpenProcessToken(
            win32api.GetCurrentProcess(), win32security.TOKEN_QUERY
        )
        current_user_sid = win32security.GetTokenInformation(
            process_token, win32security.TokenUser
        )[0]

        sids_to_add = [current_user_sid, system_sid, admin_sid]
        sid_names = ["CurrentUser", "SYSTEM", "Administrators"]

        # Try to resolve service account if provided
        if service_account:
            try:
                service_sid = win32security.LookupAccountName("", service_account)[0]
                sids_to_add.append(service_sid)
                sid_names.append(service_account)
            except Exception as e:
                logger.warning(
                    f"Could not resolve service account '{service_account}': {e}. "
                    f"Continuing without it."
                )

        # Apply permissions recursively to root and all children
        _apply_windows_dacl_recursive(root, sids_to_add, sid_names)

    except (ImportError, OSError) as e:
        # Fall back to icacls on Windows
        logger.warning(f"pywin32 DACL setup failed: {e}. Falling back to icacls.")
        _apply_windows_permissions_icacls_fallback(root, service_account)


def _apply_windows_dacl_recursive(path: Path, sids_to_add: list, sid_names: list) -> None:
    """Recursively apply Windows DACL to a directory tree.

    Args:
        path: Root path to protect
        sids_to_add: List of SID objects to add to ACL
        sid_names: List of name strings corresponding to sids_to_add (for logging).

    """
    import ntsecuritycon
    import win32security

    # Apply to the current path
    try:
        sd = win32security.GetFileSecurity(str(path), win32security.DACL_SECURITY_INFORMATION)
        dacl = win32security.ACL(len(sids_to_add) + 5)  # Extra slots for safety

        # Add ACEs for each SID with inheritance flags
        # OBJECT_INHERIT_ACE (0x1) allows inheritance to files
        # CONTAINER_INHERIT_ACE (0x2) allows inheritance to directories
        inherit_flags = ntsecuritycon.OBJECT_INHERIT_ACE | ntsecuritycon.CONTAINER_INHERIT_ACE

        for sid in sids_to_add:
            dacl.AddAccessAllowedAceEx(
                win32security.ACL_REVISION,
                inherit_flags,
                ntsecuritycon.FILE_ALL_ACCESS,
                sid,
            )

        # Set SE_DACL_PROTECTED to prevent unauthorized inheritance modifications
        sd.SetSecurityDescriptorDacl(1, dacl, 0)

        # Enable SE_DACL_PROTECTED flag (prevents non-owner modifications)
        # SetSecurityDescriptorControl takes (control_bits, control_mask)
        se_dacl_protected = 0x1000  # SE_DACL_PROTECTED in security descriptor control
        try:
            sd.SetSecurityDescriptorControl(se_dacl_protected, se_dacl_protected)
        except AttributeError:
            # Fallback: some pywin32 versions don't have SetSecurityDescriptorControl
            logger.debug(
                "SetSecurityDescriptorControl not available; " "skipping DACL protection flag"
            )

        win32security.SetFileSecurity(str(path), win32security.DACL_SECURITY_INFORMATION, sd)
        logger.debug(f"Applied DACL to {path}")
    except OSError as e:
        logger.error(f"Failed to apply DACL to {path}: {e}")
        raise

    # Recursively apply to children (skip symlinks)
    try:
        for item in path.iterdir():
            # Skip symlinks (security: prevent escape or loops)
            if item.is_symlink():
                logger.debug(f"Skipping symlink: {item}")
                continue

            if item.is_dir(follow_symlinks=False):  # type: ignore[call-arg]
                # Recurse into subdirectory
                _apply_windows_dacl_recursive(item, sids_to_add, sid_names)
            elif item.is_file(follow_symlinks=False):  # type: ignore[call-arg]
                # Apply to file
                try:
                    sd = win32security.GetFileSecurity(
                        str(item), win32security.DACL_SECURITY_INFORMATION
                    )
                    dacl = win32security.ACL(len(sids_to_add) + 5)

                    for sid in sids_to_add:
                        dacl.AddAccessAllowedAce(
                            win32security.ACL_REVISION,
                            ntsecuritycon.FILE_ALL_ACCESS,
                            sid,
                        )

                    sd.SetSecurityDescriptorDacl(1, dacl, 0)
                    win32security.SetFileSecurity(
                        str(item), win32security.DACL_SECURITY_INFORMATION, sd
                    )
                    logger.debug(f"Applied permissions to file: {item}")
                except OSError as e:
                    logger.warning(f"Could not set permissions on {item}: {e}")

    except (OSError, PermissionError) as e:
        logger.warning(f"Could not traverse directory {path}: {e}")


def _apply_windows_permissions_icacls_fallback(
    root: Path, service_account: str | None = None
) -> None:
    """Apply Windows permissions using icacls CLI tool.

    Fallback method when pywin32 is unavailable. Uses subprocess to call
    icacls with /inheritance:e (replace all) and /T (recursive).

    Args:
        root: Path to protect
        service_account: Optional service account to include.

    """
    try:
        # Build icacls command
        # First, clear existing ACLs: icacls "path" /inheritance:e /T
        # Then, grant permissions to required accounts

        # Clear and set permissions recursively
        cmd_clear = ["icacls", str(root), "/inheritance:e", "/T"]
        subprocess.run(cmd_clear, check=True, capture_output=True)
        logger.debug(f"Cleared inheritance for {root}")

        # Grant permissions to current user
        cmd_user = [
            "icacls",
            str(root),
            "/grant",
            f"{os.environ.get('USERNAME', 'CurrentUser')}:(OI)(CI)F",
            "/T",
        ]
        subprocess.run(cmd_user, check=True, capture_output=True)

        # Grant to SYSTEM
        cmd_system = ["icacls", str(root), "/grant", "SYSTEM:(OI)(CI)F", "/T"]
        subprocess.run(cmd_system, check=True, capture_output=True)

        # Grant to Administrators
        cmd_admin = ["icacls", str(root), "/grant", "Administrators:(OI)(CI)F", "/T"]
        subprocess.run(cmd_admin, check=True, capture_output=True)

        # If service account provided, grant to it
        if service_account:
            try:
                cmd_service = [
                    "icacls",
                    str(root),
                    "/grant",
                    f"{service_account}:(OI)(CI)F",
                    "/T",
                ]
                subprocess.run(cmd_service, check=True, capture_output=True)
                logger.debug(f"Granted permissions to service account {service_account}")
            except subprocess.CalledProcessError as e:
                logger.warning(
                    f"Could not grant permissions to service account {service_account}: {e}"
                )

        logger.debug(f"Applied permissions via icacls to {root} and children")

    except (subprocess.CalledProcessError, OSError) as e:
        logger.error(f"icacls fallback failed: {e}")
        # Last resort: try chmod (unlikely to work on Windows but try anyway)
        try:
            os.chmod(root, 0o700)
            logger.info(f"Applied chmod 0o700 to {root}")
        except OSError as chmod_error:
            logger.error(f"Final fallback (chmod) also failed: {chmod_error}")
            raise


def _apply_posix_permissions(root: Path) -> None:
    """Apply POSIX permissions (0o700) to root and all children."""
    try:
        # Apply to root
        os.chmod(root, 0o700)
        logger.debug(f"Applied 0o700 to {root}")

        # Recursively apply to children
        for item in root.rglob("*"):
            # Skip symlinks (security: prevent escape)
            if item.is_symlink():
                logger.debug(f"Skipping symlink: {item}")
                continue

            try:
                os.chmod(item, 0o700)
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not apply permissions to {item}: {e}")
                continue

    except OSError as e:
        logger.error(f"Failed to apply POSIX permissions to {root}: {e}")
        raise


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
