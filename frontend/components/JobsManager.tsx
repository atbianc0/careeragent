"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { JobTable, type JobTableRow } from "@/components/JobTable";
import {
  type Job,
  type JobImportRequest,
  type JobParseResult,
  type RecommendationResponse,
  type ScoreAllSummary,
  type VerifyAllSummary,
  getJob,
  getAppliedJobs,
  getJobs,
  getSavedJobs,
  getRecommendations,
  importJob,
  parseJobImport,
  scoreAllJobs,
  verifyAllJobs,
} from "@/lib/api";

export type JobsManagerView = "saved" | "applied" | "manual" | "recommended";

const SAVED_STATUSES = new Set([
  "saved",
  "ready_to_apply",
  "verified_open",
  "packet_ready",
  "application_opened",
  "applying",
  "autofill_started",
  "autofill_completed",
]);

const APPLIED_STATUSES = new Set(["applied", "applied_manual", "interview", "rejected", "offer", "withdrawn", "closed_after_apply"]);

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

function isPartialParse(preview: JobParseResult) {
  return preview.parsing_status === "partial";
}

function formatImportError(error: unknown, inputType: JobImportRequest["input_type"]) {
  const baseMessage = error instanceof Error ? error.message : "Failed to parse or save the job.";
  if (inputType !== "url") {
    return baseMessage;
  }
  return `${baseMessage} Open the job in your browser, copy the full job description, and paste it into CareerAgent.`;
}

function normalizeKeyPart(value: string | null | undefined) {
  return (value || "").trim().toLowerCase().replace(/\s+/g, " ");
}

function normalizedJobKey(job: Job) {
  const url = normalizeKeyPart(job.url).replace(/\/+$/, "");
  if (url) {
    return `url:${url}`;
  }
  return `job:${normalizeKeyPart(job.company)}|${normalizeKeyPart(job.title)}|${normalizeKeyPart(job.location)}`;
}

function isTestJob(job: Job) {
  const combined = `${job.source} ${job.application_status} ${job.company} ${job.title}`.toLowerCase();
  return ["local_test", "stage10_smoke", "test", "demo", "careeragent test company", "test company", "fake local test form"].some((token) =>
    combined.includes(token),
  );
}

function formatDisplayStatus(value: string) {
  const labels: Record<string, string> = {
    saved: "Saved",
    ready_to_apply: "Ready to Apply",
    verified_open: "Ready to Apply",
    packet_ready: "Ready to Apply",
    application_opened: "Applying",
    applying: "Applying",
    autofill_started: "Applying",
    autofill_completed: "Applying",
    applied: "Applied",
    applied_manual: "Applied",
    interview: "Interview",
    rejected: "Rejected",
    offer: "Offer",
    withdrawn: "Withdrawn",
    closed_before_apply: "Closed",
    closed_after_apply: "Closed",
  };
  return labels[value] || value.replace(/_/g, " ");
}

function outcomeForJob(job: Job) {
  if (job.offer_at || job.application_status === "offer") return "Offer";
  if (job.interview_at || job.application_status === "interview") return "Interview";
  if (job.rejected_at || job.application_status === "rejected") return "Rejected";
  if (job.withdrawn_at || job.application_status === "withdrawn") return "Withdrawn";
  if (job.application_status === "closed_after_apply") return "Closed";
  return "Pending";
}

function isClosedJob(job: Job) {
  return ["rejected", "withdrawn", "closed_before_apply", "closed_after_apply", "closed"].includes(job.application_status) || job.verification_status === "closed";
}

function isSavedJob(job: Job) {
  return SAVED_STATUSES.has(job.application_status) && !job.applied_at;
}

function isAppliedJob(job: Job) {
  return APPLIED_STATUSES.has(job.application_status) || job.applied_at !== null;
}

function getNextAction(job: Job) {
  if (isClosedJob(job)) {
    return { label: "View Details", href: `/jobs/${job.id}`, tone: "secondary" as const };
  }
  if (APPLIED_STATUSES.has(job.application_status) || job.applied_at || job.interview_at) {
    return { label: "View in Insights", href: "/insights", tone: "secondary" as const };
  }
  if (job.application_status === "application_opened" || job.application_status === "autofill_started" || job.application_status === "autofill_completed") {
    return { label: "Continue Apply", href: `/apply?jobId=${job.id}`, tone: "primary" as const };
  }
  return { label: "Apply", href: `/apply?jobId=${job.id}`, tone: "primary" as const };
}

function descriptionTextForJob(job: Job | null) {
  const raw = job?.job_description?.trim() || "";
  if (!raw) {
    return "";
  }

  if (typeof window !== "undefined" && /<[^>]+>/.test(raw)) {
    const document = new DOMParser().parseFromString(raw, "text/html");
    return (document.body.textContent || "").trim();
  }

  return raw
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/p>/gi, "\n\n")
    .replace(/<[^>]+>/g, "")
    .trim();
}

function descriptionParagraphs(job: Job | null) {
  return descriptionTextForJob(job)
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.replace(/\n/g, " ").trim())
    .filter(Boolean);
}

const defaultRequest: JobImportRequest = {
  input_type: "description",
  content: "",
  source: "manual",
};

export function JobsManager({ view = "saved" }: { view?: JobsManagerView }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [form, setForm] = useState<JobImportRequest>(defaultRequest);
  const [preview, setPreview] = useState<JobParseResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [verifyingAll, setVerifyingAll] = useState(false);
  const [scoringAll, setScoringAll] = useState(false);
  const [verifySummary, setVerifySummary] = useState<VerifyAllSummary | null>(null);
  const [scoreSummary, setScoreSummary] = useState<ScoreAllSummary | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [showTestJobs, setShowTestJobs] = useState(false);
  const [showDuplicates, setShowDuplicates] = useState(false);
  const [selectedDescriptionJob, setSelectedDescriptionJob] = useState<Job | null>(null);
  const [descriptionModalOpen, setDescriptionModalOpen] = useState(false);
  const [descriptionLoading, setDescriptionLoading] = useState(false);
  const [descriptionError, setDescriptionError] = useState<string | null>(null);

  const tableRows = useMemo<JobTableRow[]>(() => {
    const firstSeen = new Map<string, number>();
    const duplicateOf = new Map<number, number>();

    for (const job of jobs) {
      const key = normalizedJobKey(job);
      const existing = firstSeen.get(key);
      if (existing !== undefined) {
        duplicateOf.set(job.id, existing);
      } else {
        firstSeen.set(key, job.id);
      }
    }

    const searchTerm = search.trim().toLowerCase();
    return jobs
      .map((job) => {
        const duplicateOfJobId = duplicateOf.get(job.id) ?? null;
        const isDuplicate = duplicateOfJobId !== null;
        return {
          job,
          nextAction: getNextAction(job),
          isDuplicate,
          duplicateOfJobId,
          isTestJob: isTestJob(job),
          activeDisplayStatus: job.application_status,
        };
      })
      .filter((row) => (showTestJobs ? true : !row.isTestJob))
      .filter((row) => (showDuplicates ? true : !row.isDuplicate))
      .filter((row) => {
        if (view === "applied") {
          return isAppliedJob(row.job);
        }
        if (view === "saved") {
          return isSavedJob(row.job);
        }
        return true;
      })
      .filter((row) => {
        if (!searchTerm) {
          return true;
        }
        return [row.job.company, row.job.title, row.job.location].some((value) => value.toLowerCase().includes(searchTerm));
      })
      .sort((left, right) => {
        if (left.job.overall_priority_score !== right.job.overall_priority_score) {
          return right.job.overall_priority_score - left.job.overall_priority_score;
        }
        return right.job.id - left.job.id;
      });
  }, [jobs, search, showDuplicates, showTestJobs, view]);

  const visibleRecommendations = useMemo(
    () => (recommendations?.jobs || []).filter((job) => (showTestJobs ? true : !isTestJob(job))),
    [recommendations, showTestJobs],
  );

  async function loadJobs() {
    const response = view === "applied" ? await getAppliedJobs() : view === "saved" ? await getSavedJobs() : await getJobs();
    setJobs(response);
  }

  async function loadRecommendations() {
    const response = await getRecommendations({ limit: 5 });
    setRecommendations(response);
  }

  async function refreshData() {
    setLoading(true);
    try {
      if (view === "recommended") {
        await Promise.all([loadJobs(), loadRecommendations()]);
      } else {
        await loadJobs();
      }
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load jobs and recommendations.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshData();
  }, [view]);

  useEffect(() => {
    if (!descriptionModalOpen) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setDescriptionModalOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [descriptionModalOpen]);

  async function handleViewDescription(job: Job) {
    setSelectedDescriptionJob(job);
    setDescriptionModalOpen(true);
    setDescriptionLoading(true);
    setDescriptionError(null);

    try {
      const fullJob = await getJob(job.id);
      setSelectedDescriptionJob(fullJob);
      setJobs((currentJobs) => currentJobs.map((currentJob) => (currentJob.id === fullJob.id ? fullJob : currentJob)));
    } catch (loadError) {
      setDescriptionError(loadError instanceof Error ? loadError.message : "Failed to load the saved job description.");
    } finally {
      setDescriptionLoading(false);
    }
  }

  async function handlePreview() {
    setSubmitting(true);
    setMessage(null);
    setError(null);

    try {
      const response = await parseJobImport(form);
      setPreview(response);
    } catch (previewError) {
      setError(formatImportError(previewError, form.input_type));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleImport() {
    setSubmitting(true);
    setMessage(null);
    setError(null);
    setVerifySummary(null);
    setScoreSummary(null);

    try {
      const response = await importJob(form);
      if (response.verification_status === "unknown" || response.scoring_status !== "scored") {
        setMessage("Saved. View in Saved Jobs. Verification/scoring may need retry.");
      } else {
        setMessage("Saved. View in Saved Jobs.");
      }
      setPreview((currentPreview) =>
        currentPreview
          ? {
              ...currentPreview,
              ...response,
              input_type: form.input_type,
            }
          : null,
      );
      await refreshData();
    } catch (importError) {
      setError(formatImportError(importError, form.input_type));
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

  return (
    <div className="page">
      {descriptionModalOpen ? (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setDescriptionModalOpen(false);
            }
          }}
        >
          <section
            className="description-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="description-modal-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="description-modal-header">
              <div>
                <p className="subtle">Saved job description</p>
                <h2 id="description-modal-title">{selectedDescriptionJob?.title || "Saved Job"}</h2>
                <p className="subtle">
                  {selectedDescriptionJob?.company || "Unknown company"} • {selectedDescriptionJob?.location || "Unknown location"}
                </p>
                <p className="subtle">
                  Source: {selectedDescriptionJob?.source || "Unknown"}
                  {selectedDescriptionJob?.url ? ` • ${selectedDescriptionJob.url}` : ""}
                </p>
              </div>
              <button className="button secondary compact" type="button" onClick={() => setDescriptionModalOpen(false)}>
                Close
              </button>
            </div>

            <div className="button-row description-modal-actions">
              {selectedDescriptionJob ? (
                <Link href={`/jobs/${selectedDescriptionJob.id}`} className="button secondary compact">
                  Advanced Details
                </Link>
              ) : null}
              {selectedDescriptionJob?.url ? (
                <a href={selectedDescriptionJob.url} target="_blank" rel="noreferrer" className="button secondary compact">
                  Open Original Posting
                </a>
              ) : null}
            </div>

            {descriptionError ? <p className="message error">{descriptionError}</p> : null}

            <div className="description-modal-body">
              {descriptionLoading ? (
                <p className="subtle">Loading description...</p>
              ) : descriptionParagraphs(selectedDescriptionJob).length > 0 ? (
                descriptionParagraphs(selectedDescriptionJob).map((paragraph, index) => (
                  <p key={`${selectedDescriptionJob?.id || "job"}-${index}`}>{paragraph}</p>
                ))
              ) : (
                <p className="subtle">
                  No saved job description is available for this job. Open the job detail page or re-import the posting
                  with a full description.
                </p>
              )}
            </div>
          </section>
        </div>
      ) : null}

      {view === "recommended" ? <section className="panel">
        <div className="section-title">
          <h2>Recommended Jobs</h2>
          <span className="subtle">Top 5 ranked saved jobs</span>
        </div>
        <p className="subtle">
          CareerAgent ranks saved jobs by fit, availability, freshness, location, and application ease. These are guidance, not guarantees.
        </p>
        <div className="button-row">
          <label className="checkbox-row">
            <input type="checkbox" checked={showTestJobs} onChange={(event) => setShowTestJobs(event.target.checked)} />
            Show test/demo jobs
          </label>
        </div>
        {loading ? (
          <p className="subtle">Loading recommendations...</p>
        ) : visibleRecommendations.length > 0 ? (
          <div className="recommendation-list">
            {visibleRecommendations.map((job, index) => (
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
                <div className="button-row">
                  <Link href={`/apply?jobId=${job.id}`} className="button secondary compact">
                    Apply
                  </Link>
                  <span className="subtle">Next: {getNextAction(job).label}</span>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="subtle">
            No recommendations yet. Verify and score jobs first, then CareerAgent will rank the strongest options here.
          </p>
        )}
      </section> : null}

      {view === "manual" ? <section className="panel">
        <div className="section-title">
          <h2>Manual Import Job</h2>
          <Link href="/jobs?tab=discover" className="button secondary compact">
            Use Job Finder
          </Link>
        </div>
        <p className="subtle">Paste a job URL or description when discovery misses something.</p>
        <ul className="list">
          <li>Rule-based parsing remains the default and only fills fields CareerAgent can honestly infer.</li>
          <li>Job parsing is local/rule-based. AI/API is not used for job parsing.</li>
          <li>Verification is still rule-based and may be limited on JavaScript-heavy or blocked job pages.</li>
          <li>Scoring is still deterministic in the current workflow and may miss context or hidden requirements.</li>
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

          <div className="message">
            Job parsing is local/rule-based. External AI/API calls are blocked for job URL parsing, extraction, skills,
            degree, and experience parsing.
          </div>

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
            {submitting ? "Saving, verifying, and scoring..." : "Save Job"}
          </button>
        </div>

        {message ? (
          <p className="message success">
            {message}
          </p>
        ) : null}
        {error ? <p className="message error">{error}</p> : null}
      </section> : null}

      {view === "manual" ? <section className="panel">
        <div className="section-title">
          <h2>Parsed Preview</h2>
          <span className="subtle">
            {preview ? `${preview.parse_mode} • ${preview.parsing_status}` : "Nothing parsed yet"}
          </span>
        </div>
        {preview ? (
          <div className="stack">
            {isPartialParse(preview) ? (
              <section className="warning-panel">
                <h3>Partial Parse</h3>
                <p>
                  This page did not expose the full job text. CareerAgent inferred partial details from the URL. Paste
                  the job description manually for better parsing.
                </p>
              </section>
            ) : null}

            <div className="panel-grid">
              <article className="panel subtle-panel">
                <dl className="key-value">
                  <dt>Company</dt>
                  <dd>{preview.company || "Unknown"}</dd>
                  <dt>Title</dt>
                  <dd>{preview.title || "Unknown"}</dd>
                  <dt>Location</dt>
                  <dd>{preview.location || "Unknown"}</dd>
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
                  <dt>Parsing Mode</dt>
                  <dd>{preview.parse_mode || "rule_based"}</dd>
                  <dt>Salary</dt>
                  <dd>{formatSalaryRange(preview)}</dd>
                  <dt>Years Experience</dt>
                  <dd>{formatYearsExperience(preview)}</dd>
                </dl>
                {preview.parsing_warnings.length > 0 ? (
                  <>
                    <h3>Parsing Warnings</h3>
                    <ul className="list">
                      {preview.parsing_warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  </>
                ) : null}
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
          </div>
        ) : (
          <p className="subtle">Use Preview Parse to inspect the structured fields before you save the job.</p>
        )}
      </section> : null}

      {view === "saved" ? <section className="panel">
        <div className="section-title">
          <h2>Saved Jobs</h2>
          <span className="subtle">{loading ? "Loading..." : `${tableRows.length} shown of ${jobs.length}`}</span>
        </div>
        <p className="subtle">Jobs you saved and have not marked applied yet.</p>
        <div className="filter-row">
          <label className="field-group">
            <span>Search saved jobs</span>
            <input
              className="input"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Company, title, or location"
            />
          </label>
        </div>
        <div className="button-row">
          <label className="checkbox-row">
            <input type="checkbox" checked={showTestJobs} onChange={(event) => setShowTestJobs(event.target.checked)} />
            Show test/demo jobs
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={showDuplicates} onChange={(event) => setShowDuplicates(event.target.checked)} />
            Show duplicates
          </label>
        </div>
        <div className="button-row">
          <button
            className="button secondary"
            type="button"
            onClick={() => void refreshData()}
            disabled={loading || verifyingAll || scoringAll}
          >
            Refresh Jobs
          </button>
          <details className="details-block">
            <summary>Advanced refresh actions</summary>
            <div className="button-row">
              <button className="button secondary" type="button" onClick={handleVerifyAll} disabled={verifyingAll || jobs.length === 0}>
                {verifyingAll ? "Re-verifying..." : "Re-verify saved jobs"}
              </button>
              <button className="button secondary" type="button" onClick={handleScoreAll} disabled={scoringAll || jobs.length === 0}>
                {scoringAll ? "Re-scoring..." : "Re-score saved jobs"}
              </button>
            </div>
          </details>
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
        ) : jobs.length === 0 ? (
          <p className="subtle">No saved jobs yet. Save jobs from Discover first.</p>
        ) : (
          <JobTable rows={tableRows} onViewDescription={handleViewDescription} />
        )}
      </section> : null}

      {view === "applied" ? <section className="panel">
        <div className="section-title">
          <h2>Applied Jobs</h2>
          <span className="subtle">{loading ? "Loading..." : `${tableRows.length} shown of ${jobs.length}`}</span>
        </div>
        <p className="subtle">Jobs you manually submitted or moved into an outcome status.</p>
        <div className="button-row">
          <label className="checkbox-row">
            <input type="checkbox" checked={showTestJobs} onChange={(event) => setShowTestJobs(event.target.checked)} />
            Show test/demo jobs
          </label>
        </div>
        {loading ? (
          <p className="subtle">Loading applied jobs...</p>
        ) : tableRows.length === 0 ? (
          <p className="subtle">No applied jobs yet. After you submit an application manually, mark it applied from Apply.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Title</th>
                  <th>Applied date</th>
                  <th>Status</th>
                  <th>Score/Match</th>
                  <th>Outcome</th>
                  <th>Notes</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {tableRows.map(({ job }) => (
                  <tr key={job.id}>
                    <td>{job.company}</td>
                    <td><strong>{job.title}</strong></td>
                    <td>{job.applied_at ? new Date(job.applied_at).toLocaleDateString() : "-"}</td>
                    <td><span className={`status-tag status-${job.application_status.replace(/_/g, "-")}`}>{formatDisplayStatus(job.application_status)}</span></td>
                    <td>{job.overall_priority_score.toFixed(1)} / {job.resume_match_score.toFixed(1)}</td>
                    <td>{outcomeForJob(job)}</td>
                    <td>{job.user_notes ? job.user_notes.slice(0, 120) : "-"}</td>
                    <td>
                      <Link href={`/jobs/${job.id}`} className="button secondary compact">
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section> : null}
    </div>
  );
}
