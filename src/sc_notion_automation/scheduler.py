from sc_notion_automation.job_service import JobDefinition, JobManager
from sc_notion_automation.tasks import update_recurring_tasks


job_manager = JobManager()
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
  print("Starting the scheduler...")
  job_manager.start()


def stop_scheduler():
  job_manager.stop()


def list_jobs():
  return job_manager.list_jobs()


def running_jobs():
  return job_manager.running_jobs()


def run_job_now(job_id):
  return job_manager.run_now(job_id)