"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { JobTable, type JobTableRow } from "@/components/JobTable";
import {
  type AIProviderInfo,
  type AIStatus,
  type Job,
  type JobImportRequest,
  type JobParseResult,
  type RecommendationResponse,
  type ScoreAllSummary,
  type VerifyAllSummary,
  getAIProviders,
  getAIStatus,
  getJob,
  getJobs,
  getRecommendations,
  importJob,
  parseJobImport,
  scoreAllJobs,
  verifyAllJobs,
} from "@/lib/api";

export type JobsManagerView = "saved" | "recommended" | "manual";

const ACTIVE_FILTERS = [
  { key: "active", label: "All active" },
  { key: "recommended", label: "Recommended" },
  { key: "needs_verification", label: "Needs verification" },
  { key: "needs_scoring", label: "Needs scoring" },
  { key: "packet_ready", label: "Packet ready" },
  { key: "opened", label: "Opened" },
  { key: "applied", label: "Applied" },
  { key: "follow_up", label: "Follow-up" },
  { key: "closed", label: "Closed/rejected" },
];

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

function isClosedJob(job: Job) {
  return ["rejected", "withdrawn", "closed_before_apply", "closed"].includes(job.application_status) || job.verification_status === "closed";
}

function getNextAction(job: Job) {
  if (isClosedJob(job)) {
    return { label: "Review archive", href: `/jobs/${job.id}`, tone: "secondary" as const };
  }
  if (job.application_status === "applied_manual" || job.application_status === "follow_up" || job.interview_at) {
    return { label: "Track outcome", href: `/jobs/${job.id}`, tone: "secondary" as const };
  }
  if (job.application_status === "application_opened") {
    return { label: "Mark applied or follow up", href: `/jobs/${job.id}`, tone: "primary" as const };
  }
  if (job.application_status === "packet_ready") {
    return { label: "Open/apply", href: `/jobs/${job.id}`, tone: "primary" as const };
  }
  if (job.verification_status === "unknown") {
    return { label: "Verify job", href: `/jobs/${job.id}`, tone: "primary" as const };
  }
  if (job.scoring_status !== "scored") {
    return { label: "Score fit", href: `/jobs/${job.id}`, tone: "primary" as const };
  }
  if (job.overall_priority_score >= 65) {
    return { label: "Generate packet", href: `/jobs/${job.id}`, tone: "primary" as const };
  }
  return { label: "Open job", href: `/jobs/${job.id}`, tone: "secondary" as const };
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

function jobMatchesFilter(job: Job, filter: string) {
  if (filter === "recommended") {
    return job.scoring_status === "scored" && job.overall_priority_score >= 65 && !isClosedJob(job);
  }
  if (filter === "needs_verification") {
    return job.verification_status === "unknown" && !isClosedJob(job);
  }
  if (filter === "needs_scoring") {
    return job.scoring_status !== "scored" && !isClosedJob(job);
  }
  if (filter === "packet_ready") {
    return job.application_status === "packet_ready";
  }
  if (filter === "opened") {
    return job.application_status === "application_opened";
  }
  if (filter === "applied") {
    return ["applied_manual", "interview", "offer"].includes(job.application_status);
  }
  if (filter === "follow_up") {
    return job.application_status === "follow_up" || Boolean(job.follow_up_at);
  }
  if (filter === "closed") {
    return isClosedJob(job);
  }
  return !isClosedJob(job);
}

const defaultRequest: JobImportRequest = {
  input_type: "description",
  content: "",
  source: "manual",
  use_ai: false,
  provider: "mock",
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
  const [aiStatus, setAIStatus] = useState<AIStatus | null>(null);
  const [providerOptions, setProviderOptions] = useState<AIProviderInfo[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastSavedJobId, setLastSavedJobId] = useState<number | null>(null);
  const [savedFilter, setSavedFilter] = useState("active");
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
          activeDisplayStatus: job.application_status === "autofill_completed" ? "autofill test completed" : job.application_status,
        };
      })
      .filter((row) => (showTestJobs ? true : !row.isTestJob))
      .filter((row) => (showDuplicates ? true : !row.isDuplicate))
      .filter((row) => jobMatchesFilter(row.job, savedFilter))
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
  }, [jobs, savedFilter, search, showDuplicates, showTestJobs]);

  const visibleRecommendations = useMemo(
    () => (recommendations?.jobs || []).filter((job) => (showTestJobs ? true : !isTestJob(job))),
    [recommendations, showTestJobs],
  );

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

  async function loadAIConfig() {
    try {
      const [statusResponse, providersResponse] = await Promise.all([getAIStatus(), getAIProviders()]);
      setAIStatus(statusResponse);
      setProviderOptions(providersResponse.providers);
    } catch {
      setAIStatus(null);
      setProviderOptions([
        { name: "mock", available: true, message: null },
        { name: "openai", available: false, message: "Unavailable." },
        { name: "local", available: false, message: "Placeholder provider." },
      ]);
    }
  }

  useEffect(() => {
    void refreshData();
    void loadAIConfig();
  }, []);

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
    setLastSavedJobId(null);

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
    setLastSavedJobId(null);
    setVerifySummary(null);
    setScoreSummary(null);

    try {
      const response = await importJob(form);
      setMessage(`Imported and saved job #${response.id}.`);
      setLastSavedJobId(response.id);
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
                  Open Job Detail
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
                  <Link href={`/jobs/${job.id}`} className="button secondary compact">
                    Open Job
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
        <p className="subtle">
          Paste a job description or URL when Job Finder does not cover the source. Most new jobs should start in Discover.
        </p>
        <ul className="list">
          <li>Rule-based parsing remains the default and only fills fields CareerAgent can honestly infer.</li>
          <li>AI parsing is a draft enhancement and still must not invent experience, credentials, or work authorization facts.</li>
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

          <label className="field-group">
            <span>Use AI Parsing</span>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={Boolean(form.use_ai)}
                onChange={(event) => setForm((current) => ({ ...current, use_ai: event.target.checked }))}
              />
              <span>AI parsing is optional. Rule-based parsing is used by default.</span>
            </label>
          </label>

          <label className="field-group">
            <span>AI Provider</span>
            <select
              className="input"
              value={form.provider || "mock"}
              onChange={(event) => setForm((current) => ({ ...current, provider: event.target.value }))}
            >
              {(providerOptions.length > 0 ? providerOptions : [{ name: "mock", available: true, message: null }]).map((provider) => (
                <option key={provider.name} value={provider.name}>
                  {provider.name} {provider.available ? "" : "(unavailable)"}
                </option>
              ))}
            </select>
            <span className="subtle">
              {aiStatus?.message || "CareerAgent falls back safely if the selected provider is unavailable."}
            </span>
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
                  <dt>Provider</dt>
                  <dd>{preview.provider || "rule_based"}</dd>
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
        <p className="subtle">
          This is the clean saved-jobs queue. Open a job detail page for verify, score, packet, apply, autofill, and tracker actions.
        </p>
        <div className="job-filter-tabs" aria-label="Saved job filters">
          {ACTIVE_FILTERS.map((filter) => (
            <button
              className={savedFilter === filter.key ? "filter-chip active" : "filter-chip"}
              type="button"
              key={filter.key}
              onClick={() => setSavedFilter(filter.key)}
            >
              {filter.label}
            </button>
          ))}
        </div>
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
          <JobTable rows={tableRows} onViewDescription={handleViewDescription} />
        )}
      </section> : null}
    </div>
  );
}
