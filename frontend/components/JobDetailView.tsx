"use client";

import Link from "next/link";

import { Job } from "@/lib/api";

type JobDetailViewProps = {
  initialJob: Job;
};

function formatScore(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function formatYearsExperience(job: Job) {
  if (job.years_experience_min === null && job.years_experience_max === null) return "Not found";
  if (job.years_experience_min !== null && job.years_experience_max !== null) {
    return job.years_experience_min === job.years_experience_max
      ? `${job.years_experience_min}+ years`
      : `${job.years_experience_min} - ${job.years_experience_max} years`;
  }
  if (job.years_experience_min !== null) return `${job.years_experience_min}+ years`;
  return `Up to ${job.years_experience_max} years`;
}

function descriptionText(job: Job) {
  return (job.job_description || "")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/p>/gi, "\n\n")
    .replace(/<[^>]+>/g, "")
    .trim();
}

export function JobDetailView({ initialJob: job }: JobDetailViewProps) {
  const description = descriptionText(job);

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Job Details</span>
        <h1>{job.title}</h1>
        <p className="hero-copy">
          {job.company} • {job.location}
        </p>
        <div className="button-row">
          <Link href={`/apply?jobId=${job.id}`} className="button">
            Apply
          </Link>
          <Link href="/jobs?tab=saved" className="button secondary">
            Back to Jobs
          </Link>
          {job.url ? (
            <a href={job.url} target="_blank" rel="noreferrer" className="button secondary">
              Original Posting
            </a>
          ) : null}
        </div>
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>Overview</h2>
          <dl className="key-value">
            <dt>Company</dt>
            <dd>{job.company}</dd>
            <dt>Title</dt>
            <dd>{job.title}</dd>
            <dt>Location</dt>
            <dd>{job.location}</dd>
            <dt>Role</dt>
            <dd>{job.role_category || "Unknown"}</dd>
            <dt>Remote Status</dt>
            <dd>{job.remote_status || "Unknown"}</dd>
            <dt>Match Score</dt>
            <dd>{formatScore(job.resume_match_score)}</dd>
            <dt>Priority</dt>
            <dd>{formatScore(job.overall_priority_score)}</dd>
            <dt>Verification</dt>
            <dd>{job.verification_status} ({formatScore(job.verification_score)})</dd>
          </dl>
        </article>

        <article className="panel">
          <h2>Fit</h2>
          <dl className="key-value">
            <dt>Experience Fit</dt>
            <dd>{formatScore(job.experience_fit_score)}</dd>
            <dt>Years Experience</dt>
            <dd>{formatYearsExperience(job)}</dd>
            <dt>Degree Fit</dt>
            <dd>{job.education_requirements.length > 0 ? job.education_requirements.join("; ") : "No strict degree requirement found"}</dd>
            <dt>Location Fit</dt>
            <dd>{formatScore(job.location_score)}</dd>
            <dt>Status</dt>
            <dd>{job.application_status.replace(/_/g, " ")}</dd>
          </dl>
        </article>
      </section>

      <section className="panel">
        <h2>Job Description</h2>
        {description ? (
          <div className="stack">
            {description.split(/\n{2,}/).map((paragraph, index) => (
              <p key={`${job.id}-${index}`}>{paragraph.replace(/\n/g, " ")}</p>
            ))}
          </div>
        ) : (
          <p className="subtle">No job description is saved for this job.</p>
        )}
      </section>

      <details className="details-block">
        <summary>Advanced details</summary>
        <section className="panel-grid">
          <article className="panel">
            <h2>Verification Details</h2>
            {job.verification_evidence.length > 0 ? (
              <ul className="list">
                {job.verification_evidence.map((item) => <li key={item}>{item}</li>)}
              </ul>
            ) : (
              <p className="subtle">No verification evidence is saved yet.</p>
            )}
          </article>
          <article className="panel">
            <h2>Scoring Evidence</h2>
            <pre className="code-block">{JSON.stringify(job.scoring_evidence, null, 2)}</pre>
          </article>
          <article className="panel">
            <h2>Prediction Evidence</h2>
            <pre className="code-block">{JSON.stringify(job.prediction_evidence, null, 2)}</pre>
          </article>
          <article className="panel">
            <h2>Raw Parsed Data</h2>
            <pre className="code-block">{JSON.stringify(job.raw_parsed_data, null, 2)}</pre>
          </article>
        </section>
      </details>
    </div>
  );
}
