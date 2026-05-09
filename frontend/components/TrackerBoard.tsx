"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { StatCard } from "@/components/StatCard";
import { TrackingActions } from "@/components/TrackingActions";
import { ApplicationEvent, Job, getTrackerJobs, getTrackerSummary } from "@/lib/api";

type TrackerSummaryState = Awaited<ReturnType<typeof getTrackerSummary>>;

const STATUS_GROUPS = [
  { title: "Found / Saved", statuses: ["found", "saved", "verified_open"] },
  { title: "Packet Ready", statuses: ["packet_ready"] },
  { title: "Application Opened", statuses: ["application_opened", "autofill_started"] },
  { title: "Autofill Diagnostics", statuses: ["autofill_completed"] },
  { title: "Applied", statuses: ["applied_manual"] },
  { title: "Follow Up", statuses: ["follow_up"] },
  { title: "Interview", statuses: ["interview"] },
  { title: "Rejected", statuses: ["rejected"] },
  { title: "Offer", statuses: ["offer"] },
  { title: "Closed / Withdrawn", statuses: ["withdrawn", "closed_before_apply"] },
];

function getStatusClassName(status: string) {
  return `status-tag status-${status.replace(/_/g, "-")}`;
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "Not set";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function formatTimelineEvent(event: ApplicationEvent) {
  if (event.old_status && event.new_status && event.old_status !== event.new_status) {
    return `${event.event_type} (${event.old_status} → ${event.new_status})`;
  }
  return event.event_type;
}

export function TrackerBoard() {
  const [summary, setSummary] = useState<TrackerSummaryState | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadTrackerData(searchValue = search) {
    setLoading(true);
    try {
      const [summaryResponse, jobsResponse] = await Promise.all([
        getTrackerSummary(),
        getTrackerJobs(searchValue.trim() ? { search: searchValue.trim() } : undefined),
      ]);
      setSummary(summaryResponse);
      setJobs(jobsResponse);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load tracker data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTrackerData();
  }, []);

  const groupedJobs = useMemo(() => {
    return STATUS_GROUPS.map((group) => ({
      ...group,
      jobs: jobs.filter((job) => group.statuses.includes(job.application_status)),
    }));
  }, [jobs]);

  function handleJobUpdated(updatedJob: Job) {
    setJobs((currentJobs) => currentJobs.map((job) => (job.id === updatedJob.id ? updatedJob : job)));
    void loadTrackerData();
  }

  return (
    <>
      <section className="panel">
        <div className="section-title">
          <h2>Tracker Overview</h2>
          <span className="status-tag">Stage 8</span>
        </div>
        <p className="subtle">
          Stage 8 tracks the application workflow and now adds browser autofill assistance. CareerAgent still does not
          submit applications and still stops before any final submit action.
        </p>
        <div className="filter-row">
          <label className="field-group">
            <span>Search jobs</span>
            <input
              className="input"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search company, title, location, or notes"
            />
          </label>
          <div className="button-row">
            <button className="button secondary" type="button" onClick={() => void loadTrackerData()}>
              Refresh Tracker
            </button>
          </div>
        </div>
        {message ? <p className="message success">{message}</p> : null}
        {error ? <p className="message error">{error}</p> : null}
      </section>

      <section className="stats-grid">
        <StatCard label="Total Jobs" value={summary?.total_jobs ?? (loading ? "..." : 0)} hint="All tracked jobs in PostgreSQL." />
        <StatCard label="Packet Ready" value={summary?.packet_ready_count ?? (loading ? "..." : 0)} hint="Jobs with a generated packet ready to review." />
        <StatCard
          label="Application Opened"
          value={summary?.application_opened_count ?? (loading ? "..." : 0)}
          hint="Jobs whose application links were opened through CareerAgent."
        />
        <StatCard label="Applied" value={summary?.applied_count ?? (loading ? "..." : 0)} hint="Jobs manually marked as submitted." />
        <StatCard label="Follow Up" value={summary?.follow_up_count ?? (loading ? "..." : 0)} hint="Jobs with a pending follow-up." />
        <StatCard label="Interview" value={summary?.interview_count ?? (loading ? "..." : 0)} hint="Jobs that reached an interview or recruiter response stage." />
        <StatCard label="Rejected" value={summary?.rejected_count ?? (loading ? "..." : 0)} hint="Jobs marked as rejected." />
        <StatCard label="Offer" value={summary?.offer_count ?? (loading ? "..." : 0)} hint="Jobs marked as offers." />
      </section>

      <section className="tracker-columns">
        {groupedJobs.map((group) => (
          <article className="panel" key={group.title}>
            <div className="section-title">
              <h2>{group.title}</h2>
              <span className="subtle">{group.jobs.length}</span>
            </div>
            {group.jobs.length === 0 ? (
              <p className="subtle">No jobs in this stage right now.</p>
            ) : (
              <div className="tracker-job-list">
                {group.jobs.map((job) => (
                  <article className="tracker-job-card" key={job.id}>
                    <div className="section-title">
                      <div>
                        <h3>
                          <Link href={`/jobs/${job.id}`} className="job-link">
                            {job.title}
                          </Link>
                        </h3>
                        <p className="subtle">
                          {job.company} • {job.location}
                        </p>
                      </div>
                      <span className={getStatusClassName(job.application_status)}>{job.application_status}</span>
                    </div>
                    <dl className="key-value compact-key-value">
                      <dt>Priority</dt>
                      <dd>{job.overall_priority_score.toFixed(1)}</dd>
                      <dt>Verification</dt>
                      <dd>{job.verification_status}</dd>
                      <dt>Follow Up</dt>
                      <dd>{formatDateTime(job.follow_up_at)}</dd>
                    </dl>
                    {job.next_action ? <p className="subtle">Next action: {job.next_action}</p> : null}
                    <div className="button-row">
                      <Link href={`/jobs/${job.id}`} className="button secondary compact">
                        View Job
                      </Link>
                      {job.url.trim() ? (
                        <Link href={`/autofill?jobId=${job.id}`} className="button secondary compact">
                          Start Autofill
                        </Link>
                      ) : null}
                    </div>
                    <TrackingActions
                      job={job}
                      compact
                      onJobUpdated={handleJobUpdated}
                      onMessage={setMessage}
                      onError={setError}
                    />
                  </article>
                ))}
              </div>
            )}
          </article>
        ))}
      </section>

      <section className="panel-grid">
        <article className="panel">
          <div className="section-title">
            <h2>Upcoming Follow-Ups</h2>
            <span className="subtle">{summary?.upcoming_follow_ups.length ?? 0}</span>
          </div>
          {summary && summary.upcoming_follow_ups.length > 0 ? (
            <div className="timeline-list">
              {summary.upcoming_follow_ups.map((job) => (
                <div className="timeline-item" key={job.id}>
                  <strong>
                    <Link href={`/jobs/${job.id}`} className="job-link">
                      {job.title}
                    </Link>
                  </strong>
                  <p className="subtle">
                    {job.company} • {formatDateTime(job.follow_up_at)}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="subtle">No follow-ups are scheduled yet.</p>
          )}
        </article>

        <article className="panel">
          <div className="section-title">
            <h2>Recent Activity</h2>
            <span className="subtle">{summary?.recent_events.length ?? 0}</span>
          </div>
          {summary && summary.recent_events.length > 0 ? (
            <div className="timeline-list">
              {summary.recent_events.map((event) => (
                <div className="timeline-item" key={event.id}>
                  <strong>{formatTimelineEvent(event)}</strong>
                  <p className="subtle">
                    {event.job ? `${event.job.company} • ${event.job.title}` : `Job #${event.job_id}`} •{" "}
                    {formatDateTime(event.event_time)}
                  </p>
                  {event.notes ? <p className="subtle">{event.notes}</p> : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="subtle">No tracker events yet.</p>
          )}
        </article>
      </section>
    </>
  );
}
