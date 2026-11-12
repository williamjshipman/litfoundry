"""Tests for secret leak detection."""

from pathlib import Path

import pytest

from litfoundry.test_helpers.secret_leak_detector import (
    SecretLeakDetector,
    create_secret_leak_detector,
)


@pytest.fixture
def temp_logs_dir(tmp_path: Path) -> Path:
    """Create a temporary logs directory."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    return logs_dir


class TestSecretLeakDetectorBasic:
    """Basic functionality tests."""

    def test_detector_initialization(self) -> None:
        """Verify detector initializes with empty secrets."""
        detector = SecretLeakDetector()
        assert len(detector.known_secrets) == 0

    def test_register_single_secret(self) -> None:
        """Verify registering a single secret."""
        detector = SecretLeakDetector()
        detector.register_secret("test_secret_123")
        assert "test_secret_123" in detector.known_secrets

    def test_register_multiple_secrets(self) -> None:
        """Verify registering multiple secrets at once."""
        detector = SecretLeakDetector()
        secrets = ["secret1", "secret2", "secret3"]
        detector.register_secrets(secrets)
        assert detector.known_secrets == set(secrets)

    def test_create_detector_with_secrets(self) -> None:
        """Verify create_secret_leak_detector initializes with secrets."""
        detector = create_secret_leak_detector("secret1", "secret2")
        assert "secret1" in detector.known_secrets
        assert "secret2" in detector.known_secrets


class TestSecretLeakDetectorFileScan:
    """File scanning tests."""

    def test_scan_file_not_found(self, tmp_path: Path) -> None:
        """Verify scanning non-existent file returns empty list."""
        detector = SecretLeakDetector()
        detector.register_secret("secret")

        leaks = detector.scan_file(tmp_path / "nonexistent.log")
        assert leaks == []

    def test_scan_file_with_secret(self, tmp_path: Path) -> None:
        """Verify detecting a secret in a file."""
        detector = SecretLeakDetector()
        detector.register_secret("api_key_12345")

        log_file = tmp_path / "test.log"
        log_file.write_text("Starting app\nUsing api_key_12345\nApp started")

        leaks = detector.scan_file(log_file)
        assert len(leaks) == 1
        assert leaks[0][0] == 2  # Line 2
        assert "api_key_12345" in leaks[0][1]

    def test_scan_file_without_secret(self, tmp_path: Path) -> None:
        """Verify no leaks when secret not in file."""
        detector = SecretLeakDetector()
        detector.register_secret("secret_key")

        log_file = tmp_path / "test.log"
        log_file.write_text("Normal log line\nAnother line\nNo secrets here")

        leaks = detector.scan_file(log_file)
        assert leaks == []

    def test_scan_file_multiple_secrets(self, tmp_path: Path) -> None:
        """Verify detecting multiple different secrets."""
        detector = SecretLeakDetector()
        detector.register_secrets(["api_key", "password"])

        log_file = tmp_path / "test.log"
        log_file.write_text("api_key found\npassword found\nok done")

        leaks = detector.scan_file(log_file)
        assert len(leaks) == 2

    def test_scan_file_multiple_occurrences_same_line(self, tmp_path: Path) -> None:
        """Verify detecting secret on a line (current impl finds once per secret per line)."""
        detector = SecretLeakDetector()
        detector.register_secret("secret")

        log_file = tmp_path / "test.log"
        log_file.write_text("secret and another secret on same line")

        leaks = detector.scan_file(log_file)
        # Current implementation finds one leak per (line, secret) pair
        # (not multiple occurrences of same secret on same line)
        assert len(leaks) >= 1
        assert leaks[0][0] == 1  # Line 1

    def test_scan_file_empty_secret_ignored(self, tmp_path: Path) -> None:
        """Verify that empty string secrets don't match (avoid false positives)."""
        detector = SecretLeakDetector()
        detector.register_secret("")  # Empty secret

        log_file = tmp_path / "test.log"
        log_file.write_text("anything\neverything")

        leaks = detector.scan_file(log_file)
        # Empty secrets should be ignored (secret.strip() check)
        assert leaks == []

    def test_scan_file_binary_file_ignored(self, tmp_path: Path) -> None:
        """Verify binary files are handled gracefully."""
        detector = SecretLeakDetector()
        detector.register_secret("secret")

        bin_file = tmp_path / "test.bin"
        bin_file.write_bytes(b"\x00\x01\x02\xff\xfe\xfd")

        leaks = detector.scan_file(bin_file)
        # Should handle gracefully with utf-8 decode errors
        assert isinstance(leaks, list)


class TestSecretLeakDetectorDirectoryScan:
    """Directory scanning tests."""

    def test_scan_directory_empty(self, tmp_path: Path) -> None:
        """Verify scanning empty directory."""
        detector = SecretLeakDetector()
        detector.register_secret("secret")

        leaks = detector.scan_directory(tmp_path)
        assert leaks == {}

    def test_scan_directory_with_secrets(self, tmp_path: Path) -> None:
        """Verify scanning directory finds secrets in files."""
        detector = SecretLeakDetector()
        detector.register_secret("api_key_123")

        file1 = tmp_path / "file1.txt"
        file1.write_text("api_key_123 found here")

        file2 = tmp_path / "file2.txt"
        file2.write_text("no secret here")

        leaks = detector.scan_directory(tmp_path)
        assert len(leaks) == 1
        assert str(file1) in leaks

    def test_scan_directory_with_pattern(self, tmp_path: Path) -> None:
        """Verify scanning directory with glob pattern."""
        detector = SecretLeakDetector()
        detector.register_secret("secret")

        log_file = tmp_path / "app.log"
        log_file.write_text("secret in log")

        txt_file = tmp_path / "secret.txt"
        txt_file.write_text("secret in text")

        # Only scan .log files
        leaks = detector.scan_directory(tmp_path, pattern="*.log")
        assert len(leaks) == 1
        assert str(log_file) in leaks

    def test_scan_logs_helper(self, tmp_path: Path) -> None:
        """Verify scan_logs helper scans .log files."""
        detector = SecretLeakDetector()
        detector.register_secret("secret_key")

        log_file = tmp_path / "app.log"
        log_file.write_text("secret_key exposed")

        leaks = detector.scan_logs(tmp_path)
        assert len(leaks) == 1

    def test_scan_json_files_helper(self, tmp_path: Path) -> None:
        """Verify scan_json_files helper scans .json files."""
        detector = SecretLeakDetector()
        detector.register_secret("password123")

        json_file = tmp_path / "config.json"
        json_file.write_text('{"password": "password123"}')

        leaks = detector.scan_json_files(tmp_path)
        assert len(leaks) == 1


class TestSecretLeakDetectorAssertions:
    """Assertion tests."""

    def test_assert_no_leaks_success(self, tmp_path: Path) -> None:
        """Verify assert_no_leaks passes when no secrets found."""
        detector = SecretLeakDetector()
        detector.register_secret("api_key_12345xyz")

        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        log_file = logs_dir / "app.log"
        log_file.write_text("no api keys here, everything is normal")

        # Should not raise
        detector.assert_no_leaks(logs_dir=logs_dir)

    def test_assert_no_leaks_failure(self, tmp_path: Path) -> None:
        """Verify assert_no_leaks raises when secret found."""
        detector = SecretLeakDetector()
        detector.register_secret("api_key_secret")

        log_file = tmp_path / "app.log"
        log_file.write_text("api_key_secret found")

        with pytest.raises(AssertionError, match="Secrets leaked"):
            detector.assert_no_leaks(logs_dir=tmp_path)

    def test_assert_no_leaks_multiple_locations(self, tmp_path: Path) -> None:
        """Verify assert_no_leaks scans multiple locations."""
        detector = SecretLeakDetector()
        detector.register_secret("secret")

        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        (dir1 / "file.txt").write_text("secret here")

        dir2 = tmp_path / "dir2"
        dir2.mkdir()
        (dir2 / "file.txt").write_text("no secret")

        with pytest.raises(AssertionError):
            detector.assert_no_leaks(dir1, dir2)

    def test_assert_secret_found_success(self, tmp_path: Path) -> None:
        """Verify assert_secret_found succeeds when secret is found."""
        detector = SecretLeakDetector()
        detector.register_secret("test_secret")

        file = tmp_path / "file.txt"
        file.write_text("test_secret in here")

        # Should not raise
        detector.assert_secret_found(file, "test_secret")

    def test_assert_secret_found_failure(self, tmp_path: Path) -> None:
        """Verify assert_secret_found fails when secret not found."""
        detector = SecretLeakDetector()
        detector.register_secret("secret1")

        file = tmp_path / "file.txt"
        file.write_text("no secrets")

        with pytest.raises(AssertionError, match="Expected secret not found"):
            detector.assert_secret_found(file, "secret1")


class TestSecretLeakDetectorRealWorldScenarios:
    """Real-world use case tests."""

    def test_scenario_api_key_leak_in_logs(self, tmp_path: Path) -> None:
        """Verify detecting API key leaked in logs."""
        detector = create_secret_leak_detector(
            "openAlex_api_key_test_12345",
            "wos_api_key_test_67890",
        )

        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        # Simulate accidental logging
        (logs_dir / "app.log").write_text(
            """
            [INFO] Initializing source adapter
            [DEBUG] Using openAlex_api_key_test_12345
            [INFO] Adapter initialized
            """
        )

        with pytest.raises(AssertionError):
            detector.assert_no_leaks(logs_dir=logs_dir)

    def test_scenario_password_leak_in_config(self, tmp_path: Path) -> None:
        """Verify detecting AD password in config export."""
        detector = create_secret_leak_detector("ad_service_account_password_test")

        config_file = tmp_path / "config_export.json"
        config_file.write_text('{"password": "ad_service_account_password_test"}')

        with pytest.raises(AssertionError):
            detector.assert_no_leaks(export_files=[config_file])

    def test_scenario_no_leaks_clean_run(self, tmp_path: Path) -> None:
        """Verify clean test run with no secrets leaked."""
        detector = create_secret_leak_detector(
            "test_api_key_xyz",
            "test_password_abc",
        )

        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        (logs_dir / "app.log").write_text("[INFO] App started normally\n[INFO] All good")

        export_file = tmp_path / "export.json"
        export_file.write_text('{"status": "success", "records": 100}')

        # Should not raise
        detector.assert_no_leaks(
            logs_dir=logs_dir,
            export_files=[export_file],
        )

    def test_scenario_multiple_secrets_multiple_locations(self, tmp_path: Path) -> None:
        """Verify detecting multiple secrets in multiple locations."""
        detector = create_secret_leak_detector(
            "secret1_test",
            "secret2_test",
            "secret3_test",
        )

        # Create various files with leaks
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        (logs_dir / "app.log").write_text("secret1_test exposed")

        job_records_dir = tmp_path / "jobs"
        job_records_dir.mkdir()
        (job_records_dir / "job1.json").write_text('{"args": "secret2_test"}')

        export_file = tmp_path / "export.zip"
        export_file.write_text("secret3_test in archive")

        with pytest.raises(AssertionError):
            detector.assert_no_leaks(
                logs_dir=logs_dir,
                job_records_dir=job_records_dir,
                export_files=[export_file],
            )
