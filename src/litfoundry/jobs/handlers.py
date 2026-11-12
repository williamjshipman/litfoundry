"""Test job types for background jobs."""

from pathlib import Path
import json
import tempfile

from litfoundry.jobs import JobContext, JobResult, JobStatus, JobProgress


def create_test_job_handler() -> callable:
    """Factory function that returns a test job handler.
    
    Returns:
        A handler function
    """
    def _test_job_handler(ctx: JobContext) -> JobResult:
        """A simple test job handler for testing.
        
        This handler:
        - Reports progress
        - Can be cancelled at checkpoints
        - Can be configured to pass or fail
        
        Args:
            ctx: Job context
            
        Returns:
            Job result
        """
        # Parse any job configuration from progress data
        config = {}
        if ctx.job.progress_json:
            try:
                config = json.loads(ctx.job.progress_json)
            except (json.JSONDecodeError, TypeError):
                pass
        
        should_fail = config.get("should_fail", False)
        failure_mode = config.get("failure_mode", "retryable")  # retryable or non_retryable
        items = config.get("items", 10)
        
        # Simulate processing items
        for i in range(items):
            # Checkpoint between items (checks for cancellation, renews lease, checks barrier)
            ctx.checkpoint()
            
            # Update progress
            progress = JobProgress(
                message=f"Processing item {i + 1}/{items}",
                percent_complete=(i + 1) / items * 100,
                current_item=f"item-{i}",
            )
            ctx.progress(progress)
        
        # Check authorization before returning
        if not ctx.authorize("editor"):
            from litfoundry.jobs import NonRetryableError
            raise NonRetryableError(
                "No longer authorized to perform this operation",
                "FORBIDDEN",
            )
        
        if should_fail:
            from litfoundry.jobs import RetryableError, NonRetryableError
            
            if failure_mode == "retryable":
                raise RetryableError("Simulated retryable failure", "TEMPORARY_ERROR")
            else:
                raise NonRetryableError(
                    "Simulated non-retryable failure",
                    "TEST_ERROR",
                    "SIMULATED_ERROR",
                )
        
        # Return success
        return JobResult(
            status=JobStatus.COMPLETED,
            progress=JobProgress(
                message="All items processed successfully",
                percent_complete=100.0,
            ),
        )
    
    return _test_job_handler


# Create a default instance (internal use only)
_internal_test_job_handler = create_test_job_handler()

# To use in tests, import create_test_job_handler() directly
def get_test_job_handler():
    """Get the default test job handler."""
    global _internal_test_job_handler
    return _internal_test_job_handler

