"""Job Scheduler Configuration.

This module initializes the global JobManager instance, registers background jobs,
and provides public wrapper functions to start/stop the scheduler, inspect job lists,
and manually trigger executions.
"""

from sc_automation_hub.job_service import JobDefinition, JobManager
from sc_automation_hub.tasks import update_recurring_tasks


# Instantiate the global JobManager
job_manager = JobManager()

# Register the default recurring Notion task update job
job_manager.register_job(
  JobDefinition(
    job_id="update_recurring_tasks",
    label="Update recurring tasks",
    description="Fetches recurring Notion tasks and updates their due dates.",
    interval_minutes=5,
    runner=update_recurring_tasks,
  )
)


def start_scheduler():
  """Starts the background scheduler loop for registered jobs."""
  print("Starting the scheduler...")
  job_manager.start()


def stop_scheduler():
  """Shuts down the background scheduler."""
  job_manager.stop()


def list_jobs():
  """Lists all registered jobs and their state details.

  Returns:
      A list of dictionaries containing job properties and status.
  """
  return job_manager.list_jobs()


def running_jobs():
  """Lists all currently executing jobs.

  Returns:
      A list of dictionaries of jobs where state.running is True.
  """
  return job_manager.running_jobs()


def run_job_now(job_id: str):
  """Manually triggers a job to run immediately in a background thread.

  Args:
      job_id: The unique identifier of the job to run.

  Returns:
      A dictionary representation of the updated job state.
  """
  return job_manager.run_now(job_id)