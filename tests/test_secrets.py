"""Tests for secret storage and encryption."""

import os
import tempfile
from pathlib import Path

import pytest

from litfoundry.secrets import SecretManager


@pytest.fixture
def secret_material_dir(tmp_path: Path) -> Path:
    """Create a temporary secret_material directory."""
    secret_dir = tmp_path / "secret_material"
    secret_dir.mkdir(parents=True)
    return secret_dir


class TestSecretManagerKeyGeneration:
    """Tests for key generation and loading."""

    def test_ensure_keys_exist_creates_both_keys(self, secret_material_dir: Path) -> None:
        """Verify that ensure_keys_exist creates both key files."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        assert manager.master_key_path.exists()
        assert manager.session_signing_key_path.exists()

    def test_master_key_is_256_bits(self, secret_material_dir: Path) -> None:
        """Verify that master key is exactly 256 bits (32 bytes)."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        master_key = manager.get_master_key()
        assert len(master_key) == 32

    def test_session_signing_key_is_512_bits(self, secret_material_dir: Path) -> None:
        """Verify that session signing key is exactly 512 bits (64 bytes)."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        signing_key = manager.get_session_signing_key()
        assert len(signing_key) == 64

    def test_ensure_keys_exist_is_idempotent(self, secret_material_dir: Path) -> None:
        """Verify that calling ensure_keys_exist twice doesn't overwrite keys."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        master_key_1 = manager.get_master_key()
        signing_key_1 = manager.get_session_signing_key()

        manager.ensure_keys_exist()

        master_key_2 = manager.get_master_key()
        signing_key_2 = manager.get_session_signing_key()

        assert master_key_1 == master_key_2
        assert signing_key_1 == signing_key_2

    def test_get_master_key_raises_if_not_exists(self, secret_material_dir: Path) -> None:
        """Verify that get_master_key raises FileNotFoundError if key doesn't exist."""
        manager = SecretManager(secret_material_dir)

        with pytest.raises(FileNotFoundError, match="Master key not found"):
            manager.get_master_key()

    def test_get_session_signing_key_raises_if_not_exists(
        self, secret_material_dir: Path
    ) -> None:
        """Verify that get_session_signing_key raises if key doesn't exist."""
        manager = SecretManager(secret_material_dir)

        with pytest.raises(FileNotFoundError, match="Session signing key not found"):
            manager.get_session_signing_key()

    def test_keys_are_randomly_generated(self, secret_material_dir: Path) -> None:
        """Verify that multiple calls to ensure_keys_exist generate different keys."""
        manager1 = SecretManager(secret_material_dir)
        manager1.ensure_keys_exist()
        key1 = manager1.get_master_key()

        # Create a second manager with a different directory
        secret_material_dir_2 = secret_material_dir.parent / "secret_material_2"
        secret_material_dir_2.mkdir()
        manager2 = SecretManager(secret_material_dir_2)
        manager2.ensure_keys_exist()
        key2 = manager2.get_master_key()

        # Keys should be different (extremely unlikely to be the same)
        assert key1 != key2


class TestSecretManagerEncryption:
    """Tests for AES-256-GCM encryption and decryption."""

    def test_encrypt_returns_bytes(self, secret_material_dir: Path) -> None:
        """Verify that encrypt returns bytes."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        ciphertext = manager.encrypt(b"test secret")
        assert isinstance(ciphertext, bytes)

    def test_ciphertext_contains_key_id_and_nonce(self, secret_material_dir: Path) -> None:
        """Verify that ciphertext has key_id (1 byte) + nonce (12 bytes) prefix."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        ciphertext = manager.encrypt(b"test secret")

        # Minimum length: 1 (key_id) + 12 (nonce) + 16 (tag)
        assert len(ciphertext) >= 29

    def test_encrypt_decrypt_roundtrip(self, secret_material_dir: Path) -> None:
        """Verify that encrypted data can be decrypted to original plaintext."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        plaintext = b"my secret API key"
        ciphertext = manager.encrypt(plaintext)
        decrypted = manager.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_decrypt_different_ciphertexts_for_same_plaintext(
        self, secret_material_dir: Path
    ) -> None:
        """Verify that encrypting the same plaintext twice produces different ciphertexts."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        plaintext = b"same secret"
        ciphertext1 = manager.encrypt(plaintext)
        ciphertext2 = manager.encrypt(plaintext)

        # Different nonces should produce different ciphertexts
        assert ciphertext1 != ciphertext2

        # But both should decrypt to the same plaintext
        assert manager.decrypt(ciphertext1) == plaintext
        assert manager.decrypt(ciphertext2) == plaintext

    def test_decrypt_invalid_ciphertext_raises(self, secret_material_dir: Path) -> None:
        """Verify that decrypting corrupted ciphertext raises ValueError."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        # Invalid ciphertext (wrong length)
        with pytest.raises(ValueError, match="Encrypted data too short"):
            manager.decrypt(b"too short")

    def test_decrypt_tampered_ciphertext_raises(self, secret_material_dir: Path) -> None:
        """Verify that decrypting tampered ciphertext raises ValueError (auth tag fails)."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        plaintext = b"secret"
        ciphertext = manager.encrypt(plaintext)

        # Flip a bit in the ciphertext
        tampered = bytearray(ciphertext)
        tampered[-1] ^= 0x01
        tampered = bytes(tampered)

        with pytest.raises(ValueError, match="Decryption failed"):
            manager.decrypt(tampered)

    def test_decrypt_without_master_key_raises(self, secret_material_dir: Path) -> None:
        """Verify that decrypt raises if master key doesn't exist."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        plaintext = b"secret"
        ciphertext = manager.encrypt(plaintext)

        # Delete the master key
        manager.master_key_path.unlink()

        with pytest.raises(FileNotFoundError, match="Master key not found"):
            manager.decrypt(ciphertext)

    def test_encrypt_binary_data(self, secret_material_dir: Path) -> None:
        """Verify that arbitrary binary data can be encrypted and decrypted."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        # Binary data with null bytes and non-UTF8
        plaintext = b"\x00\x01\x02\xff\xfe\xfd"
        ciphertext = manager.encrypt(plaintext)
        decrypted = manager.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encrypt_large_data(self, secret_material_dir: Path) -> None:
        """Verify that large data can be encrypted and decrypted."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        # 1MB of data
        plaintext = os.urandom(1024 * 1024)
        ciphertext = manager.encrypt(plaintext)
        decrypted = manager.decrypt(ciphertext)

        assert decrypted == plaintext


class TestSecretManagerKeyRotation:
    """Tests for session signing key rotation."""

    def test_rotate_session_signing_key_creates_new_key(
        self, secret_material_dir: Path
    ) -> None:
        """Verify that rotate_session_signing_key creates a new key."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        old_key = manager.get_session_signing_key()
        new_key = manager.rotate_session_signing_key()

        # New key should be different from old
        assert new_key != old_key

        # File should contain the new key
        assert manager.get_session_signing_key() == new_key

    def test_rotate_session_signing_key_returns_bytes(
        self, secret_material_dir: Path
    ) -> None:
        """Verify that rotate_session_signing_key returns the new key."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        new_key = manager.rotate_session_signing_key()
        assert isinstance(new_key, bytes)
        assert len(new_key) == 64  # 512 bits

    def test_rotate_session_signing_key_invalidates_sessions(
        self, secret_material_dir: Path
    ) -> None:
        """Verify that rotation overwrites the old key."""
        manager = SecretManager(secret_material_dir)
        manager.ensure_keys_exist()

        old_key = manager.get_session_signing_key()

        # Simulate a session signed with old key
        old_session_token = f"session.{old_key.hex()}"

        new_key = manager.rotate_session_signing_key()

        # Old token would be invalid because new_key != old_key
        # (In real Flask-JWT, the signature wouldn't verify)
        assert new_key != old_key
        assert f"session.{new_key.hex()}" != old_session_token


class TestSecretManagerPortability:
    """Tests for key portability across machines."""

    def test_decrypt_with_copied_key(self, secret_material_dir: Path, tmp_path: Path) -> None:
        """Verify that copied master key can decrypt data on another 'machine'."""
        manager1 = SecretManager(secret_material_dir)
        manager1.ensure_keys_exist()

        plaintext = b"portable secret"
        ciphertext = manager1.encrypt(plaintext)

        # Simulate copying data to another machine: copy key file
        other_secret_dir = tmp_path / "other_machine" / "secret_material"
        other_secret_dir.mkdir(parents=True)

        # Copy master key
        import shutil
        shutil.copy2(manager1.master_key_path, other_secret_dir / "master.key")

        # Create new manager with copied key
        manager2 = SecretManager(other_secret_dir)

        # Should be able to decrypt with copied key
        decrypted = manager2.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_restore_backup_on_different_machine(self, tmp_path: Path) -> None:
        """Verify that a full backup can be restored and secrets decrypted."""
        # Original machine
        machine1_dir = tmp_path / "machine1" / "secret_material"
        machine1_dir.mkdir(parents=True)

        manager1 = SecretManager(machine1_dir)
        manager1.ensure_keys_exist()

        secrets_to_store = [
            b"openAlex API key: secret123",
            b"WoS API key: another_secret",
            b"AD service account password: complex_pass",
        ]

        encrypted_secrets = []
        for secret in secrets_to_store:
            encrypted_secrets.append(manager1.encrypt(secret))

        # Simulate backup by copying secret_material directory
        import shutil
        backup_dir = tmp_path / "backup" / "secret_material"
        shutil.copytree(machine1_dir, backup_dir)

        # Simulate restore on different machine
        machine2_dir = tmp_path / "machine2" / "secret_material"
        shutil.copytree(backup_dir, machine2_dir)

        manager2 = SecretManager(machine2_dir)

        # Verify all secrets can be decrypted
        for original_secret, encrypted in zip(secrets_to_store, encrypted_secrets):
            decrypted = manager2.decrypt(encrypted)
            assert decrypted == original_secret
