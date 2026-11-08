"""Project file management with write-once guarantees."""

import os
import tempfile
from pathlib import Path
from typing import BinaryIO, Optional
import shutil


class WriteOnceFileHelper:
    """Helper for writing files with write-once semantics and atomicity guarantees."""
    
    @staticmethod
    def write_bytes(target_path: Path, data: bytes, project_path: Optional[Path] = None) -> None:
        """Write bytes to a file with write-once guarantees.
        
        Steps:
        1. Write to temporary file with .tmp extension
        2. Flush and fsync to ensure durability
        3. Atomically rename to final destination
        
        Args:
            target_path: Final destination path
            data: Bytes to write
            project_path: Project path (used for temp file placement)
            
        Raises:
            IOError: If write fails at any step
        """
        target_path = Path(target_path)
        
        # Ensure target parent directory exists first
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Determine temp directory (prefer project temp/ if available)
        if project_path:
            temp_dir = Path(project_path) / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            temp_dir = target_path.parent
        
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(
            dir=str(temp_dir),
            prefix=".tmp-",
            suffix=""
        )
        
        try:
            # Write data
            with os.fdopen(temp_fd, 'wb') as f:
                f.write(data)
                f.flush()
                # Force data to disk
                os.fsync(f.fileno())
            
            # Atomically rename to final destination
            # os.replace() is atomic on Windows and Unix
            os.replace(temp_path, target_path)
        except Exception as e:
            # Clean up temp file on failure
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise IOError(f"Failed to write file {target_path}: {e}")
    
    @staticmethod
    def write_text(target_path: Path, content: str, encoding: str = 'utf-8', 
                  project_path: Optional[Path] = None) -> None:
        """Write text to a file with write-once guarantees.
        
        Args:
            target_path: Final destination path
            content: Text content to write
            encoding: Text encoding (default: utf-8)
            project_path: Project path (used for temp file placement)
            
        Raises:
            IOError: If write fails at any step
        """
        data = content.encode(encoding)
        WriteOnceFileHelper.write_bytes(target_path, data, project_path)
    
    @staticmethod
    def write_file_from_stream(target_path: Path, source_stream: BinaryIO, 
                              project_path: Optional[Path] = None) -> int:
        """Write data from a stream to a file with write-once guarantees.
        
        Args:
            target_path: Final destination path
            source_stream: Input stream to read from
            project_path: Project path (used for temp file placement)
            
        Returns:
            Number of bytes written
            
        Raises:
            IOError: If write fails at any step
        """
        target_path = Path(target_path)
        
        # Determine temp directory
        if project_path:
            temp_dir = Path(project_path) / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            temp_dir = target_path.parent
        
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(
            dir=str(temp_dir),
            prefix=".tmp-",
            suffix=""
        )
        
        bytes_written = 0
        try:
            # Write from stream
            with os.fdopen(temp_fd, 'wb') as f:
                while True:
                    chunk = source_stream.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_written += len(chunk)
                
                f.flush()
                # Force data to disk
                os.fsync(f.fileno())
            
            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Atomically rename to final destination
            os.replace(temp_path, target_path)
        except Exception as e:
            # Clean up temp file on failure
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise IOError(f"Failed to write file {target_path}: {e}")
        
        return bytes_written


class StagedProvisioning:
    """Manages staged project provisioning with atomic rename and cleanup."""
    
    @staticmethod
    def create_staging_folder(data_root: Path, project_id: str) -> Path:
        """Create a temporary staging folder for a new project.
        
        Args:
            data_root: Root data directory
            project_id: Project UUID
            
        Returns:
            Path to the staging folder
            
        Raises:
            IOError: If staging folder creation fails
        """
        projects_dir = data_root / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        
        staging_path = projects_dir / f".staging-{project_id}"
        
        try:
            staging_path.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            raise IOError(f"Staging folder already exists: {staging_path}")
        
        return staging_path
    
    @staticmethod
    def commit_staging_folder(data_root: Path, project_id: str) -> Path:
        """Atomically rename a staging folder to its final location.
        
        Args:
            data_root: Root data directory
            project_id: Project UUID
            
        Returns:
            Path to the final project folder
            
        Raises:
            IOError: If rename fails
        """
        projects_dir = data_root / "projects"
        staging_path = projects_dir / f".staging-{project_id}"
        final_path = projects_dir / project_id
        
        if not staging_path.exists():
            raise IOError(f"Staging folder not found: {staging_path}")
        
        if final_path.exists():
            raise IOError(f"Final folder already exists: {final_path}")
        
        try:
            # os.replace() is atomic on Windows and Unix
            os.replace(staging_path, final_path)
        except Exception as e:
            raise IOError(f"Failed to rename staging folder: {e}")
        
        return final_path
    
    @staticmethod
    def cleanup_staging_folder(data_root: Path, project_id: str) -> None:
        """Remove a staging folder if provisioning failed.
        
        Args:
            data_root: Root data directory
            project_id: Project UUID
        """
        projects_dir = data_root / "projects"
        staging_path = projects_dir / f".staging-{project_id}"
        
        if staging_path.exists():
            try:
                shutil.rmtree(staging_path)
            except Exception:
                # Best effort cleanup
                pass
    
    @staticmethod
    def create_project_subdirectories(project_path: Path) -> None:
        """Create the standard project subdirectories.
        
        Args:
            project_path: Path to the project folder
        """
        subdirs = ["sources", "imports", "attachments", "figures", "reports", "exports", "temp"]
        
        for subdir in subdirs:
            (project_path / subdir).mkdir(parents=True, exist_ok=True)
