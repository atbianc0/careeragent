"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { JobTable } from "@/components/JobTable";
import {
  type Job,
  type JobImportRequest,
  type JobParseResult,
  type RecommendationResponse,
  type ScoreAllSummary,
  type VerifyAllSummary,
  getJobs,
  getRecommendations,
  importJob,
  parseJobImport,
  scoreAllJobs,
  scoreJob,
  verifyAllJobs,
  verifyJob,
} from "@/lib/api";

function formatSalaryRange(job: {
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
}) {
  if (job.salary_min === null && job.salary_max === null) {
    return "Not found";
  }

  const formatter = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  });
  const currency = job.salary_currency || "USD";
  const minimum = job.salary_min !== null ? formatter.format(job.salary_min) : "Unknown";
  const maximum = job.salary_max !== null ? formatter.format(job.salary_max) : "Unknown";
  return `${currency} ${minimum} - ${maximum}`;
}

function formatYearsExperience(job: {
  years_experience_min: number | null;
  years_experience_max: number | null;
}) {
  if (job.years_experience_min === null && job.years_experience_max === null) {
    return "Not found";
  }
  if (job.years_experience_min !== null && job.years_experience_max !== null) {
    if (job.years_experience_min === job.years_experience_max) {
      return `${job.years_experience_min}+ years`;
    }
    return `${job.years_experience_min} - ${job.years_experience_max} years`;
  }
  if (job.years_experience_min !== null) {
    return `${job.years_experience_min}+ years`;
  }
  return `Up to ${job.years_experience_max} years`;
}

function renderItems(items: string[]) {
  if (items.length === 0) {
    return <p className="subtle">None found.</p>;
  }

  return (
    <ul className="list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function getRecommendationSummary(job: Job) {
  const evidence = job.scoring_evidence as { summary?: string[] } | null;
  return evidence?.summary?.slice(0, 3) || [];
}

const defaultRequest: JobImportRequest = {
  input_type: "description",
  content: "",
  source: "manual",
};

export function JobsManager() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [form, setForm] = useState<JobImportRequest>(defaultRequest);
  const [preview, setPreview] = useState<JobParseResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [verifyingAll, setVerifyingAll] = useState(false);
  const [scoringAll, setScoringAll] = useState(false);
  const [verifyingJobId, setVerifyingJobId] = useState<number | null>(null);
  const [scoringJobId, setScoringJobId] = useState<number | null>(null);
  const [verifySummary, setVerifySummary] = useState<VerifyAllSummary | null>(null);
  const [scoreSummary, setScoreSummary] = useState<ScoreAllSummary | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastSavedJobId, setLastSavedJobId] = useState<number | null>(null);

  async function loadJobs() {
    const response = await getJobs();
    setJobs(response);
  }

  async function loadRecommendations() {
    const response = await getRecommendations({ limit: 5 });
    setRecommendations(response);
  }

  async function refreshData() {
    setLoading(true);
    try {
      await Promise.all([loadJobs(), loadRecommendations()]);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load jobs and recommendations.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshData();
  }, []);

  async function handlePreview() {
    setSubmitting(true);
    setMessage(null);
    setError(null);
    setLastSavedJobId(null);

    try {
      const response = await parseJobImport(form);
      setPreview(response);
    } catch (previewError) {
      setError(previewError instanceof Error ? previewError.message : "Failed to preview the parsed job.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleImport() {
    setSubmitting(true);
    setMessage(null);
    setError(null);
    setLastSavedJobId(null);
    setVerifySummary(null);
    setScoreSummary(null);

    try {
      const response = await importJob(form);
      setMessage(`Imported and saved job #${response.id}.`);
      setLastSavedJobId(response.id);
      setPreview({
        ...response,
        input_type: form.input_type,
        parse_mode: "rule_based_v1",
      });
      await refreshData();
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : "Failed to import and save the job.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleVerifyAll() {
    setVerifyingAll(true);
    setMessage(null);
    setError(null);

    try {
      const summary = await verifyAllJobs();
      setVerifySummary(summary);
      setMessage(`Verified ${summary.verified_count} job URL${summary.verified_count === 1 ? "" : "s"}.`);
      await refreshData();
    } catch (verifyError) {
      setError(verifyError instanceof Error ? verifyError.message : "Failed to verify saved jobs.");
    } finally {
      setVerifyingAll(false);
    }
  }

  async function handleVerifyJob(job: Job) {
    if (!job.url.trim()) {
      setError(`Job #${job.id} has no URL to verify.`);
      return;
    }

    setVerifyingJobId(job.id);
    setMessage(null);
    setError(null);

    try {
      const response = await verifyJob(job.id);
      setJobs((currentJobs) =>
        currentJobs.map((currentJob) => (currentJob.id === response.job.id ? response.job : currentJob)),
      );
      await loadRecommendations();
      setMessage(
        `Verified job #${response.job.id}: ${response.verification.verification_status} (${response.verification.verification_score}/100).`,
      );
    } catch (verifyError) {
      setError(verifyError instanceof Error ? verifyError.message : `Failed to verify job #${job.id}.`);
    } finally {
      setVerifyingJobId(null);
    }
  }

  async function handleScoreAll() {
    setScoringAll(true);
    setMessage(null);
    setError(null);

    try {
      const summary = await scoreAllJobs();
      setScoreSummary(summary);
      setMessage(`Scored ${summary.scored_count} job${summary.scored_count === 1 ? "" : "s"} against the current profile and resume.`);
      await refreshData();
    } catch (scoreError) {
      setError(scoreError instanceof Error ? scoreError.message : "Failed to score saved jobs.");
    } finally {
      setScoringAll(false);
    }
  }

  async function handleScoreJob(job: Job) {
    setScoringJobId(job.id);
    setMessage(null);
    setError(null);

    try {
      const response = await scoreJob(job.id);
      setJobs((currentJobs) =>
        currentJobs.map((currentJob) => (currentJob.id === response.job.id ? response.job : currentJob)),
      );
      await loadRecommendations();
      setMessage(
        `Scored job #${response.job.id}: resume match ${response.score.resume_match_score}/100, priority ${response.score.overall_priority_score}/100.`,
      );
    } catch (scoreError) {
      setError(scoreError instanceof Error ? scoreError.message : `Failed to score job #${job.id}.`);
    } finally {
      setScoringJobId(null);
    }
  }

  return (
    <div className="page">
      <section className="panel">
        <div className="section-title">
          <h2>Recommended Jobs</h2>
          <span className="status-tag">Stage 5</span>
        </div>
        <p className="subtle">
          Recommendations are rule-based and blend resume fit, availability, freshness, location fit, and application ease.
          They are a starting point, not a guarantee. Stage 6 can generate application packets for the jobs you choose next.
        </p>
        {loading ? (
          <p className="subtle">Loading recommendations...</p>
        ) : recommendations && recommendations.jobs.length > 0 ? (
          <div className="recommendation-list">
            {recommendations.jobs.map((job, index) => (
              <article className="recommendation-card" key={job.id}>
                <div className="recommendation-header">
                  <div>
                    <p className="subtle">Rank #{index + 1}</p>
                    <h3>
                      <Link href={`/jobs/${job.id}`} className="job-link">
                        {job.title}
                      </Link>
                    </h3>
                    <p className="subtle">
                      {job.company} • {job.location}
                    </p>
                  </div>
                  <div className="recommendation-metrics">
                    <span className="status-tag status-open">Priority {job.overall_priority_score.toFixed(1)}</span>
                    <span className="planned-chip">Match {job.resume_match_score.toFixed(1)}</span>
                    <span className={`status-tag status-${job.verification_status.replace(/_/g, "-")}`}>
                      {job.verification_status}
                    </span>
                  </div>
                </div>
                <ul className="list">
                  {getRecommendationSummary(job).map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
                <p className="subtle">Freshness score: {job.freshness_score.toFixed(1)}</p>
              </article>
            ))}
          </div>
        ) : (
          <p className="subtle">
            No recommendations yet. Verify and score jobs first, then CareerAgent will rank the strongest options here.
          </p>
        )}
      </section>

      <section className="panel">
        <div className="section-title">
          <h2>Import Job</h2>
          <span className="status-tag">Stage 5</span>
        </div>
        <p className="subtle">
          Paste a job description or URL, preview the rule-based parsing, save the job into PostgreSQL, then verify and score
          it against the current profile and resume.
        </p>
        <ul className="list">
          <li>Parsing is rule-based and only fills fields CareerAgent can honestly infer.</li>
          <li>Verification is still rule-based and may be limited on JavaScript-heavy or blocked job pages.</li>
          <li>Scoring is also rule-based in Stage 5. It does not use AI yet and may miss context or hidden requirements.</li>
        </ul>

        <div className="form-grid">
          <label className="field-group">
            <span>Input Type</span>
            <select
              className="input"
              value={form.input_type}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  input_type: event.target.value as JobImportRequest["input_type"],
                  content: "",
                }))
              }
            >
              <option value="description">Paste Job Description</option>
              <option value="url">Paste Job URL</option>
            </select>
          </label>

          <label className="field-group">
            <span>Source</span>
            <input
              className="input"
              value={form.source}
              onChange={(event) => setForm((current) => ({ ...current, source: event.target.value }))}
            />
          </label>

          <label className="field-group">
            <span>{form.input_type === "url" ? "Job URL" : "Job Description"}</span>
            {form.input_type === "url" ? (
              <input
                className="input"
                placeholder="https://example.com/job-posting"
                value={form.content}
                onChange={(event) => setForm((current) => ({ ...current, content: event.target.value }))}
              />
            ) : (
              <textarea
                className="textarea"
                rows={14}
                placeholder="Paste the job description here..."
                value={form.content}
                onChange={(event) => setForm((current) => ({ ...current, content: event.target.value }))}
              />
            )}
          </label>
        </div>

        <div className="button-row">
          <button className="button secondary" type="button" onClick={handlePreview} disabled={submitting}>
            Preview Parse
          </button>
          <button className="button" type="button" onClick={handleImport} disabled={submitting}>
            Import and Save
          </button>
        </div>

        {message ? (
          <p className="message success">
            {message}{" "}
            {lastSavedJobId !== null ? (
              <Link href={`/jobs/${lastSavedJobId}`} className="inline-link">
                Open saved job
              </Link>
            ) : null}
          </p>
        ) : null}
        {error ? <p className="message error">{error}</p> : null}
      </section>

      <section className="panel">
        <div className="section-title">
          <h2>Parsed Preview</h2>
          <span className="subtle">{preview ? preview.parse_mode : "Nothing parsed yet"}</span>
        </div>
        {preview ? (
          <div className="panel-grid">
            <article className="panel subtle-panel">
              <dl className="key-value">
                <dt>Company</dt>
                <dd>{preview.company}</dd>
                <dt>Title</dt>
                <dd>{preview.title}</dd>
                <dt>Location</dt>
                <dd>{preview.location}</dd>
                <dt>Source</dt>
                <dd>{preview.source}</dd>
                <dt>URL</dt>
                <dd>{preview.url || "Not provided"}</dd>
                <dt>Role Category</dt>
                <dd>{preview.role_category || "Unknown"}</dd>
                <dt>Seniority</dt>
                <dd>{preview.seniority_level || "Unknown"}</dd>
                <dt>Remote Status</dt>
                <dd>{preview.remote_status || "Unknown"}</dd>
                <dt>Salary</dt>
                <dd>{formatSalaryRange(preview)}</dd>
                <dt>Years Experience</dt>
                <dd>{formatYearsExperience(preview)}</dd>
              </dl>
            </article>

            <article className="panel subtle-panel">
              <h3>Required Skills</h3>
              <div className="pill-list">
                {preview.required_skills.length > 0 ? (
                  preview.required_skills.map((skill) => (
                    <span className="pill" key={skill}>
                      {skill}
                    </span>
                  ))
                ) : (
                  <span className="subtle">None found.</span>
                )}
              </div>

              <h3>Preferred Skills</h3>
              <div className="pill-list">
                {preview.preferred_skills.length > 0 ? (
                  preview.preferred_skills.map((skill) => (
                    <span className="pill" key={skill}>
                      {skill}
                    </span>
                  ))
                ) : (
                  <span className="subtle">None found.</span>
                )}
              </div>
            </article>

            <article className="panel subtle-panel">
              <h3>Responsibilities</h3>
              {renderItems(preview.responsibilities)}
            </article>

            <article className="panel subtle-panel">
              <h3>Requirements</h3>
              {renderItems(preview.requirements)}
            </article>

            <article className="panel subtle-panel">
              <h3>Application Questions</h3>
              {renderItems(preview.application_questions)}
            </article>
          </div>
        ) : (
          <p className="subtle">Use Preview Parse to inspect the structured fields before you save the job.</p>
        )}
      </section>

      <section className="panel">
        <div className="section-title">
          <h2>Saved Jobs</h2>
          <span className="subtle">{loading ? "Loading..." : `${jobs.length} jobs`}</span>
        </div>
        <p className="subtle">
          Verify jobs first to estimate availability, then score them against the profile and resume to prioritize which ones to apply to first.
        </p>
        <div className="button-row">
          <button
            className="button secondary"
            type="button"
            onClick={() => void refreshData()}
            disabled={loading || verifyingAll || scoringAll}
          >
            Refresh Jobs
          </button>
          <button className="button secondary" type="button" onClick={handleVerifyAll} disabled={verifyingAll || jobs.length === 0}>
            {verifyingAll ? "Verifying All Jobs..." : "Verify All Jobs"}
          </button>
          <button className="button" type="button" onClick={handleScoreAll} disabled={scoringAll || jobs.length === 0}>
            {scoringAll ? "Scoring All Jobs..." : "Score All Jobs"}
          </button>
        </div>

        {verifySummary ? (
          <div className="message success">
            <strong>Verification summary:</strong> {verifySummary.verified_count} verified, {verifySummary.skipped_count} skipped,
            {" "}open {verifySummary.open_count}, probably open {verifySummary.probably_open_count}, unknown {verifySummary.unknown_count},
            {" "}possibly closed {verifySummary.possibly_closed_count}, likely closed {verifySummary.likely_closed_count}, closed {verifySummary.closed_count}.
            {verifySummary.errors.length > 0 ? (
              <details className="details-block">
                <summary>View warnings</summary>
                <ul className="list">
                  {verifySummary.errors.map((entry) => (
                    <li key={entry}>{entry}</li>
                  ))}
                </ul>
              </details>
            ) : null}
          </div>
        ) : null}

        {scoreSummary ? (
          <div className="message success">
            <strong>Scoring summary:</strong> {scoreSummary.scored_count} scored, {scoreSummary.skipped_count} skipped, average match{" "}
            {scoreSummary.average_resume_match_score}, average priority {scoreSummary.average_overall_priority_score}.
            {scoreSummary.top_jobs.length > 0 ? (
              <ul className="list">
                {scoreSummary.top_jobs.map((job) => (
                  <li key={job.id}>
                    <Link href={`/jobs/${job.id}`} className="inline-link">
                      {job.title} at {job.company}
                    </Link>{" "}
                    — priority {job.overall_priority_score}, match {job.resume_match_score}
                  </li>
                ))}
              </ul>
            ) : null}
            {scoreSummary.errors.length > 0 ? (
              <details className="details-block">
                <summary>View scoring warnings</summary>
                <ul className="list">
                  {scoreSummary.errors.map((entry) => (
                    <li key={entry}>{entry}</li>
                  ))}
                </ul>
              </details>
            ) : null}
          </div>
        ) : null}

        {loading ? (
          <p className="subtle">Loading jobs...</p>
        ) : (
          <JobTable
            jobs={jobs}
            onVerify={handleVerifyJob}
            onScore={handleScoreJob}
            verifyingJobId={verifyingJobId}
            scoringJobId={scoringJobId}
          />
        )}
      </section>
    </div>
  );
}
