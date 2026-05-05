"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AutofillControls } from "@/components/AutofillControls";
import {
  type AutofillSafety,
  type AutofillStatus,
  type Job,
  getTrackerJobs,
} from "@/lib/api";

type AutofillManagerProps = {
  status: AutofillStatus;
  safety: AutofillSafety;
  initialJobId?: number | null;
};

export function AutofillManager({ status, safety, initialJobId = null }: AutofillManagerProps) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId) ?? null,
    [jobs, selectedJobId],
  );

  return (
    <>
      <section className="warning-panel">
        <h2>Never Auto-Submit</h2>
        <p>{status.message}</p>
        <p>{status.environment_note}</p>
        {status.configured_browser_mode === "headless" ? (
          <p>
            Headless mode does not show a live browser window. CareerAgent will still stop before final actions, and you
            must open the application manually to review and submit.
          </p>
        ) : null}
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>Environment Status</h2>
          <dl className="key-value compact-key-value">
            <dt>Stage</dt>
            <dd>{status.stage}</dd>
            <dt>Playwright Installed</dt>
            <dd>{status.playwright_installed ? "Yes" : "No"}</dd>
            <dt>Chromium Installed</dt>
            <dd>{status.chromium_installed ? "Yes" : "No"}</dd>
            <dt>Browser Mode</dt>
            <dd>{status.configured_browser_mode}</dd>
            <dt>Headed Display Available</dt>
            <dd>{status.headed_display_available ? "Yes" : "No"}</dd>
            <dt>Headed Browser Ready</dt>
            <dd>{status.headed_browser_supported ? "Yes" : "No"}</dd>
            <dt>Xvfb Enabled</dt>
            <dd>{status.playwright_use_xvfb ? "Yes" : "No"}</dd>
            <dt>Slow Motion</dt>
            <dd>{status.playwright_slow_mo_ms}ms</dd>
            <dt>Install Command</dt>
            <dd>{status.install_command}</dd>
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

      <section className="panel">
        <div className="section-title">
          <h2>Start Autofill</h2>
          <span className="status-tag">Stage 8</span>
        </div>
        <p className="subtle">
          Preview the plan first, then start Chromium for the selected job. CareerAgent will fill safe fields only and
          will never click any final submit or apply button.
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
          <div className="button-row">
            <button className="button secondary" type="button" onClick={() => void loadJobs()}>
              Refresh Jobs
            </button>
          </div>
        </div>

        {error ? <p className="message error">{error}</p> : null}
        {loading ? <p className="subtle">Loading jobs with saved application URLs...</p> : null}
        {!loading && jobs.length === 0 ? (
          <p className="subtle">
            No jobs with saved application URLs are available yet. Import a job with a URL first, then generate a packet
            before starting autofill.
          </p>
        ) : null}
        {selectedJob ? <AutofillControls job={selectedJob} onAutofillComplete={loadJobs} /> : null}
      </section>

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
                {session.message ? <p className="subtle">{String(session.message)}</p> : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}
