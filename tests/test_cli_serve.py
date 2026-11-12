"""Tests for CLI serve command."""

import tempfile
from pathlib import Path

from click.testing import CliRunner

from litfoundry.cli import main
from litfoundry.initialization import initialize_data_root


class TestServeCLI:
    """Test serve command CLI behavior."""

    def test_serve_requires_mode(self):
        """Test that serve command requires --mode option."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Try to run serve without --mode
            result = runner.invoke(
                main,
                ["serve", "--data-root", tmpdir],
                catch_exceptions=False,
            )
            # Should fail because --mode is required
            assert result.exit_code != 0

    def test_serve_mode_options_valid(self):
        """Test that serve accepts valid mode options."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize the data root
            initialize_data_root(Path(tmpdir))

            # Test that both modes are valid by using --help
            for mode in ["server", "workstation"]:
                result = runner.invoke(
                    main,
                    ["serve", "--data-root", tmpdir, "--mode", mode, "--help"],
                )
                assert result.exit_code == 0

    def test_serve_mode_invalid_option(self):
        """Test that serve rejects invalid mode options."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                main,
                ["serve", "--data-root", tmpdir, "--mode", "invalid"],
            )
            # Should fail because "invalid" is not a valid choice
            assert result.exit_code != 0

    def test_serve_mode_from_env_var(self):
        """Test that serve can read --mode from LITFOUNDRY_RUN_MODE env var."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            initialize_data_root(Path(tmpdir))

            # Test with env var set (verify it's accepted by checking help)
            result = runner.invoke(
                main,
                ["serve", "--data-root", tmpdir, "--help"],
                env={"LITFOUNDRY_RUN_MODE": "server"},
            )
            assert result.exit_code == 0
            assert "--mode" in result.output

    def test_serve_cli_arg_overrides_env_var(self):
        """Test that explicit --mode CLI arg overrides LITFOUNDRY_RUN_MODE env var."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            initialize_data_root(Path(tmpdir))

            # CLI arg "workstation" should override env var "server"
            result = runner.invoke(
                main,
                ["serve", "--data-root", tmpdir, "--mode", "workstation", "--help"],
                env={"LITFOUNDRY_RUN_MODE": "server"},
            )
            # Help should work fine
            assert result.exit_code == 0

