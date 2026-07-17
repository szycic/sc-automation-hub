"""Background Job Execution Service.

This module implements the state tracking and execution manager for background tasks.
It wraps APScheduler's `BackgroundScheduler` to support scheduled recurring tasks,
and uses standard python `threading.Thread` and `threading.Lock` primitives to safely
trigger background tasks manually via web endpoints without race conditions or dual-running.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from threading import Lock, Thread
from typing import Any, Callable
from apscheduler.schedulers.background import BackgroundScheduler


# Type alias for a parameterless callable that executes a background task
Runner = Callable[[], Any]


@dataclass(frozen=True)
class JobDefinition:
  """Static configuration definition for a registered background job.

  Attributes:
      job_id: Unique string identifier for the job.
      label: Human-readable short name for the job.
      description: Explanatory description of what the job does.
      interval_minutes: Periodic interval in minutes to run the job,
          or None if the job is only triggered manually.
      runner: The execution handler function.
  """
  job_id: str
  label: str
  description: str
  interval_minutes: int | None
  runner: Runner


@dataclass
class JobState:
  """Mutable dynamic execution and performance tracking state for a job.

  Attributes:
      running: Flag indicating if the job is currently executing.
      last_trigger: The source that started the last run ('manual' or 'scheduled').
      last_started_at: Timestamp when the last run started.
      last_finished_at: Timestamp when the last run completed.
      last_duration_seconds: Computational elapsed duration in seconds of the last run.
      last_status: Outcome status of the last run ('running', 'success', or 'error').
      last_result: Formatted string result returned by the runner upon success.
      last_error: Error message string if the runner raised an exception.
      manual_run_count: Total cumulative manually triggered runs.
      scheduled_run_count: Total cumulative scheduler triggered runs.
  """
  running: bool = False
  last_trigger: str | None = None
  last_started_at: datetime | None = None
  last_finished_at: datetime | None = None
  last_duration_seconds: float | None = None
  last_status: str | None = None
  last_result: str | None = None
  last_error: str | None = None
  manual_run_count: int = 0
  scheduled_run_count: int = 0


class JobManager:
  """Scheduler wrapper managing job configuration, execution safety, and execution states.

  Synchronizes execution through re-entrant checks (mutex locks per job) to avoid
  running the same job multiple times concurrently.
  """

  def __init__(self):
    """Initializes the JobManager with an unstarted BackgroundScheduler."""
    self.scheduler = BackgroundScheduler()
    self._definitions: dict[str, JobDefinition] = {}
    self._states: dict[str, JobState] = {}
    self._locks: dict[str, Lock] = {}
    self._started = False

  def register_job(self, definition: JobDefinition):
    """Registers a new job definition with the manager.

    Args:
        definition: The JobDefinition instance specifying config and execution runner.

    Raises:
        RuntimeError: If attempting to register a job after starting the scheduler.
        ValueError: If a job with the same job_id has already been registered.
    """
    if self._started:
      raise RuntimeError("Jobs must be registered before the scheduler starts.")

    if definition.job_id in self._definitions:
      raise ValueError(f"Job '{definition.job_id}' is already registered.")

    self._definitions[definition.job_id] = definition
    self._states[definition.job_id] = JobState()
    self._locks[definition.job_id] = Lock()

  def start(self):
    """Starts the background scheduler, scheduling any jobs with periodic intervals."""
    if self._started:
      return

    for definition in self._definitions.values():
      if definition.interval_minutes is not None:
        self.scheduler.add_job(
          self._run_job,
          trigger="interval",
          minutes=definition.interval_minutes,
          id=definition.job_id,
          name=definition.label,
          replace_existing=True,
          max_instances=1,
          coalesce=True,
          misfire_grace_time=30,
          kwargs={
            "job_id": definition.job_id,
            "trigger_source": "scheduled",
          },
        )

    self.scheduler.start()
    self._started = True

  def stop(self):
    """Gracefully shuts down the background scheduler."""
    if self.scheduler.running:
      self.scheduler.shutdown(wait=False)
    self._started = False

  def run_now(self, job_id: str) -> dict[str, Any]:
    """Manually triggers a job execution immediately in a separate background thread.

    Verifies mutex locks first to prevent concurrent execution.

    Args:
        job_id: The ID of the job to run.

    Returns:
        The updated job configuration and state dictionary.

    Raises:
        RuntimeError: If the requested job is currently already running.
        KeyError: If the job_id does not match any registered jobs.
    """
    definition = self._get_definition(job_id)
    lock = self._locks[job_id]

    # Non-blocking lock acquisition check
    if not lock.acquire(blocking=False):
      raise RuntimeError(f"Job '{definition.label}' is already running.")

    # Begin run transition setup
    self._begin_run(job_id, "manual")

    # Run the executor function in a daemon thread so it doesn't block server shutdown
    worker = Thread(
      target=self._run_job_with_acquired_lock,
      kwargs={
        "job_id": job_id,
        "trigger_source": "manual",
        "lock": lock,
      },
      daemon=True,
    )
    worker.start()

    return self.get_job(job_id)

  def _run_job(self, job_id: str, trigger_source: str):
    """Internal scheduler entrypoint for periodic interval tasks.

    Acquires the lock safely before running, skipping if already locked.
    """
    lock = self._locks[job_id]

    if not lock.acquire(blocking=False):
      return

    self._begin_run(job_id, trigger_source)
    self._run_job_with_acquired_lock(job_id=job_id, trigger_source=trigger_source, lock=lock)

  def _run_job_with_acquired_lock(self, job_id: str, trigger_source: str, lock: Lock):
    """Executes the runner callback with lock ownership and handles state updates.

    Ensures the lock is released in a finally block.
    """
    definition = self._definitions[job_id]
    state = self._states[job_id]
    started_at = state.last_started_at or self._now()

    try:
      result = definition.runner()
      state.last_status = "success"
      state.last_result = self._format_result(result)
      state.last_error = None
    except Exception as exc:
      state.last_status = "error"
      state.last_error = str(exc)
      state.last_result = None
    finally:
      finished_at = self._now()
      state.running = False
      state.last_finished_at = finished_at
      state.last_duration_seconds = round((finished_at - started_at).total_seconds(), 3)
      lock.release()

  def _begin_run(self, job_id: str, trigger_source: str):
    """Sets initial execution states before calling the runner."""
    state = self._states[job_id]
    started_at = self._now()
    state.running = True
    state.last_trigger = trigger_source
    state.last_started_at = started_at
    state.last_finished_at = None
    state.last_duration_seconds = None
    state.last_status = "running"
    state.last_error = None

    if trigger_source == "manual":
      state.manual_run_count += 1
    else:
      state.scheduled_run_count += 1

  def _format_result(self, result: Any) -> str | None:
    """Helper method to format raw return values of runners to strings."""
    if result is None:
      return None

    return str(result)

  def _get_definition(self, job_id: str) -> JobDefinition:
    """Retrieves definition, raising KeyError if unregistered."""
    if job_id not in self._definitions:
      raise KeyError(job_id)

    return self._definitions[job_id]

  def get_job(self, job_id: str) -> dict[str, Any]:
    """Prepares and serializes job configuration and current state metrics.

    Args:
        job_id: Unique identifier for the job.

    Returns:
        A dictionary containing state and metadata fields.
    """
    definition = self._get_definition(job_id)
    state = self._states[job_id]
    apscheduler_job = self.scheduler.get_job(job_id)

    return {
      "job_id": definition.job_id,
      "label": definition.label,
      "description": definition.description,
      "interval_minutes": definition.interval_minutes,
      "running": state.running,
      "last_trigger": state.last_trigger,
      "last_started_at": self._serialize_datetime(state.last_started_at),
      "last_finished_at": self._serialize_datetime(state.last_finished_at),
      "last_duration_seconds": state.last_duration_seconds,
      "last_status": state.last_status,
      "last_result": state.last_result,
      "last_error": state.last_error,
      "manual_run_count": state.manual_run_count,
      "scheduled_run_count": state.scheduled_run_count,
      "next_run_time": self._serialize_datetime(getattr(apscheduler_job, "next_run_time", None)),
    }

  def list_jobs(self) -> list[dict[str, Any]]:
    """Lists all registered jobs.

    Returns:
        A list of job dictionary objects.
    """
    return [self.get_job(job_id) for job_id in self._definitions]

  def running_jobs(self) -> list[dict[str, Any]]:
    """Lists only active/currently running jobs.

    Returns:
      A list of job dictionary objects where running is True.
    """
    return [job for job in self.list_jobs() if job["running"]]

  @staticmethod
  def _serialize_datetime(value: datetime | None) -> str | None:
    """Converts a datetime object to an ISO format string."""
    if value is None:
      return None

    return value.isoformat()

  @staticmethod
  def _now() -> datetime:
    """Returns local timezone-aware current datetime."""
    return datetime.now().astimezone()