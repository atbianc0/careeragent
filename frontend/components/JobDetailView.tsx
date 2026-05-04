"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AutofillControls } from "@/components/AutofillControls";
import { TrackingActions } from "@/components/TrackingActions";
import {
  ApplicationEvent,
  ApplicationPacket,
  Job,
  JobPredictionDetails,
  generatePacket,
  getJob,
  getJobPrediction,
  getJobTimeline,
  getPacketsForJob,
  scoreJob,
  verifyJob,
} from "@/lib/api";

type JobDetailViewProps = {
  initialJob: Job;
};

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
  const minimum = job.salary_min !== null ? formatter.format(job.salary_min) : "Unknown";
  const maximum = job.salary_max !== null ? formatter.format(job.salary_max) : "Unknown";
  return `${job.salary_currency || "USD"} ${minimum} - ${maximum}`;
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

function formatSource(value: string) {
  return value === "sample_seed" ? "sample/demo" : value;
}

function getStatusClassName(status: string) {
  return `status-tag status-${status.replace(/_/g, "-")}`;
}

function getScoringEvidenceList(job: Job, key: string): string[] {
  const scoringEvidence = job.scoring_evidence as Record<string, unknown>;
  const section = scoringEvidence?.[key] as { evidence?: string[] } | undefined;
  return section?.evidence || [];
}

function getSummaryEvidence(job: Job): string[] {
  const scoringEvidence = job.scoring_evidence as Record<string, unknown>;
  return ((scoringEvidence?.summary as string[]) || []).slice(0, 6);
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "Not available";
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

function getNumberValue(record: Record<string, unknown> | undefined, key: string) {
  const value = record?.[key];
  return typeof value === "number" ? value : null;
}

function formatPredictionNumber(value: number | null | undefined) {
  return typeof value === "number" ? value.toFixed(0) : "Not available";
}

function formatPredictionConfidence(value: number | null | undefined) {
  return typeof value === "number" ? value.toFixed(2) : "Not available";
}

function getStringValue(record: Record<string, unknown> | undefined, key: string, fallback = "Not available") {
  const value = record?.[key];
  return typeof value === "string" && value ? value : fallback;
}

function getStringList(record: Record<string, unknown> | undefined, key: string) {
  const value = record?.[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

type PacketOptionToggleKey =
  | "include_cover_letter"
  | "include_recruiter_message"
  | "include_application_questions"
  | "compile_resume_pdf"
  | "use_ai";

export function JobDetailView({ initialJob }: JobDetailViewProps) {
  const [job, setJob] = useState<Job>(initialJob);
  const [verifying, setVerifying] = useState(false);
  const [scoring, setScoring] = useState(false);
  const [packets, setPackets] = useState<ApplicationPacket[]>([]);
  const [loadingPackets, setLoadingPackets] = useState(true);
  const [generatingPacket, setGeneratingPacket] = useState(false);
  const [packetMessage, setPacketMessage] = useState<string | null>(null);
  const [packetError, setPacketError] = useState<string | null>(null);
  const [packetOptions, setPacketOptions] = useState({
    include_cover_letter: true,
    include_recruiter_message: true,
    include_application_questions: true,
    compile_resume_pdf: true,
    use_ai: false,
    provider: "mock",
  });
  const [timeline, setTimeline] = useState<ApplicationEvent[]>([]);
  const [loadingTimeline, setLoadingTimeline] = useState(true);
  const [predictionDetails, setPredictionDetails] = useState<JobPredictionDetails | null>(null);
  const [loadingPrediction, setLoadingPrediction] = useState(true);
  const [predictionError, setPredictionError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const latestPacket = packets[0] || null;

  useEffect(() => {
    void loadPackets();
    void loadTimeline();
    void loadPrediction();
  }, [job.id]);

  async function loadPackets() {
    setLoadingPackets(true);
    try {
      const response = await getPacketsForJob(job.id);
      setPackets(response);
      setPacketError(null);
    } catch (loadError) {
      setPacketError(loadError instanceof Error ? loadError.message : "Failed to load packets for this job.");
    } finally {
      setLoadingPackets(false);
    }
  }

  async function loadTimeline() {
    setLoadingTimeline(true);
    try {
      const response = await getJobTimeline(job.id);
      setTimeline(response);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load the job timeline.");
    } finally {
      setLoadingTimeline(false);
    }
  }

  async function loadPrediction() {
    setLoadingPrediction(true);
    try {
      const response = await getJobPrediction(job.id);
      setPredictionDetails(response);
      setPredictionError(null);
    } catch (loadError) {
      setPredictionError(loadError instanceof Error ? loadError.message : "Failed to load prediction details.");
    } finally {
      setLoadingPrediction(false);
    }
  }

  async function handleVerify() {
    if (!job.url.trim()) {
      setError("This job does not have a saved URL to verify.");
      return;
    }

    setVerifying(true);
    setMessage(null);
    setError(null);

    try {
      const response = await verifyJob(job.id);
      setJob(response.job);
      await loadTimeline();
      setMessage(
        `Verification updated: ${response.verification.verification_status} (${response.verification.verification_score}/100).`,
      );
    } catch (verifyError) {
      setError(verifyError instanceof Error ? verifyError.message : "Failed to verify this job.");
    } finally {
      setVerifying(false);
    }
  }

  async function handleScore() {
    setScoring(true);
    setMessage(null);
    setError(null);

    try {
      const response = await scoreJob(job.id);
      setJob(response.job);
      await Promise.all([loadTimeline(), loadPrediction()]);
      setMessage(
        `Scoring updated: resume match ${response.score.resume_match_score}/100, priority ${response.score.overall_priority_score}/100.`,
      );
    } catch (scoreError) {
      setError(scoreError instanceof Error ? scoreError.message : "Failed to score this job.");
    } finally {
      setScoring(false);
    }
  }

  async function handleGeneratePacket() {
    setGeneratingPacket(true);
    setPacketMessage(null);
    setPacketError(null);

    try {
      const response = await generatePacket({
        job_id: job.id,
        ...packetOptions,
      });
      setJob(response.job);
      await Promise.all([loadPackets(), loadTimeline()]);

      if (response.compile_resume_pdf_requested && !response.compile_resume_pdf_success) {
        setPacketMessage(`${response.message} The rest of the packet was created, but the resume PDF is unavailable right now.`);
      } else {
        setPacketMessage(response.message);
      }
    } catch (generationError) {
      setPacketError(generationError instanceof Error ? generationError.message : "Failed to generate the application packet.");
    } finally {
      setGeneratingPacket(false);
    }
  }

  function togglePacketOption(key: PacketOptionToggleKey) {
    setPacketOptions((current) => ({
      ...current,
      [key]: !current[key],
    }));
  }

  function handleTrackedJobUpdated(updatedJob: Job) {
    setJob(updatedJob);
    void Promise.all([loadPackets(), loadTimeline(), loadPrediction()]);
  }

  async function refreshTrackedJob() {
    const refreshedJob = await getJob(job.id);
    setJob(refreshedJob);
    await Promise.all([loadPackets(), loadTimeline(), loadPrediction()]);
  }

  const priorityPrediction = predictionDetails?.priority_prediction;
  const closeRiskPrediction = predictionDetails?.close_risk_prediction;
  const responsePrediction = predictionDetails?.response_likelihood_prediction;

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">{job.role_category || "Imported Job"}</span>
        <h1>{job.title}</h1>
        <p className="hero-copy">
          {job.company} • {job.location} • {job.application_status}
        </p>
        <p className="hero-copy">
          Verification and scoring are both rule-based estimates. CareerAgent can help surface fit and availability signals,
          but you should still manually confirm the posting and review the recommendation before applying.
        </p>
        <div className="button-row">
          <Link href="/jobs" className="button secondary">
            Back to Jobs
          </Link>
          <Link href="/tracker" className="button secondary">
            Open Tracker
          </Link>
          <button className="button secondary" type="button" onClick={handleVerify} disabled={verifying || !job.url.trim()}>
            {verifying ? "Verifying..." : "Verify This Job"}
          </button>
          <button className="button" type="button" onClick={handleScore} disabled={scoring}>
            {scoring ? "Scoring..." : "Score This Job"}
          </button>
        </div>
        {message ? <p className="message success">{message}</p> : null}
        {error ? <p className="message error">{error}</p> : null}
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
            <dt>Source</dt>
            <dd>{formatSource(job.source)}</dd>
            <dt>URL</dt>
            <dd>{job.url || "No URL stored"}</dd>
            <dt>Application Status</dt>
            <dd>{job.application_status}</dd>
            <dt>Employment Type</dt>
            <dd>{job.employment_type || "Unknown"}</dd>
            <dt>Role Category</dt>
            <dd>{job.role_category || "Other"}</dd>
            <dt>Seniority</dt>
            <dd>{job.seniority_level || "Unknown"}</dd>
            <dt>Remote Status</dt>
            <dd>{job.remote_status || "Unknown"}</dd>
            <dt>Salary</dt>
            <dd>{formatSalaryRange(job)}</dd>
            <dt>Years Experience</dt>
            <dd>{formatYearsExperience(job)}</dd>
          </dl>
        </article>

        <article className="panel">
          <h2>Verification</h2>
          <p className="subtle">
            CareerAgent never clicks Apply or final submit buttons. This panel only estimates whether the job page still appears active.
          </p>
          <dl className="key-value">
            <dt>Status</dt>
            <dd>
              <span className={getStatusClassName(job.verification_status)}>{job.verification_status}</span>
            </dd>
            <dt>Verification Score</dt>
            <dd>{job.verification_score}</dd>
            <dt>Likely Closed Score</dt>
            <dd>{job.likely_closed_score}</dd>
            <dt>Last Checked</dt>
            <dd>{job.last_checked_date || "Not checked yet"}</dd>
            <dt>Last Seen</dt>
            <dd>{job.last_seen_date || "Unknown"}</dd>
            <dt>Closed Date</dt>
            <dd>{job.closed_date || "Not closed"}</dd>
            <dt>Freshness Score</dt>
            <dd>{job.freshness_score}</dd>
            <dt>Verification Error</dt>
            <dd>{job.last_verification_error || "None"}</dd>
          </dl>

          <h3>Verification Evidence</h3>
          {job.verification_evidence.length > 0 ? renderItems(job.verification_evidence) : <p className="subtle">No verification evidence yet.</p>}

          <details className="details-block">
            <summary>Raw verification details</summary>
            <pre className="code-block">{JSON.stringify(job.verification_raw_data, null, 2)}</pre>
          </details>
        </article>

        <article className="panel">
          <h2>Scoring</h2>
          <p className="subtle">
            Stage 5 compares the parsed job, profile YAML, and base resume text to estimate fit and application priority.
          </p>
          <dl className="key-value">
            <dt>Skill Match Score</dt>
            <dd>{job.skill_match_score}</dd>
            <dt>Role Match Score</dt>
            <dd>{job.role_match_score}</dd>
            <dt>Experience Fit Score</dt>
            <dd>{job.experience_fit_score}</dd>
            <dt>Profile Keyword Score</dt>
            <dd>{job.profile_keyword_score}</dd>
            <dt>Resume Match Score</dt>
            <dd>{job.resume_match_score}</dd>
            <dt>Freshness Score</dt>
            <dd>{job.freshness_score}</dd>
            <dt>Location Score</dt>
            <dd>{job.location_score}</dd>
            <dt>Application Ease Score</dt>
            <dd>{job.application_ease_score}</dd>
            <dt>Verification Score</dt>
            <dd>{job.verification_score}</dd>
            <dt>Overall Priority Score</dt>
            <dd>{job.overall_priority_score}</dd>
            <dt>Scoring Status</dt>
            <dd>{job.scoring_status}</dd>
            <dt>Scored At</dt>
            <dd>{job.scored_at || "Not scored yet"}</dd>
          </dl>

          <h3>Scoring Summary</h3>
          {getSummaryEvidence(job).length > 0 ? renderItems(getSummaryEvidence(job)) : <p className="subtle">No scoring evidence yet.</p>}

          <details className="details-block">
            <summary>Matched and missing skills</summary>
            <pre className="code-block">{JSON.stringify(job.scoring_raw_data, null, 2)}</pre>
          </details>
        </article>

        <article className="panel">
          <h2>Score Evidence</h2>
          <h3>Skill Match</h3>
          {renderItems(getScoringEvidenceList(job, "skill_match"))}
          <h3>Role Match</h3>
          {renderItems(getScoringEvidenceList(job, "role_match"))}
          <h3>Experience Fit</h3>
          {renderItems(getScoringEvidenceList(job, "experience_fit"))}
          <h3>Profile Keywords</h3>
          {renderItems(getScoringEvidenceList(job, "profile_keyword"))}
          <h3>Location</h3>
          {renderItems(getScoringEvidenceList(job, "location"))}
          <h3>Freshness</h3>
          {renderItems(getScoringEvidenceList(job, "freshness"))}
          <h3>Application Ease</h3>
          {renderItems(getScoringEvidenceList(job, "application_ease"))}
        </article>

        <article className="panel">
          <h2>Prediction</h2>
          <p className="subtle">
            Stage 11 estimates are cautious and explainable. Recalculate saved prediction fields from the Predictions page.
          </p>
          {loadingPrediction ? <p className="subtle">Loading prediction details...</p> : null}
          {predictionError ? <p className="message error">{predictionError}</p> : null}
          <dl className="key-value">
            <dt>Predicted Priority</dt>
            <dd>{formatPredictionNumber(getNumberValue(priorityPrediction, "predicted_priority_score") ?? job.predicted_priority_score)}</dd>
            <dt>Close Risk</dt>
            <dd>{formatPredictionNumber(getNumberValue(closeRiskPrediction, "predicted_close_risk_score") ?? job.predicted_close_risk_score)}</dd>
            <dt>Response Estimate</dt>
            <dd>{formatPredictionNumber(getNumberValue(responsePrediction, "predicted_response_score") ?? job.predicted_response_score)}</dd>
            <dt>Confidence</dt>
            <dd>
              {getStringValue(priorityPrediction, "confidence_label", "low")} (
              {formatPredictionConfidence(getNumberValue(priorityPrediction, "confidence") ?? job.prediction_confidence)})
            </dd>
            <dt>Risk Label</dt>
            <dd>{getStringValue(closeRiskPrediction, "risk_label", "unknown")}</dd>
            <dt>Suggested Action</dt>
            <dd>{getStringValue(priorityPrediction, "suggested_action", "manual_review").replace(/_/g, " ")}</dd>
            <dt>Updated</dt>
            <dd>{formatDateTime(predictionDetails?.stored_prediction.prediction_updated_at || job.prediction_updated_at)}</dd>
          </dl>
          {getStringValue(responsePrediction, "warning", "") ? (
            <p className="subtle">{getStringValue(responsePrediction, "warning", "")}</p>
          ) : null}
          <h3>Prediction Evidence</h3>
          {getStringList(priorityPrediction, "evidence").length > 0 ? (
            renderItems(getStringList(priorityPrediction, "evidence"))
          ) : (
            <p className="subtle">No prediction evidence has been generated yet.</p>
          )}
          <h3>Close-Risk Evidence</h3>
          {getStringList(closeRiskPrediction, "evidence").length > 0 ? (
            renderItems(getStringList(closeRiskPrediction, "evidence"))
          ) : (
            <p className="subtle">No close-risk evidence has been generated yet.</p>
          )}
          <div className="button-row">
            <Link href="/predictions" className="button secondary">
              Open Predictions Page
            </Link>
          </div>
        </article>

        <article className="panel">
          <h2>Tracking</h2>
          <p className="subtle">
            Stage 7 tracks the application workflow. Open application links through CareerAgent to log the action, then
            manually review and manually submit on the company site.
          </p>
          <dl className="key-value">
            <dt>Current Status</dt>
            <dd>
              <span className={getStatusClassName(job.application_status)}>{job.application_status}</span>
            </dd>
            <dt>Application Opened</dt>
            <dd>{formatDateTime(job.application_link_opened_at)}</dd>
            <dt>Packet Generated</dt>
            <dd>{formatDateTime(job.packet_generated_at)}</dd>
            <dt>Applied At</dt>
            <dd>{formatDateTime(job.applied_at)}</dd>
            <dt>Follow Up At</dt>
            <dd>{formatDateTime(job.follow_up_at)}</dd>
            <dt>Interview At</dt>
            <dd>{formatDateTime(job.interview_at)}</dd>
            <dt>Rejected At</dt>
            <dd>{formatDateTime(job.rejected_at)}</dd>
            <dt>Offer At</dt>
            <dd>{formatDateTime(job.offer_at)}</dd>
            <dt>Next Action</dt>
            <dd>{job.next_action || "None"}</dd>
            <dt>Next Action Due</dt>
            <dd>{formatDateTime(job.next_action_due_at)}</dd>
          </dl>
          {job.user_notes ? (
            <details className="details-block">
              <summary>Saved Notes</summary>
              <pre className="code-block">{job.user_notes}</pre>
            </details>
          ) : (
            <p className="subtle">No user notes saved yet.</p>
          )}
          <TrackingActions
            job={job}
            showClosedBeforeApply
            showCompleteFollowUp
            onJobUpdated={handleTrackedJobUpdated}
            onMessage={setMessage}
            onError={setError}
          />
          <div className="planned-action-stack">
            <span className="status-tag status-open">Tracker logging: Stage 7 live</span>
            <span className="status-tag status-open">Browser autofill: Stage 8 live</span>
          </div>
        </article>

        <article className="panel">
          <h2>Application Packet</h2>
          <p className="subtle">
            Stage 10 can optionally use AI drafts for packet materials, but every output remains reviewable and CareerAgent still does not submit applications.
          </p>
          <div className="checkbox-grid">
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={packetOptions.include_cover_letter}
                onChange={() => togglePacketOption("include_cover_letter")}
              />
              <span>Include cover letter draft</span>
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={packetOptions.include_recruiter_message}
                onChange={() => togglePacketOption("include_recruiter_message")}
              />
              <span>Include recruiter message draft</span>
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={packetOptions.include_application_questions}
                onChange={() => togglePacketOption("include_application_questions")}
              />
              <span>Include application question drafts</span>
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={packetOptions.compile_resume_pdf}
                onChange={() => togglePacketOption("compile_resume_pdf")}
              />
              <span>Compile tailored resume PDF when LaTeX is available</span>
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={packetOptions.use_ai}
                onChange={() => togglePacketOption("use_ai")}
              />
              <span>Use AI drafts for packet content</span>
            </label>
          </div>
          <label className="field-group">
            <span>AI Provider</span>
            <select
              className="input"
              value={packetOptions.provider}
              onChange={(event) =>
                setPacketOptions((current) => ({
                  ...current,
                  provider: event.target.value,
                }))
              }
            >
              <option value="mock">mock</option>
              <option value="openai">openai</option>
              <option value="local">local</option>
            </select>
            <span className="subtle">
              AI drafts are optional, must stay truthful, and should never invent experience or credentials.
            </span>
          </label>
          <div className="button-row">
            <button className="button" type="button" onClick={handleGeneratePacket} disabled={generatingPacket}>
              {generatingPacket ? "Generating Packet..." : "Generate Application Packet"}
            </button>
            {latestPacket ? (
              <Link href={`/packets/${latestPacket.id}`} className="button secondary">
                Open Latest Packet
              </Link>
            ) : null}
            <Link href={`/autofill?jobId=${job.id}`} className="button secondary">
              Open Autofill Page
            </Link>
          </div>
          <p className="subtle">
            AI output is a draft. Review all generated materials manually before using them. Work authorization and sponsorship answers must come from your profile settings.
          </p>
          {packetMessage ? <p className="message success">{packetMessage}</p> : null}
          {packetError ? <p className="message error">{packetError}</p> : null}
          {loadingPackets ? <p className="subtle">Loading packet history...</p> : null}
          {latestPacket ? (
            <div className="meta-stack">
              <dl className="key-value">
                <dt>Latest Packet</dt>
                <dd>#{latestPacket.id}</dd>
                <dt>Status</dt>
                <dd>
                  <span className={getStatusClassName(latestPacket.generation_status)}>{latestPacket.generation_status}</span>
                </dd>
                <dt>Generated</dt>
                <dd>{formatDateTime(latestPacket.generated_at)}</dd>
                <dt>Packet Folder</dt>
                <dd>{latestPacket.packet_path}</dd>
                <dt>Resume PDF</dt>
                <dd>{latestPacket.tailored_resume_pdf_path || "Not available"}</dd>
                <dt>Generation Note</dt>
                <dd>{latestPacket.generation_error || "No errors recorded."}</dd>
              </dl>
              <div className="status-stack">
                {packets.slice(0, 3).map((packet) => (
                  <Link href={`/packets/${packet.id}`} key={packet.id} className="inline-link">
                    Packet #{packet.id} • {packet.generation_status} • {formatDateTime(packet.generated_at)}
                  </Link>
                ))}
              </div>
            </div>
          ) : !loadingPackets ? (
            <p className="subtle">No packets generated for this job yet.</p>
          ) : null}
        </article>

        <article className="panel">
          <h2>Autofill</h2>
          <p className="subtle">
            Stage 8 opens a visible Chromium browser, fills safe high-confidence fields, uploads packet files when
            available, and always stops before submit.
          </p>
          <AutofillControls
            job={job}
            initialPackets={packets}
            initialPacketId={latestPacket?.id ?? null}
            onAutofillComplete={refreshTrackedJob}
          />
        </article>

        <article className="panel">
          <h2>Required Skills</h2>
          <div className="pill-list">
            {job.required_skills.length > 0 ? (
              job.required_skills.map((skill) => (
                <span className="pill" key={skill}>
                  {skill}
                </span>
              ))
            ) : (
              <span className="subtle">None found.</span>
            )}
          </div>
        </article>

        <article className="panel">
          <h2>Preferred Skills</h2>
          <div className="pill-list">
            {job.preferred_skills.length > 0 ? (
              job.preferred_skills.map((skill) => (
                <span className="pill" key={skill}>
                  {skill}
                </span>
              ))
            ) : (
              <span className="subtle">None found.</span>
            )}
          </div>
        </article>

        <article className="panel">
          <h2>Responsibilities</h2>
          {renderItems(job.responsibilities)}
        </article>

        <article className="panel">
          <h2>Requirements</h2>
          {renderItems(job.requirements)}
        </article>

        <article className="panel">
          <h2>Education Requirements</h2>
          {renderItems(job.education_requirements)}
        </article>

        <article className="panel">
          <h2>Application Questions</h2>
          {renderItems(job.application_questions)}
        </article>
      </section>

      <section className="panel">
        <div className="section-title">
          <h2>Timeline</h2>
          <span className="subtle">{loadingTimeline ? "Loading..." : `${timeline.length} events`}</span>
        </div>
        {loadingTimeline ? (
          <p className="subtle">Loading timeline...</p>
        ) : timeline.length > 0 ? (
          <div className="timeline-list">
            {timeline.map((event) => (
              <article className="timeline-item" key={event.id}>
                <strong>{formatTimelineEvent(event)}</strong>
                <p className="subtle">{formatDateTime(event.event_time)}</p>
                {event.notes ? <p className="subtle">{event.notes}</p> : null}
              </article>
            ))}
          </div>
        ) : (
          <p className="subtle">No tracker activity has been recorded for this job yet.</p>
        )}
      </section>

      <section className="panel">
        <h2>Job Description</h2>
        <pre className="code-block">{job.job_description || "No job description stored."}</pre>
      </section>

      <section className="panel">
        <h2>Raw Parsed Data</h2>
        <pre className="code-block">{JSON.stringify(job.raw_parsed_data, null, 2)}</pre>
      </section>
    </div>
  );
}
