"""Secret storage and encryption utilities.

Manages master key and session signing key generation, storage, and rotation.
Provides AES-256-GCM encryption with key ID-based key rotation support.
"""

import os
import secrets
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes


class SecretManager:
    """Manages master key, session signing key, and secret encryption."""

    MASTER_KEY_FILE = "master.key"
    SESSION_SIGNING_KEY_FILE = "session_signing.key"
    KEY_SIZE_BYTES = 32  # 256 bits for AES-256
    SIGNING_KEY_SIZE_BYTES = 64  # 512 bits
    NONCE_SIZE_BYTES = 12  # 96 bits for AES-GCM
    CURRENT_KEY_ID = 0  # Current key version (incremented on rotation)

    def __init__(self, secret_material_dir: Path) -> None:
        """Initialize SecretManager with secret_material directory.

        Args:
            secret_material_dir: Path to the secret_material directory
        """
        self.secret_material_dir = Path(secret_material_dir)
        self.master_key_path = self.secret_material_dir / self.MASTER_KEY_FILE
        self.session_signing_key_path = (
            self.secret_material_dir / self.SESSION_SIGNING_KEY_FILE
        )

    def ensure_keys_exist(self) -> None:
        """Create master key and session signing key if they don't exist.

        Creates files with OS-specific restrictive permissions (already applied
        to secret_material directory by filesystem.apply_permissions).
        """
        self.secret_material_dir.mkdir(parents=True, exist_ok=True)

        if not self.master_key_path.exists():
            key = secrets.token_bytes(self.KEY_SIZE_BYTES)
            self.master_key_path.write_bytes(key)

        if not self.session_signing_key_path.exists():
            key = secrets.token_bytes(self.SIGNING_KEY_SIZE_BYTES)
            self.session_signing_key_path.write_bytes(key)

    def get_master_key(self) -> bytes:
        """Load master key from file.

        Returns:
            256-bit master key as bytes

        Raises:
            FileNotFoundError: If master key file does not exist
        """
        if not self.master_key_path.exists():
            raise FileNotFoundError(f"Master key not found at {self.master_key_path}")
        return self.master_key_path.read_bytes()

    def get_session_signing_key(self) -> bytes:
        """Load session signing key from file.

        Returns:
            512-bit session signing key as bytes

        Raises:
            FileNotFoundError: If session signing key file does not exist
        """
        if not self.session_signing_key_path.exists():
            raise FileNotFoundError(
                f"Session signing key not found at {self.session_signing_key_path}"
            )
        return self.session_signing_key_path.read_bytes()

    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt plaintext using AES-256-GCM with key ID.

        Format: [key_id: 1 byte][nonce: 12 bytes][ciphertext + tag: variable]

        Args:
            plaintext: Data to encrypt

        Returns:
            Encrypted bytes with key ID and nonce

        Raises:
            FileNotFoundError: If master key does not exist
        """
        master_key = self.get_master_key()
        nonce = secrets.token_bytes(self.NONCE_SIZE_BYTES)

        cipher = AESGCM(master_key)
        ciphertext = cipher.encrypt(nonce, plaintext, None)

        key_id = bytes([self.CURRENT_KEY_ID])
        return key_id + nonce + ciphertext

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt AES-256-GCM ciphertext with key ID.

        Format: [key_id: 1 byte][nonce: 12 bytes][ciphertext + tag: variable]

        Args:
            encrypted_data: Encrypted bytes with key ID and nonce

        Returns:
            Decrypted plaintext

        Raises:
            FileNotFoundError: If master key does not exist
            ValueError: If decryption fails (invalid key or corrupted data)
        """
        if len(encrypted_data) < 13:  # 1 byte key_id + 12 bytes nonce
            raise ValueError("Encrypted data too short")

        key_id = encrypted_data[0]
        nonce = encrypted_data[1:13]
        ciphertext = encrypted_data[13:]

        master_key = self.get_master_key()

        cipher = AESGCM(master_key)
        try:
            plaintext = cipher.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

        return plaintext

    def rotate_session_signing_key(self) -> bytes:
        """Rotate the session signing key and return the new key.

        Creates a new session signing key file. All existing sessions will be
        invalidated on next request because they were signed with the old key.

        Returns:
            New 512-bit session signing key as bytes
        """
        new_key = secrets.token_bytes(self.SIGNING_KEY_SIZE_BYTES)
        self.session_signing_key_path.write_bytes(new_key)
        return new_key
