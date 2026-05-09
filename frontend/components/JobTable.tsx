"use client";

import Link from "next/link";

import { Job } from "@/lib/api";

export type JobNextAction = {
  label: string;
  href: string;
  tone?: "primary" | "secondary";
};

export type JobTableRow = {
  job: Job;
  nextAction: JobNextAction;
  isDuplicate: boolean;
  duplicateOfJobId: number | null;
  isTestJob: boolean;
  activeDisplayStatus: string;
};

type JobTableProps = {
  rows: JobTableRow[];
  onViewDescription: (job: Job) => void;
};

function formatDate(value: string | null) {
  return value || "-";
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

function formatStatusLabel(value: string) {
  return value.replace(/_/g, " ");
}

function formatAvailability(job: Job) {
  if (job.verification_status === "unknown") {
    return "Not verified";
  }
  return `${formatStatusLabel(job.verification_status)} (${formatScore(job.verification_score)})`;
}

export function JobTable({ rows, onViewDescription }: JobTableProps) {
  if (rows.length === 0) {
    return <p className="subtle">No saved jobs match the current filters.</p>;
  }

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Company</th>
            <th>Title</th>
            <th>Description</th>
            <th>Location</th>
            <th>Role</th>
            <th>Status</th>
            <th>Match</th>
            <th>Priority</th>
            <th>Availability</th>
            <th>Next Action</th>
            <th>Open</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ job, nextAction, isDuplicate, duplicateOfJobId, isTestJob, activeDisplayStatus }) => {
            return (
              <tr key={job.id}>
                <td>
                  <div className="status-stack">
                    <span>{job.company}</span>
                    {isDuplicate && duplicateOfJobId ? (
                      <span className="status-tag status-unknown">Possible duplicate of #{duplicateOfJobId}</span>
                    ) : null}
                    {isTestJob ? <span className="status-tag status-unknown">Test/demo</span> : null}
                  </div>
                </td>
                <td>
                  <Link href={`/jobs/${job.id}`} className="job-link">
                    <strong>{job.title}</strong>
                  </Link>
                </td>
                <td>
                  <button
                    className="button secondary compact"
                    type="button"
                    onClick={() => onViewDescription(job)}
                  >
                    {job.job_description?.trim() ? "View" : "Missing"}
                  </button>
                </td>
                <td>{job.location}</td>
                <td>{job.role_category || "Other"}</td>
                <td>
                  <div className="status-stack">
                    <span className={getStatusClassName(job.application_status)}>{formatStatusLabel(activeDisplayStatus)}</span>
                    {activeDisplayStatus !== job.application_status ? (
                      <span className="subtle">Diagnostic result; not applied.</span>
                    ) : null}
                    {job.follow_up_at ? <span className="subtle">Follow up: {formatDate(job.follow_up_at)}</span> : null}
                  </div>
                </td>
                <td>
                  <div className="status-stack">
                    <span className="score">{formatScore(job.resume_match_score)}</span>
                    <span className="subtle">{job.scoring_status === "scored" ? "Scored" : "Needs scoring"}</span>
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
                    <span className={getStatusClassName(job.verification_status)}>{formatAvailability(job)}</span>
                    <span className="subtle">Checked: {formatDate(job.last_checked_date)}</span>
                  </div>
                </td>
                <td>
                  <Link
                    href={nextAction.href}
                    className={nextAction.tone === "primary" ? "button compact" : "button secondary compact"}
                  >
                    {nextAction.label}
                  </Link>
                </td>
                <td>
                  <Link href={`/jobs/${job.id}`} className="button secondary compact">
                    Open Job
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
