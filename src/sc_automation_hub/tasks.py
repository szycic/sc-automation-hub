"""Automation Tasks.

This module defines high-level job executors that orchestrate multi-step automation
procedures (e.g. synchronizing task dates).
"""

from sc_automation_hub.notion.primary import (
    get_recurring_tasks_to_update as get_primary_recurring_tasks_to_update,
    update_task_due_date as update_primary_task_due_date,
)
from sc_automation_hub.notion.secondary import (
    get_recurring_tasks_to_update as get_secondary_recurring_tasks_to_update,
    update_task_due_date as update_secondary_task_due_date,
)


def update_recurring_tasks():
  """Updates all recurring primary Notion tasks that currently require synchronization.

  Queries primary Notion for tasks with missing due dates but defined offsets, computes
  new due dates based on planned start dates and offsets, updates those tasks in Notion,
  and reports the aggregate results.

  Returns:
      A dictionary summarizing execution details:
          - fetched (int): Total number of eligible tasks identified.
          - updated (int): Count of successfully updated tasks.
          - failed (list[dict]): Details of tasks that encountered errors during update.
  """
  print("Checking for primary recurring tasks to update...")
  tasks_to_update = get_primary_recurring_tasks_to_update()
  updated_count = 0
  failed_tasks = []
  
  if tasks_to_update:
    # Iterate through all fetched tasks and attempt to compute and update due date
    for task in tasks_to_update:
      try:
        update_primary_task_due_date(task)
        updated_count += 1
      except Exception as exc:
        task_id = task.get("id", "unknown")
        failed_tasks.append({"id": task_id, "error": str(exc)})
        print(f"Failed to update task {task_id}: {exc}")

    print(f"Updated {updated_count} primary recurring {'task' if updated_count == 1 else 'tasks'}.")
    if failed_tasks:
      print(f"Skipped {len(failed_tasks)} task(s) with errors.")
  else:
    print("No primary recurring tasks to update.")

  return {
    "fetched": len(tasks_to_update),
    "updated": updated_count,
    "failed": failed_tasks,
  }


def update_secondary_recurring_tasks():
  """Updates all recurring secondary Notion tasks that currently require synchronization.

  Queries secondary Notion for tasks with missing due dates but defined offsets, computes
  new due dates based on planned start dates and offsets, updates those tasks in Notion,
  and reports the aggregate results.

  Returns:
      A dictionary summarizing execution details:
          - fetched (int): Total number of eligible tasks identified.
          - updated (int): Count of successfully updated tasks.
          - failed (list[dict]): Details of tasks that encountered errors during update.
  """
  print("Checking for secondary recurring tasks to update...")
  tasks_to_update = get_secondary_recurring_tasks_to_update()
  updated_count = 0
  failed_tasks = []
  
  if tasks_to_update:
    # Iterate through all fetched tasks and attempt to compute and update due date
    for task in tasks_to_update:
      try:
        update_secondary_task_due_date(task)
        updated_count += 1
      except Exception as exc:
        task_id = task.get("id", "unknown")
        failed_tasks.append({"id": task_id, "error": str(exc)})
        print(f"Failed to update secondary task {task_id}: {exc}")

    print(f"Updated {updated_count} secondary recurring {'task' if updated_count == 1 else 'tasks'}.")
    if failed_tasks:
      print(f"Skipped {len(failed_tasks)} task(s) with errors.")
  else:
    print("No secondary recurring tasks to update.")

  return {
    "fetched": len(tasks_to_update),
    "updated": updated_count,
    "failed": failed_tasks,
  }


# Aliases for flexible function naming
update_primary_recurring_tasks = update_recurring_tasks
update_recurring_secondary_tasks = update_secondary_recurring_tasks