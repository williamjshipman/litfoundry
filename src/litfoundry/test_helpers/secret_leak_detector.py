"""Test helper to verify that secrets don't leak in logs, audit, or exports."""

import re
from pathlib import Path
from typing import List, Optional, Set


class SecretLeakDetector:
    """Scans test artifacts for leaked secrets."""

    def __init__(self) -> None:
        """Initialize the detector with empty known secrets."""
        self.known_secrets: Set[str] = set()

    def register_secret(self, secret: str) -> None:
        """Register a test secret to scan for.

        Args:
            secret: The secret value to look for (will be escaped for regex matching)
        """
        self.known_secrets.add(secret)

    def register_secrets(self, secrets: List[str]) -> None:
        """Register multiple test secrets.

        Args:
            secrets: List of secret values to look for
        """
        self.known_secrets.update(secrets)

    def scan_file(self, file_path: Path) -> List[tuple[int, str, str]]:
        """Scan a file for leaked secrets.

        Args:
            file_path: Path to the file to scan

        Returns:
            List of tuples (line_number, line_content, matched_secret)
            Empty list if no leaks found
        """
        if not file_path.exists():
            return []

        leaks = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    for secret in self.known_secrets:
                        if secret in line and secret.strip():  # Don't match empty strings
                            leaks.append((line_num, line.rstrip(), secret))
        except (OSError, IOError):
            # File read errors are not secret leaks
            pass

        return leaks

    def scan_directory(self, directory: Path, pattern: Optional[str] = None) -> dict[str, List[tuple[int, str, str]]]:
        """Scan a directory for leaked secrets in files.

        Args:
            directory: Path to directory to scan
            pattern: Optional glob pattern (e.g., "*.log", "*.json")
                    If not provided, scans all files

        Returns:
            Dictionary mapping file paths to lists of leaks
            Empty dict if no leaks found
        """
        leaks_by_file = {}

        if not directory.exists():
            return leaks_by_file

        if pattern:
            files_to_scan = directory.glob(pattern)
        else:
            files_to_scan = directory.rglob("*")

        for file_path in files_to_scan:
            if file_path.is_file():
                leaks = self.scan_file(file_path)
                if leaks:
                    leaks_by_file[str(file_path)] = leaks

        return leaks_by_file

    def scan_logs(self, logs_directory: Path) -> dict[str, List[tuple[int, str, str]]]:
        """Scan log files for leaked secrets.

        Scans all .log files in the logs directory.

        Args:
            logs_directory: Path to logs directory

        Returns:
            Dictionary mapping log file paths to lists of leaks
        """
        return self.scan_directory(logs_directory, pattern="*.log")

    def scan_json_files(self, directory: Path) -> dict[str, List[tuple[int, str, str]]]:
        """Scan JSON files for leaked secrets.

        Args:
            directory: Path to directory containing JSON files

        Returns:
            Dictionary mapping JSON file paths to lists of leaks
        """
        return self.scan_directory(directory, pattern="*.json")

    def assert_no_leaks(
        self,
        *directories: Path,
        logs_dir: Optional[Path] = None,
        job_records_dir: Optional[Path] = None,
        export_files: Optional[List[Path]] = None,
    ) -> None:
        """Assert that no secrets leaked in specified locations.

        Args:
            *directories: Directories to scan
            logs_dir: Optional path to logs directory (scans *.log files)
            job_records_dir: Optional path to job records directory (scans *.json)
            export_files: Optional list of export files to scan

        Raises:
            AssertionError: If any secrets are found
        """
        all_leaks = {}

        # Scan provided directories
        for directory in directories:
            leaks = self.scan_directory(directory)
            all_leaks.update(leaks)

        # Scan logs
        if logs_dir:
            logs_leaks = self.scan_logs(logs_dir)
            all_leaks.update(logs_leaks)

        # Scan job records
        if job_records_dir:
            job_leaks = self.scan_json_files(job_records_dir)
            all_leaks.update(job_leaks)

        # Scan export files
        if export_files:
            for export_file in export_files:
                leaks = self.scan_file(export_file)
                if leaks:
                    all_leaks[str(export_file)] = leaks

        # Report findings
        if all_leaks:
            message_lines = ["Secrets leaked in the following locations:"]
            for file_path, leaks in all_leaks.items():
                message_lines.append(f"\n{file_path}:")
                for line_num, line_content, secret in leaks:
                    # Don't include the actual secret in the error message
                    message_lines.append(
                        f"  Line {line_num}: (secret found - not displayed for safety)"
                    )

            raise AssertionError("\n".join(message_lines))

    def assert_secret_found(self, file_path: Path, secret: str) -> None:
        """Assert that a secret IS found in a file (for testing the detector itself).

        Args:
            file_path: Path to file to scan
            secret: Secret to look for

        Raises:
            AssertionError: If the secret is not found
        """
        leaks = self.scan_file(file_path)
        matched_secrets = [leaked_secret for _, _, leaked_secret in leaks]

        if secret not in matched_secrets:
            raise AssertionError(
                f"Expected secret not found in {file_path}: (not displayed for safety)"
            )


def create_secret_leak_detector(*secrets: str) -> SecretLeakDetector:
    """Create and initialize a SecretLeakDetector with known test secrets.

    Usage:
        detector = create_secret_leak_detector(
            "test_api_key_12345",
            "test_password_xyz",
        )
        # Run tests...
        detector.assert_no_leaks(logs_dir=Path("/path/to/logs"))

    Args:
        *secrets: Test secrets to register

    Returns:
        Initialized SecretLeakDetector
    """
    detector = SecretLeakDetector()
    detector.register_secrets(list(secrets))
    return detector
