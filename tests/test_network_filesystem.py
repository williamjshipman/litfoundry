"""Network filesystem detection tests."""

import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from litfoundry.filesystem import check_network_filesystem


class TestWindowsNetworkDetection:
    """Windows network filesystem detection tests."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_reject_unc_path(self):
        """Test that UNC paths are rejected."""
        unc_path = Path("\\\\server\\share\\data")
        with pytest.raises(ValueError, match="UNC paths"):
            check_network_filesystem(unc_path)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_reject_network_drive_mocked(self):
        """Test that network drives (DRIVE_REMOTE=4) are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Mock GetDriveTypeW to return DRIVE_REMOTE (4)
            with mock.patch("ctypes.windll.kernel32.GetDriveTypeW", return_value=4):
                with pytest.raises(ValueError, match="Network drive"):
                    check_network_filesystem(root)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_accept_local_drive_mocked(self):
        """Test that local drives (DRIVE_FIXED=3) are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Mock GetDriveTypeW to return DRIVE_FIXED (3)
            with mock.patch("ctypes.windll.kernel32.GetDriveTypeW", return_value=3):
                # Should not raise
                check_network_filesystem(root)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_accept_path_when_drive_type_unavailable(self):
        """Test that paths are accepted when GetDriveTypeW is unavailable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Mock to raise AttributeError (unavailable on non-Windows)
            with mock.patch("ctypes.windll.kernel32.GetDriveTypeW", side_effect=AttributeError):
                # Should not raise; allows graceful fallback
                check_network_filesystem(root)


class TestLinuxNetworkDetection:
    """Linux network filesystem detection tests."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Linux only")
    def test_reject_nfs_mount_mocked(self):
        """Test that NFS mounts are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            mountinfo_content = """
26 25 0:25 / /dev devtmpfs rw,nosuid,size=4096k,nr_inodes=1024,mode=755 - devtmpfs devtmpfs rw
27 25 0:26 / /dev/shm tmpfs rw,nosuid,nodev - tmpfs tmpfs rw
28 25 0:27 / /run tmpfs rw,nosuid,nodev,mode=755 - tmpfs tmpfs rw
29 25 0:28 / /run/lock tmpfs rw,nosuid,nodev,noexec,mode=1777 - tmpfs tmpfs rw
80 29 8:1 / /mnt nfs ro,relatime,vers=4.2,rsize=131072,wsize=131072 - nfs server:/export rw
"""
            # Mock /proc/self/mountinfo to include an NFS mount
            with mock.patch("builtins.open", mock.mock_open(read_data=mountinfo_content)):
                with pytest.raises(ValueError, match="network filesystem nfs"):
                    check_network_filesystem(root)

    @pytest.mark.skipif(sys.platform == "win32", reason="Linux only")
    def test_reject_cifs_mount_mocked(self):
        """Test that CIFS (SMB) mounts are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            mountinfo_content = """
28 25 0:27 / /run tmpfs rw,nosuid,nodev,mode=755 - tmpfs tmpfs rw
80 29 0:50 / /mnt cifs rw,relatime,vers=3.1.1,username=user,uid=1000 - cifs //server/share rw
"""
            with mock.patch("builtins.open", mock.mock_open(read_data=mountinfo_content)):
                with pytest.raises(ValueError, match="network filesystem cifs"):
                    check_network_filesystem(root)

    @pytest.mark.skipif(sys.platform == "win32", reason="Linux only")
    def test_accept_local_mount_mocked(self):
        """Test that local mounts (ext4, btrfs, etc.) are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            mountinfo_content = """
26 25 0:25 / /dev devtmpfs rw,nosuid,size=4096k,nr_inodes=1024,mode=755 - devtmpfs devtmpfs rw
27 25 0:26 / /dev/shm tmpfs rw,nosuid,nodev - tmpfs tmpfs rw
28 25 0:27 / /run tmpfs rw,nosuid,nodev,mode=755 - tmpfs tmpfs rw
29 25 8:1 / / ext4 rw,relatime,errors=remount-ro - ext4 /dev/sda1 rw
"""
            with mock.patch("builtins.open", mock.mock_open(read_data=mountinfo_content)):
                # Should not raise
                check_network_filesystem(root)

    @pytest.mark.skipif(sys.platform == "win32", reason="Linux only")
    def test_accept_path_when_mountinfo_unavailable(self):
        """Test that paths are accepted when /proc/self/mountinfo is unavailable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            with mock.patch("builtins.open", side_effect=FileNotFoundError):
                # Should not raise; allows graceful fallback
                check_network_filesystem(root)


class TestMacOSNetworkDetection:
    """macOS network filesystem detection tests."""

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_reject_nfs_mount_mocked(self):
        """Test that NFS mounts are rejected on macOS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            mnttab_content = """server:/export /mnt nfs rw,nodev,nosuid,noatime 0 0
/dev/disk1s1 / apfs rw,local,journaled,nodev,nosuid 0 0
"""
            with mock.patch("builtins.open", mock.mock_open(read_data=mnttab_content)):
                with pytest.raises(ValueError, match="network filesystem nfs"):
                    check_network_filesystem(root)

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_reject_smbfs_mount_mocked(self):
        """Test that SMB mounts are rejected on macOS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            mnttab_content = """//user@server/share /mnt smbfs rw,nodev,nosuid 0 0
/dev/disk1s1 / apfs rw,local,journaled,nodev,nosuid 0 0
"""
            with mock.patch("builtins.open", mock.mock_open(read_data=mnttab_content)):
                with pytest.raises(ValueError, match="network filesystem smbfs"):
                    check_network_filesystem(root)

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_accept_local_mount_mocked(self):
        """Test that local mounts (apfs, hfs+) are accepted on macOS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            mnttab_content = """/dev/disk1s1 / apfs rw,local,journaled,nodev,nosuid 0 0
/dev/disk2s1 /Volumes/Data hfs+ rw,local,nodev,nosuid 0 0
"""
            with mock.patch("builtins.open", mock.mock_open(read_data=mnttab_content)):
                # Should not raise
                check_network_filesystem(root)

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_accept_path_when_mnttab_unavailable(self):
        """Test that paths are accepted when /etc/mnttab is unavailable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            with mock.patch("builtins.open", side_effect=FileNotFoundError):
                # Should not raise; allows graceful fallback
                check_network_filesystem(root)


class TestNetworkDetectionIntegration:
    """Integration tests for network filesystem detection."""

    def test_valid_local_path(self):
        """Test that a valid local path passes detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Should not raise
            check_network_filesystem(root)

    def test_symlinked_path(self):
        """Test that symlinked paths are checked (may pass or fail depending on target)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            link = root / "link"
            link.symlink_to(target)

            # Symlink to local path should pass
            check_network_filesystem(link)
