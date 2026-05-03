"use client";

import Link from "next/link";

import { Job } from "@/lib/api";
import { TrackingActions } from "@/components/TrackingActions";

type JobTableProps = {
  jobs: Job[];
  onVerify?: (job: Job) => Promise<void> | void;
  onScore?: (job: Job) => Promise<void> | void;
  onJobUpdated?: (job: Job) => void;
  onTrackerMessage?: (message: string | null) => void;
  onTrackerError?: (message: string | null) => void;
  verifyingJobId?: number | null;
  scoringJobId?: number | null;
};

function formatDate(value: string | null) {
  return value || "-";
}

function formatSource(value: string) {
  return value === "sample_seed" ? "sample/demo" : value;
}

function formatScore(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "-";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function getStatusClassName(status: string) {
  return `status-tag status-${status.replace(/_/g, "-")}`;
}

export function JobTable({
  jobs,
  onVerify,
  onScore,
  onJobUpdated,
  onTrackerMessage,
  onTrackerError,
  verifyingJobId,
  scoringJobId,
}: JobTableProps) {
  if (jobs.length === 0) {
    return <p className="subtle">No jobs saved yet. Import a pasted description or URL to create your first record.</p>;
  }

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Company</th>
            <th>Title</th>
            <th>Location</th>
            <th>Role Category</th>
            <th>Verification</th>
            <th>Resume Match</th>
            <th>Priority</th>
            <th>Scoring</th>
            <th>Application Status</th>
            <th>Source</th>
            <th>Actions</th>
            <th>Agent Workflow</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => {
            const verifying = verifyingJobId === job.id;
            const scoring = scoringJobId === job.id;
            const hasUrl = Boolean(job.url?.trim());

            return (
              <tr key={job.id}>
                <td>{job.company}</td>
                <td>
                  <Link href={`/jobs/${job.id}`} className="job-link">
                    <strong>{job.title}</strong>
                  </Link>
                </td>
                <td>{job.location}</td>
                <td>{job.role_category || "Other"}</td>
                <td>
                  <div className="status-stack">
                    <span className={getStatusClassName(job.verification_status)}>{job.verification_status}</span>
                    <span className="subtle score">Open: {formatScore(job.verification_score)}</span>
                    <span className="subtle score">Closed risk: {formatScore(job.likely_closed_score)}</span>
                    <span className="subtle">Checked: {formatDate(job.last_checked_date)}</span>
                  </div>
                </td>
                <td>
                  <div className="status-stack">
                    <span className="score">{formatScore(job.resume_match_score)}</span>
                    <span className="subtle">Skill: {formatScore(job.skill_match_score)}</span>
                    <span className="subtle">Role: {formatScore(job.role_match_score)}</span>
                  </div>
                </td>
                <td>
                  <div className="status-stack">
                    <span className="score">{formatScore(job.overall_priority_score)}</span>
                    <span className="subtle">Freshness: {formatScore(job.freshness_score)}</span>
                  </div>
                </td>
                <td>
                  <div className="status-stack">
                    <span className={getStatusClassName(job.scoring_status === "scored" ? "open" : "unknown")}>
                      {job.scoring_status}
                    </span>
                    <span className="subtle">Scored: {formatDate(job.scored_at)}</span>
                  </div>
                </td>
                <td>
                  <div className="status-stack">
                    <span className={getStatusClassName(job.application_status)}>{job.application_status}</span>
                    {job.follow_up_at ? <span className="subtle">Follow up: {formatDate(job.follow_up_at)}</span> : null}
                  </div>
                </td>
                <td>{formatSource(job.source)}</td>
                <td>
                  <div className="action-stack">
                    {hasUrl ? (
                      <button
                        className="button secondary compact"
                        type="button"
                        onClick={() => onVerify?.(job)}
                        disabled={verifying || !onVerify}
                      >
                        {verifying ? "Verifying..." : "Verify"}
                      </button>
                    ) : (
                      <span className="subtle">No URL</span>
                    )}
                    <button
                      className="button compact"
                      type="button"
                      onClick={() => onScore?.(job)}
                      disabled={scoring || !onScore}
                    >
                      {scoring ? "Scoring..." : "Score"}
                    </button>
                    <Link href="/tracker" className="button secondary compact">
                      Tracker
                    </Link>
                  </div>
                  <TrackingActions
                    job={job}
                    compact
                    onJobUpdated={onJobUpdated}
                    onMessage={onTrackerMessage}
                    onError={onTrackerError}
                  />
                </td>
                <td>
                  <div className="planned-action-stack">
                    <span className="status-tag status-open">Verify still hiring: Stage 4 live</span>
                    <span className="status-tag status-probably-open">Score fit: Stage 5 live</span>
                    <span className={job.application_status === "packet_ready" ? "status-tag status-packet-ready" : "status-tag status-open"}>
                      {job.application_status === "packet_ready" ? "Packet ready: Stage 6 live" : "Generate packet: Stage 6 live"}
                    </span>
                    <span className="status-tag status-open">Tracker logging: Stage 7 live</span>
                    <span className="planned-chip">Autofill application: planned Stage 8</span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
