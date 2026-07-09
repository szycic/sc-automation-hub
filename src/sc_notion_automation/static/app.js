const jobsEndpoint = window.jobsEndpoint || "/api/v1/jobs";

function formatDateTime(value) {
  if (!value) {
    return "--";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) {
    return "--";
  }

  return `${seconds.toFixed(2)}s`;
}

function buildStatus(job) {
  if (job.running) {
    return ["running", "Running"];
  }

  if (job.last_status === "error") {
    return ["error", "Error"];
  }

  if (job.last_status === "success") {
    return ["success", "Success"];
  }

  return ["idle", "Idle"];
}

function renderJobs(payload) {
  const jobs = payload.jobs || [];
  const rows = jobs.map((job) => {
    const [statusClass, statusLabel] = buildStatus(job);
    const resultText = job.last_result || job.last_error || "--";
    const disabled = job.running ? "disabled" : "";

    return `
      <tr>
        <td>
          <div class="job-title">
            <strong>${job.label}</strong>
            <div class="job-description">${job.description}</div>
          </div>
        </td>
        <td>
          <span class="status ${statusClass}">${statusLabel}</span>
          <div class="muted" style="margin-top: 8px;">${job.running ? "Currently executing" : "Ready"}</div>
        </td>
        <td>
          Every ${job.interval_minutes} minute${job.interval_minutes === 1 ? "" : "s"}
          <div class="muted" style="margin-top: 8px;">Next: ${formatDateTime(job.next_run_time)}</div>
        </td>
        <td>
          <div>Started: ${formatDateTime(job.last_started_at)}</div>
          <div class="muted" style="margin-top: 8px;">Finished: ${formatDateTime(job.last_finished_at)}</div>
          <div class="muted" style="margin-top: 8px;">Duration: ${formatDuration(job.last_duration_seconds)}</div>
        </td>
        <td>
          <div>Trigger: ${job.last_trigger || "--"}</div>
          <div class="muted" style="margin-top: 8px;">Manual runs: ${job.manual_run_count} | Scheduled runs: ${job.scheduled_run_count}</div>
          <div class="error-box" style="display: ${job.last_error ? "block" : "none"};">${job.last_error || ""}</div>
          <div class="muted" style="margin-top: 8px;">${resultText}</div>
        </td>
        <td>
          <button class="button secondary" ${disabled} onclick="runJob('${job.job_id}')">Run now</button>
        </td>
      </tr>
    `;
  }).join("");

  document.getElementById("job-rows").innerHTML = rows || `
    <tr>
      <td colspan="6" class="muted">No jobs registered.</td>
    </tr>
  `;

  document.getElementById("running-count").textContent = String((payload.running_jobs || []).length);
  document.getElementById("job-count").textContent = String(jobs.length);
  document.getElementById("refresh-time").textContent = new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date());
  document.getElementById("summary-line").textContent = `${jobs.length} job${jobs.length === 1 ? "" : "s"} loaded.`;
  document.getElementById("connection-state").textContent = "Connected";
}

async function refreshJobs() {
  try {
    const response = await fetch(jobsEndpoint, { headers: { "Accept": "application/json" } });
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const payload = await response.json();
    renderJobs(payload);
  } catch (error) {
    document.getElementById("connection-state").textContent = `Offline: ${error.message}`;
    document.getElementById("summary-line").textContent = "Unable to load jobs right now.";
  }
}

async function runJob(jobId) {
  const response = await fetch(`/api/v1/jobs/${jobId}/run`, {
    method: "POST",
    headers: { "Accept": "application/json" },
  });

  if (!response.ok) {
    const payload = await response.json();
    alert(payload.detail || "Unable to trigger the job.");
    return;
  }

  await refreshJobs();
}

async function runAllJobs() {
  const response = await fetch(jobsEndpoint, { headers: { "Accept": "application/json" } });
  if (!response.ok) {
    alert("Unable to load jobs.");
    return;
  }

  const payload = await response.json();
  for (const job of payload.jobs || []) {
    if (!job.running) {
      await runJob(job.job_id);
    }
  }
}

refreshJobs();
setInterval(refreshJobs, 5000);