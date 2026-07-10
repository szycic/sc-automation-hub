from sc_automation_hub.notion_api import get_recurring_tasks_to_update, update_task_due_date

def update_recurring_tasks():
  """Update all recurring tasks that need to be updated."""
  
  print("Checking for recurring tasks to update...")
  tasks_to_update = get_recurring_tasks_to_update()
  updated_count = 0
  failed_tasks = []
  
  if tasks_to_update:
    for task in tasks_to_update:
      try:
        update_task_due_date(task)
        updated_count += 1
      except Exception as exc:
        task_id = task.get("id", "unknown")
        failed_tasks.append({"id": task_id, "error": str(exc)})
        print(f"Failed to update task {task_id}: {exc}")

    print(f"Updated {updated_count} recurring {'task' if updated_count == 1 else 'tasks'}.")
    if failed_tasks:
      print(f"Skipped {len(failed_tasks)} task(s) with errors.")
  else:
    print("No recurring tasks to update.")

  return {
    "fetched": len(tasks_to_update),
    "updated": updated_count,
    "failed": failed_tasks,
  }