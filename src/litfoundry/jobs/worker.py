"""Background job worker implementation."""

import logging
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable
from uuid import uuid4

from litfoundry.jobs.queue import JobQueue, HEARTBEAT_INTERVAL_SECONDS

logger = logging.getLogger(__name__)


class Worker:
    """A background job worker process."""

    def __init__(
        self,
        catalog_engine,
        data_root: Path,
        worker_id: Optional[str] = None,
    ):
        """Initialize a worker.
        
        Args:
            catalog_engine: SQLAlchemy engine for the catalogue database
            data_root: Root directory for project databases
            worker_id: Optional worker ID (auto-generated if not provided)
        """
        self.catalog_engine = catalog_engine
        self.data_root = data_root
        self.worker_id = worker_id or str(uuid4())
        self.queue = JobQueue(catalog_engine, self.worker_id)
        self._running = False
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._main_thread_interrupted = False

    def register_handler(
        self,
        job_type: str,
        handler: Callable,
    ) -> None:
        """Register a job handler.
        
        Args:
            job_type: Type of job
            handler: Handler callable
        """
        self.queue.register_handler(job_type, handler)

    def run(self) -> None:
        """Run the worker main loop.
        
        Continuously claims and executes jobs until interrupted.
        Handles graceful shutdown on SIGTERM and SIGINT.
        """
        logger.info(f"Worker {self.worker_id} starting")
        self._running = True

        # Set up signal handlers for graceful shutdown
        def handle_shutdown(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            self._running = False
            self._main_thread_interrupted = True

        # Register signal handlers
        try:
            signal.signal(signal.SIGTERM, handle_shutdown)
            signal.signal(signal.SIGINT, handle_shutdown)
        except (ValueError, OSError):
            # Signals not available on this platform
            pass

        # Start heartbeat thread
        self._start_heartbeat_thread()

        try:
            # Main loop: claim and execute jobs
            while self._running:
                try:
                    job = self.queue.claim()
                    if not job:
                        # No jobs available, sleep before trying again
                        time.sleep(1)
                        continue

                    logger.info(f"Claimed job {job.id} (type={job.type}, user={job.user_id})")

                    # Create temp directory for this job
                    job_temp_dir = self.data_root / ".jobs" / job.id
                    job_temp_dir.mkdir(parents=True, exist_ok=True)

                    try:
                        # Execute the job
                        self.queue.execute_job(job, job_temp_dir)
                        logger.info(f"Completed job {job.id}")
                    except Exception as e:
                        logger.exception(f"Failed to execute job {job.id}: {e}")
                    finally:
                        # Clean up temp directory
                        try:
                            import shutil

                            shutil.rmtree(job_temp_dir, ignore_errors=True)
                        except Exception as e:
                            logger.warning(f"Could not clean up temp dir for {job.id}: {e}")

                except Exception as e:
                    logger.exception(f"Error in worker main loop: {e}")
                    time.sleep(1)

        finally:
            self._stop_heartbeat_thread()
            logger.info(f"Worker {self.worker_id} stopped")

    def _start_heartbeat_thread(self) -> None:
        """Start the lease heartbeat thread."""
        if self._heartbeat_thread is not None:
            return

        def heartbeat_loop():
            while self._running:
                try:
                    # Renew leases for all running jobs owned by this worker
                    self._renew_all_leases()
                except Exception as e:
                    logger.exception(f"Error in heartbeat loop: {e}")

                # Sleep until next heartbeat
                time.sleep(HEARTBEAT_INTERVAL_SECONDS)

        self._heartbeat_thread = threading.Thread(
            target=heartbeat_loop,
            daemon=True,
            name=f"heartbeat-{self.worker_id}",
        )
        self._heartbeat_thread.start()
        logger.debug(f"Heartbeat thread started for worker {self.worker_id}")

    def _stop_heartbeat_thread(self) -> None:
        """Stop the lease heartbeat thread."""
        if self._heartbeat_thread is None:
            return

        self._running = False
        if self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5.0)

        logger.debug(f"Heartbeat thread stopped for worker {self.worker_id}")

    def _renew_all_leases(self) -> None:
        """Renew leases for all running jobs owned by this worker."""
        from sqlalchemy import text

        with self.catalog_engine.connect() as conn:
            # Find all running jobs owned by this worker
            result = conn.execute(
                text(
                    "SELECT id FROM jobs WHERE lease_owner = :owner AND status = 'running'"
                ),
                {"owner": self.worker_id},
            )
            job_ids = [row[0] for row in result.fetchall()]

        for job_id in job_ids:
            try:
                self.queue._renew_lease(job_id, self.worker_id)
            except Exception as e:
                logger.warning(f"Could not renew lease for job {job_id}: {e}")


class Supervisor:
    """Supervisor process that manages worker processes and server."""

    def __init__(
        self,
        data_root: Path,
        port: int = 5080,
        mode: str = "server",
        num_workers: int = 4,
    ):
        """Initialize the supervisor.
        
        Args:
            data_root: Root directory for project databases
            port: Port for the server
            mode: Execution mode (server or workstation)
            num_workers: Number of worker processes to run
        """
        self.data_root = data_root
        self.port = port
        self.mode = mode
        self.num_workers = num_workers
        self._running = False
        self._child_processes = {}
        self._restart_backoff = {}  # Track restart backoff per process type

    def run(self) -> None:
        """Run the supervisor main loop.
        
        Manages the server process and worker processes.
        Restarts crashed children with exponential backoff.
        Forwards SIGTERM/SIGINT for graceful shutdown.
        """
        logger.info(f"Supervisor starting with {self.num_workers} workers")
        self._running = True

        # Set up signal handlers for graceful shutdown
        def handle_shutdown(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            self._running = False
            self._shutdown_children()

        try:
            signal.signal(signal.SIGTERM, handle_shutdown)
            signal.signal(signal.SIGINT, handle_shutdown)
        except (ValueError, OSError):
            pass

        try:
            # Main loop: manage child processes
            while self._running:
                # Ensure server is running
                if "server" not in self._child_processes or self._child_processes[
                    "server"
                ].poll() is not None:
                    logger.info("Starting server process")
                    try:
                        proc = subprocess.Popen(
                            [
                                sys.executable,
                                "-m",
                                "litfoundry.cli",
                                "serve",
                                "--data-root",
                                str(self.data_root),
                                "--port",
                                str(self.port),
                                "--mode",
                                self.mode,
                            ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
                        )
                        self._child_processes["server"] = proc
                        self._restart_backoff["server"] = 0.5
                        logger.info(f"Server process started (PID {proc.pid})")
                    except Exception as e:
                        logger.error(f"Failed to start server: {e}")
                        time.sleep(self._restart_backoff.get("server", 0.5))
                        self._restart_backoff["server"] = min(
                            (self._restart_backoff.get("server", 0.5) * 2), 60
                        )

                # Ensure workers are running
                for i in range(self.num_workers):
                    worker_key = f"worker-{i}"
                    if worker_key not in self._child_processes or self._child_processes[
                        worker_key
                    ].poll() is not None:
                        logger.info(f"Starting worker process {i}")
                        try:
                            proc = subprocess.Popen(
                                [
                                    sys.executable,
                                    "-m",
                                    "litfoundry.cli",
                                    "worker",
                                    "--data-root",
                                    str(self.data_root),
                                ],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
                            )
                            self._child_processes[worker_key] = proc
                            self._restart_backoff[worker_key] = 0.5
                            logger.info(f"Worker process {i} started (PID {proc.pid})")
                        except Exception as e:
                            logger.error(f"Failed to start worker {i}: {e}")
                            time.sleep(self._restart_backoff.get(worker_key, 0.5))
                            self._restart_backoff[worker_key] = min(
                                (self._restart_backoff.get(worker_key, 0.5) * 2), 60
                            )

                # Check for dead children and sleep
                time.sleep(5)

        finally:
            self._shutdown_children()
            logger.info("Supervisor stopped")

    def _shutdown_children(self) -> None:
        """Send SIGTERM to all child processes and wait for them to exit."""
        if not self._child_processes:
            return

        logger.info("Shutting down child processes")

        # Send SIGTERM to all children
        for name, proc in list(self._child_processes.items()):
            if proc and proc.poll() is None:
                logger.debug(f"Terminating {name} (PID {proc.pid})")
                try:
                    if hasattr(os, "killpg"):
                        # Unix: kill process group
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    else:
                        # Windows: terminate process
                        proc.terminate()
                except Exception as e:
                    logger.warning(f"Could not terminate {name}: {e}")

        # Wait for all children to exit with timeout
        deadline = time.time() + 30
        for name, proc in self._child_processes.items():
            timeout = max(0, deadline - time.time())
            if proc and proc.poll() is None:
                logger.debug(f"Waiting for {name} to exit (timeout {timeout}s)")
                try:
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    logger.warning(f"{name} did not exit, killing")
                    try:
                        proc.kill()
                        proc.wait(timeout=5)
                    except Exception as e:
                        logger.error(f"Could not kill {name}: {e}")

        self._child_processes.clear()
        logger.info("All child processes terminated")
