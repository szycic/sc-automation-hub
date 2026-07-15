from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from threading import Lock, Thread
from typing import Any, Callable
from apscheduler.schedulers.background import BackgroundScheduler


Runner = Callable[[], Any]


@dataclass(frozen=True)
class JobDefinition:
  job_id: str
  label: str
  description: str
  interval_minutes: int | None
  runner: Runner


@dataclass
class JobState:
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
  def __init__(self):
    self.scheduler = BackgroundScheduler()
    self._definitions: dict[str, JobDefinition] = {}
    self._states: dict[str, JobState] = {}
    self._locks: dict[str, Lock] = {}
    self._started = False

  def register_job(self, definition: JobDefinition):
    if self._started:
      raise RuntimeError("Jobs must be registered before the scheduler starts.")

    if definition.job_id in self._definitions:
      raise ValueError(f"Job '{definition.job_id}' is already registered.")

    self._definitions[definition.job_id] = definition
    self._states[definition.job_id] = JobState()
    self._locks[definition.job_id] = Lock()

  def start(self):
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
    if self.scheduler.running:
      self.scheduler.shutdown(wait=False)
    self._started = False

  def run_now(self, job_id: str):
    definition = self._get_definition(job_id)
    lock = self._locks[job_id]

    if not lock.acquire(blocking=False):
      raise RuntimeError(f"Job '{definition.label}' is already running.")

    self._begin_run(job_id, "manual")

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
    lock = self._locks[job_id]

    if not lock.acquire(blocking=False):
      return

    self._begin_run(job_id, trigger_source)
    self._run_job_with_acquired_lock(job_id=job_id, trigger_source=trigger_source, lock=lock)

  def _run_job_with_acquired_lock(self, job_id: str, trigger_source: str, lock: Lock):
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

  def _format_result(self, result: Any):
    if result is None:
      return None

    return str(result)

  def _get_definition(self, job_id: str):
    if job_id not in self._definitions:
      raise KeyError(job_id)

    return self._definitions[job_id]

  def get_job(self, job_id: str):
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

  def list_jobs(self):
    return [self.get_job(job_id) for job_id in self._definitions]

  def running_jobs(self):
    return [job for job in self.list_jobs() if job["running"]]

  @staticmethod
  def _serialize_datetime(value: datetime | None):
    if value is None:
      return None

    return value.isoformat()

  @staticmethod
  def _now():
    return datetime.now().astimezone()