"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AutofillControls } from "@/components/AutofillControls";
import {
  type AutofillSafety,
  type AutofillSession,
  type AutofillStatus,
  type Job,
  closeAutofillSession,
  getAutofillSessions,
  getTrackerJobs,
  importJob,
  updateJob,
} from "@/lib/api";

type AutofillManagerProps = {
  status: AutofillStatus;
  safety: AutofillSafety;
  initialJobId?: number | null;
};

const LOCAL_TEST_FORM_PATH = "/test-application-form";
const LOCAL_TEST_JOB_COMPANY = "CareerAgent Test Company";
const LOCAL_TEST_JOB_TITLE = "Test Application Form";

function localTestFormUrl() {
  if (typeof window === "undefined") {
    return `http://localhost:3000${LOCAL_TEST_FORM_PATH}`;
  }
  return `${window.location.origin}${LOCAL_TEST_FORM_PATH}`;
}

function isLocalTestJob(job: Job) {
  return job.source === "local_test" || job.url.endsWith(LOCAL_TEST_FORM_PATH);
}

export function AutofillManager({ status, safety, initialJobId = null }: AutofillManagerProps) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [sessionMessage, setSessionMessage] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [activeSessions, setActiveSessions] = useState<AutofillSession[]>(status.active_sessions || []);
  const [closingSessionId, setClosingSessionId] = useState<string | null>(null);
  const [testJobBusy, setTestJobBusy] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(initialJobId);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getTrackerJobs();
      const jobsWithUrls = response.filter((job) => Boolean(job.url.trim()));
      setJobs(jobsWithUrls);
      setSelectedJobId((current) => {
        if (current && jobsWithUrls.some((job) => job.id === current)) {
          return current;
        }
        if (initialJobId && jobsWithUrls.some((job) => job.id === initialJobId)) {
          return initialJobId;
        }
        return jobsWithUrls[0]?.id ?? null;
      });
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load jobs for autofill.");
    } finally {
      setLoading(false);
    }
  }, [initialJobId]);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  const loadSessions = useCallback(async () => {
    try {
      const sessions = await getAutofillSessions();
      setActiveSessions(sessions);
      setSessionError(null);
    } catch (loadError) {
      setSessionError(loadError instanceof Error ? loadError.message : "Failed to load active autofill sessions.");
    }
  }, []);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId) ?? null,
    [jobs, selectedJobId],
  );
  const headlessMode = status.configured_browser_mode === "headless";

  async function handleUseLocalTestForm() {
    setTestJobBusy(true);
    setError(null);
    setMessage(null);

    try {
      const allJobs = await getTrackerJobs();
      const existingJob = allJobs.find(isLocalTestJob);
      const url = localTestFormUrl();
      let testJob = existingJob ?? null;

      if (!testJob) {
        testJob = await importJob({
          input_type: "description",
          content: [
            `Company: ${LOCAL_TEST_JOB_COMPANY}`,
            `Title: ${LOCAL_TEST_JOB_TITLE}`,
            "Location: Localhost",
            "Employment Type: Test",
            "",
            "Responsibilities:",
            "- Provide a safe local HTML form for CareerAgent autofill testing.",
            "",
            "Requirements:",
            "- This is not a real job.",
          ].join("\n"),
          source: "local_test",
        });
      }

      if (testJob.url !== url || testJob.company !== LOCAL_TEST_JOB_COMPANY || testJob.title !== LOCAL_TEST_JOB_TITLE) {
        testJob = await updateJob(testJob.id, {
          company: LOCAL_TEST_JOB_COMPANY,
          title: LOCAL_TEST_JOB_TITLE,
          location: "Localhost",
          url,
          source: "local_test",
          application_status: "saved",
        });
      }

      await loadJobs();
      setSelectedJobId(testJob.id);
      setMessage("Local test form selected. Use Fill Application in visible mode, or run the advanced headless diagnostic.");
    } catch (testJobError) {
      setError(testJobError instanceof Error ? testJobError.message : "Failed to prepare the local test form job.");
    } finally {
      setTestJobBusy(false);
    }
  }

  async function handleCloseSession(sessionId: string) {
    setClosingSessionId(sessionId);
    setSessionMessage(null);
    setSessionError(null);
    try {
      await closeAutofillSession(sessionId);
      setSessionMessage("Autofill browser session closed.");
      await loadSessions();
    } catch (closeError) {
      setSessionError(closeError instanceof Error ? closeError.message : "Failed to close the autofill session.");
    } finally {
      setClosingSessionId(null);
    }
  }

  async function handleAutofillUpdate() {
    await Promise.all([loadJobs(), loadSessions()]);
  }

  return (
    <>
      <section className="panel">
        <div className="section-title">
          <h2>Job + Packet Selection</h2>
          <span className="status-tag">{status.browser_mode}</span>
        </div>
        <p className="subtle">
          Open the application manually or let CareerAgent fill a visible browser session. CareerAgent never submits.
        </p>
        <p className="subtle">
          Use Open in Browser for manual applications. Use Fill Application when visible browser autofill is available.
          CareerAgent fills safe fields, stops before submit, and leaves the browser open for you.
        </p>

        <div className="filter-row">
          <label className="field-group">
            <span>Job with application URL</span>
            <select
              className="input"
              value={selectedJobId ?? ""}
              onChange={(event) => setSelectedJobId(event.target.value ? Number(event.target.value) : null)}
              disabled={loading}
            >
              <option value="">Select a job</option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  #{job.id} • {job.company} • {job.title}
                </option>
              ))}
            </select>
          </label>
          <button className="button secondary" type="button" onClick={() => void loadJobs()}>
            Refresh Jobs
          </button>
        </div>

        <details className="details-block">
          <summary>Test utilities</summary>
          <p className="subtle">
            The local test form is a fake application page for checking detection and final-submit blocking.
          </p>
          <button className="button secondary compact" type="button" onClick={() => void handleUseLocalTestForm()} disabled={testJobBusy || loading}>
            {testJobBusy ? "Preparing Test Form..." : "Use Local Test Form"}
          </button>
        </details>

        {message ? <p className="message success">{message}</p> : null}
        {error ? <p className="message error">{error}</p> : null}
        {loading ? <p className="subtle">Loading jobs with saved application URLs...</p> : null}
        {!loading && jobs.length === 0 ? (
          <p className="subtle">
            No jobs with saved application URLs are available yet. Import a job with a URL first, then generate a packet
            before starting autofill.
          </p>
        ) : null}
        {selectedJob ? (
          <AutofillControls
            key={selectedJob.id}
            job={selectedJob}
            configuredBrowserMode={status.configured_browser_mode}
            visibleBrowserAvailable={status.visible_autofill_available}
            onAutofillComplete={handleAutofillUpdate}
          />
        ) : null}
      </section>

      <section className="panel">
        <div className="section-title">
          <h2>Active Autofill Sessions</h2>
          <button className="button secondary compact" type="button" onClick={() => void loadSessions()}>
            Refresh Sessions
          </button>
        </div>
        {sessionMessage ? <p className="message success">{sessionMessage}</p> : null}
        {sessionError ? <p className="message error">{sessionError}</p> : null}
        {activeSessions.length === 0 ? (
          <p className="subtle">No visible Chromium sessions are active.</p>
        ) : (
          <div className="timeline-list">
            {activeSessions.map((session) => (
              <div className="timeline-item" key={session.session_id}>
                <strong>Job #{session.job_id}</strong>
                <p className="subtle">{session.opened_url}</p>
                <p className="subtle">
                  Session {session.session_id} • {session.mode} • {session.created_at}
                </p>
                <button
                  className="button secondary compact"
                  type="button"
                  onClick={() => void handleCloseSession(session.session_id)}
                  disabled={closingSessionId !== null}
                >
                  {closingSessionId === session.session_id ? "Closing..." : "Close Session"}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      <details className="details-block">
        <summary>Environment details</summary>
        <section className="panel-grid">
          <article className="panel">
            <h2>Autofill Environment</h2>
            <dl className="key-value compact-key-value">
              <dt>Stage</dt>
              <dd>{status.stage}</dd>
              <dt>Browser Mode</dt>
              <dd>{headlessMode ? "Headless Docker Mode" : "Visible Local Mode"}</dd>
              <dt>Visible Autofill</dt>
              <dd>{status.visible_autofill_available ? "Available" : "Unavailable"}</dd>
              <dt>Can Continue</dt>
              <dd>{status.can_continue_from_autofill ? "Yes" : "No"}</dd>
              <dt>Recommended Action</dt>
              <dd>{status.recommended_user_action === "fill_application" ? "Fill Application" : "Open in Browser"}</dd>
              <dt>Playwright</dt>
              <dd>{status.playwright_installed ? "Installed" : "Missing"}</dd>
              <dt>Chromium</dt>
              <dd>{status.chromium_installed ? "Installed" : "Missing"}</dd>
              <dt>Headed Display</dt>
              <dd>{status.headed_display_available ? "Available" : "Not available"}</dd>
              <dt>Slow Motion</dt>
              <dd>{status.playwright_slow_mo_ms}ms</dd>
            </dl>
            <p className="subtle">{status.message}</p>
            {status.browser_mode === "headless" ? (
              <p className="message warning">
                CareerAgent is still connected to a headless backend. Stop the Docker backend and make sure the local
                backend is running on localhost:8000 with PLAYWRIGHT_HEADLESS=false.
              </p>
            ) : null}
            <p className="subtle">{status.environment_note}</p>
            <dl className="key-value compact-key-value">
              <dt>Backend Runtime</dt>
              <dd>{status.backend_runtime}</dd>
              <dt>Python</dt>
              <dd>{status.python_executable}</dd>
              <dt>Database Host</dt>
              <dd>{status.database_host_hint}</dd>
              <dt>Install Hint</dt>
              <dd>{status.playwright_install_hint}</dd>
            </dl>
          </article>

          <article className="panel">
            <h2>Safety Rules</h2>
            {safety.safety_rules.length > 0 ? (
              <ul className="list">
                {safety.safety_rules.map((rule) => (
                  <li key={rule}>{rule}</li>
                ))}
              </ul>
            ) : (
              <p className="subtle">Safety policy is unavailable right now.</p>
            )}
          </article>
        </section>
      </details>

      {status.recent_sessions.length > 0 ? (
        <section className="panel">
          <h2>Recent Autofill Sessions</h2>
          <div className="timeline-list">
            {status.recent_sessions.map((session, index) => (
              <div className="timeline-item" key={`session-${index}`}>
                <strong>
                  Job #{String(session.job_id || "?")} • {String(session.status || "unknown")}
                </strong>
                <p className="subtle">
                  Filled {String(session.fields_filled || 0)} of {String(session.fields_detected || 0)} detected fields.
                </p>
                <p className="subtle">Manual review was required. CareerAgent did not submit the application.</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}
