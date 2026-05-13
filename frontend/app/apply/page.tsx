"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  type ApplicationPacket,
  type AutofillFieldResult,
  type AutofillManualValue,
  type AutofillStatus,
  type FillApplicationResponse,
  type Job,
  type StartAiAssistedApplyResponse,
  type StartBasicAutofillResponse,
  closeAutofillSession,
  fillApplication,
  getAutofillStatus,
  getSavedJobs,
  markJobApplied,
  openApplication,
  startAiAssistedApply,
  startBasicAutofill,
} from "@/lib/api";

type BusyAction = "ai" | "basic" | "open" | "fill" | "close" | "applied" | null;

function isTestJob(job: Job) {
  const combined = `${job.source} ${job.application_status} ${job.company} ${job.title} ${job.url}`.toLowerCase();
  return ["local_test", "stage10_smoke", "autofill diagnostic", "careeragent test company", "test company", "localhost"].some((token) =>
    combined.includes(token),
  );
}

function formatScore(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function formatBasicStatus(status: string) {
  if (status === "manual_fallback_ready") return "Manual fallback ready";
  if (status === "ready") return "Ready";
  return status.replace(/_/g, " ");
}

function formatEnvironmentMode(status: AutofillStatus | null) {
  if (!status) return "Checking";
  if (status.visible_autofill_available) return "Visible local backend";
  if (status.backend_runtime === "docker" && status.browser_mode === "headed" && !status.headed_display_available) {
    return "Docker headed (no display)";
  }
  if (status.backend_runtime === "docker" && status.browser_mode === "headless") return "Headless Docker";
  return status.browser_mode === "headed" ? "Headed unavailable" : "Headless";
}

function packetHasWarnings(result: StartBasicAutofillResponse) {
  return Boolean(
    result.packet_id &&
      (
        result.packet_status === "completed_with_warnings" ||
        !result.packet?.tailored_resume_pdf_path ||
        (result.warnings || []).some((warning) => warning.toLowerCase().includes("packet"))
      ),
  );
}

function CopyApplicationValues({ values }: { values: AutofillManualValue[] }) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  if (values.length === 0) return null;

  async function copyValue(key: string, value: string) {
    await navigator.clipboard.writeText(value);
    setCopiedKey(key);
    window.setTimeout(() => setCopiedKey(null), 1200);
  }

  return (
    <details className="details-block">
      <summary>Copy values for manual application</summary>
      <div className="timeline-list">
        {values.map((item) => (
          <div className="timeline-item" key={item.key}>
            <strong>{item.label}</strong>
            <p className="subtle">{item.value}</p>
            <button className="button secondary compact" type="button" onClick={() => void copyValue(item.key, item.value)}>
              {copiedKey === item.key ? "Copied" : "Copy"}
            </button>
          </div>
        ))}
      </div>
    </details>
  );
}

function SetupInstructions({ instructions, command }: { instructions: string[]; command?: string | null }) {
  if (instructions.length === 0) return null;

  return (
    <section className="warning-panel stack">
      <h3>Enable Visible Autofill</h3>
      <ol className="list">
        {instructions.map((instruction) => (
          <li key={instruction}>
            {instruction.includes("&&") || instruction.includes("DATABASE_URL=") || instruction.includes("docker compose") ? (
              <pre className="code-block">{instruction}</pre>
            ) : (
              instruction
            )}
          </li>
        ))}
      </ol>
      {command ? <pre className="code-block">{command}</pre> : null}
    </section>
  );
}

function FieldResultsTable({ results }: { results: AutofillFieldResult[] }) {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const draftResults = results.filter((result) => result.action === "filled_ai_draft_review_required" && (result.value || result.value_preview));

  if (results.length === 0) return null;

  async function copyDraft(index: number, value: string) {
    await navigator.clipboard.writeText(value);
    setCopiedIndex(index);
    window.setTimeout(() => setCopiedIndex(null), 1200);
  }

  return (
    <details className="details-block" open>
      <summary>Field results</summary>
      <div className="table-wrap">
        <table className="data-table compact-table">
          <thead>
            <tr>
              <th>Field</th>
              <th>Category</th>
              <th>Action</th>
              <th>Value</th>
              <th>Reason</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {results.map((result, index) => (
              <tr key={`${result.field_key}-${index}`}>
                <td>{result.label || result.question || result.field_key}</td>
                <td>{result.category || result.field_key}</td>
                <td>{result.action || (result.filled ? "filled" : "skipped")}</td>
                <td>{result.value_preview || "-"}</td>
                <td>{result.reason}</td>
                <td>{Math.round((result.confidence || 0) * 100)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {draftResults.length > 0 ? (
        <div className="timeline-list">
          <p className="message warning">Review AI-drafted answers before submitting.</p>
          {draftResults.map((result, index) => (
            <div className="timeline-item" key={`${result.field_key}-draft-${index}`}>
              <strong>{result.label || result.question || "AI draft"}</strong>
              <p className="subtle">{result.value || result.value_preview}</p>
              <button className="button secondary compact" type="button" onClick={() => void copyDraft(index, result.value || result.value_preview || "")}>
                {copiedIndex === index ? "Copied" : "Copy draft"}
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </details>
  );
}

function AfterManualSubmit({
  busy,
  onMarkApplied,
}: {
  busy: BusyAction;
  onMarkApplied: () => void;
}) {
  return (
    <section className="warning-panel stack">
      <h3>After you submit manually</h3>
      <p className="subtle">Only click this after you personally submit the application.</p>
      <button className="button compact" type="button" onClick={onMarkApplied} disabled={busy !== null}>
        {busy === "applied" ? "Marking..." : "Mark Applied"}
      </button>
    </section>
  );
}

function FillApplicationResult({
  result,
  busy,
  onCloseSession,
}: {
  result: FillApplicationResponse;
  busy: BusyAction;
  onCloseSession: (sessionId: string) => void;
}) {
  const blockedActions = result.blocked_final_actions || result.blocked_actions || [];
  const aiDisabledQuestions = result.field_results.filter((field) => field.reason.toLowerCase().includes("ai disabled"));

  return (
    <section className={result.success ? "subtle-panel stack" : "warning-panel stack"}>
      <h3>{result.success ? "Application opened and filled in Chromium" : "Fill Application could not start"}</h3>
      <p className={result.success ? "message success" : "message warning"}>{result.message}</p>
      <dl className="key-value compact-key-value">
        <dt>Status</dt>
        <dd>{formatBasicStatus(result.status)}</dd>
        <dt>Opened URL</dt>
        <dd>{result.opened_url || "Not available"}</dd>
        <dt>Fields filled</dt>
        <dd>{result.fields_filled} of {result.fields_detected}</dd>
        <dt>Files uploaded</dt>
        <dd>{result.files_uploaded.length > 0 ? result.files_uploaded.join(", ") : "None"}</dd>
        <dt>Blocked final actions</dt>
        <dd>{blockedActions.length > 0 ? blockedActions.join(", ") : "None detected"}</dd>
        <dt>AI draft questions</dt>
        <dd>{result.field_results.filter((field) => field.action === "filled_ai_draft_review_required").length}</dd>
        <dt>Skipped fields</dt>
        <dd>{result.field_results.filter((field) => (field.action || "").startsWith("skipped") || (!field.filled && !field.action)).length}</dd>
        <dt>Session ID</dt>
        <dd>{result.session_id || "None"}</dd>
      </dl>
      {result.session_id ? (
        <button className="button secondary compact" type="button" onClick={() => onCloseSession(result.session_id || "")} disabled={busy !== null}>
          {busy === "close" ? "Closing..." : "Close Session"}
        </button>
      ) : null}
      {result.warnings.length > 0 ? (
        <details className="details-block">
          <summary>Warnings</summary>
          <ul className="list">
            {result.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </details>
      ) : null}
      {aiDisabledQuestions.length > 0 ? (
        <p className="message warning">
          Detected long-answer questions, but AI drafting is disabled. Draft manually or enable AI in{" "}
          <Link className="inline-link" href="/settings">Settings</Link>.
        </p>
      ) : null}
      <FieldResultsTable results={result.field_results || []} />
    </section>
  );
}

export default function ApplyPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [selectedPacket, setSelectedPacket] = useState<ApplicationPacket | null>(null);
  const [aiResult, setAiResult] = useState<StartAiAssistedApplyResponse | null>(null);
  const [basicResult, setBasicResult] = useState<StartBasicAutofillResponse | null>(null);
  const [fillResult, setFillResult] = useState<FillApplicationResponse | null>(null);
  const [status, setStatus] = useState<AutofillStatus | null>(null);
  const [showTestJobs, setShowTestJobs] = useState(false);
  const [fillSensitiveOptionalFields, setFillSensitiveOptionalFields] = useState(false);
  const [loading, setLoading] = useState(true);
  const [requestedJobId, setRequestedJobId] = useState<number | null>(null);
  const [busy, setBusy] = useState<BusyAction>(null);
  const [activeMode, setActiveMode] = useState<"ai" | "basic" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectionMessage, setSelectionMessage] = useState<string | null>(null);
  const [openFallbackUrl, setOpenFallbackUrl] = useState<string | null>(null);

  const visibleJobs = useMemo(() => jobs.filter((job) => (showTestJobs ? true : !isTestJob(job))), [jobs, showTestJobs]);
  const selectedJob = useMemo(() => jobs.find((job) => job.id === selectedJobId) ?? null, [jobs, selectedJobId]);
  const disabledReason = loading
    ? "Saved jobs are still loading."
    : !selectedJob
      ? "Choose a saved job to apply."
      : null;

  async function load(preferredJobId?: string | null) {
    setLoading(true);
    try {
      const [saved, autofillStatus] = await Promise.all([
        getSavedJobs(),
        getAutofillStatus(),
      ]);
      const parsedPreferredJobId = preferredJobId ? Number(preferredJobId) : null;
      const validPreferredJobId = parsedPreferredJobId && Number.isFinite(parsedPreferredJobId) ? parsedPreferredJobId : null;
      setJobs(saved);
      setStatus(autofillStatus);
      setRequestedJobId(validPreferredJobId);
      setSelectionMessage(null);
      setSelectedJobId((current) => {
        if (validPreferredJobId) {
          const requestedJob = saved.find((job) => job.id === validPreferredJobId);
          if (requestedJob) {
            if (isTestJob(requestedJob)) {
              setShowTestJobs(true);
            }
            return requestedJob.id;
          }
          setSelectionMessage("Could not find selected job. Choose another saved job.");
          return null;
        }
        if (current && saved.some((job) => job.id === current)) return current;
        return null;
      });
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load saved jobs.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const preferredJobId = new URLSearchParams(window.location.search).get("jobId");
    void load(preferredJobId);
  }, []);

  async function handleAiApply() {
    if (!selectedJob) return;
    setBusy("ai");
    setActiveMode(null);
    setSelectedPacket(null);
    setAiResult(null);
    setBasicResult(null);
    setFillResult(null);
    setOpenFallbackUrl(null);
    setMessage(null);
    setError(null);
    try {
      const response = await startAiAssistedApply(selectedJob.id);
      setAiResult(response);
      setBasicResult(null);
      setSelectedPacket(response.packet);
      if (response.autofill_environment) {
        setStatus(response.autofill_environment);
      }
      setActiveMode("ai");
      setMessage(response.message || "AI resume draft and application answers are ready to review.");
      if (response.visible_autofill_available && response.can_fill_application) {
        await runFillApplication(response.packet_id, true);
      }
      await load(String(response.job_id));
    } catch (applyError) {
      setError(applyError instanceof Error ? applyError.message : "Failed to start AI-assisted apply.");
    } finally {
      setBusy(null);
    }
  }

  async function handleBasicAutofill() {
    if (!selectedJob) return;
    setBusy("basic");
    setActiveMode(null);
    setAiResult(null);
    setBasicResult(null);
    setFillResult(null);
    setOpenFallbackUrl(null);
    setMessage(null);
    setError(null);
    try {
      const response = await startBasicAutofill(selectedJob.id, {
        fill_sensitive_optional_fields: fillSensitiveOptionalFields,
      });
      setBasicResult(response);
      setSelectedPacket(response.packet || null);
      setFillResult(null);
      setActiveMode("basic");
      setMessage(response.message);
      if (response.visible_autofill_available && response.can_fill_application) {
        await runFillApplication(response.packet_id ?? null, false);
      }
    } catch (basicError) {
      setError(basicError instanceof Error ? basicError.message : "Failed to start Basic Autofill.");
    } finally {
      setBusy(null);
    }
  }

  async function handleOpenApplication() {
    if (!selectedJob) return;
    setBusy("open");
    setMessage(null);
    setError(null);
    setOpenFallbackUrl(null);
    try {
      const response = await openApplication(selectedJob.id);
      const openedWindow = window.open(response.url, "_blank", "noopener,noreferrer");
      if (!openedWindow) {
        setOpenFallbackUrl(response.url);
        setMessage("Popup blocked. Use the application link below. CareerAgent cannot fill this tab. Complete it manually, then return and click Mark Applied.");
      } else {
        setMessage(response.message || "Application opened without autofill. Complete it manually, then return and click Mark Applied.");
      }
      await load(String(response.job_id));
    } catch (openError) {
      setError(openError instanceof Error ? openError.message : "Failed to open the application link.");
    } finally {
      setBusy(null);
    }
  }

  async function runFillApplication(packetId: number | null = null, aiAssistedApply = false) {
    if (!selectedJob) return;
    setBusy("fill");
    setMessage("Opening visible Chromium and filling application...");
    setError(null);
    setFillResult(null);
    try {
      const response = await fillApplication(selectedJob.id, {
        packet_id: packetId,
        allow_base_resume_upload: true,
        fill_sensitive_optional_fields: fillSensitiveOptionalFields,
        keep_browser_open: true,
        ai_assisted_apply: aiAssistedApply,
      });
      setFillResult(response);
      setMessage(response.success ? "Application opened and filled in Chromium. Review missing fields and submit manually." : response.message);
      await load(String(response.job_id));
    } catch (fillError) {
      setError(fillError instanceof Error ? fillError.message : "Failed to fill the application in Chromium.");
    } finally {
      setBusy(null);
    }
  }

  async function handleFillApplication() {
    if (!basicResult) return;
    await runFillApplication(basicResult.packet_id ?? null, false);
  }

  async function handleCloseSession(sessionId: string) {
    if (!sessionId) return;
    setBusy("close");
    setError(null);
    try {
      await closeAutofillSession(sessionId);
      setMessage("Visible Chromium session closed.");
      setFillResult((current) => current ? { ...current, session_id: null } : current);
      await load(selectedJob ? String(selectedJob.id) : null);
    } catch (closeError) {
      setError(closeError instanceof Error ? closeError.message : "Failed to close the Chromium session.");
    } finally {
      setBusy(null);
    }
  }

  async function handleMarkApplied() {
    if (!selectedJob) return;
    setBusy("applied");
    setMessage(null);
    setError(null);
    try {
      const response = await markJobApplied(selectedJob.id);
      setMessage(response.message);
      setActiveMode(null);
      setSelectedPacket(null);
      setAiResult(null);
      setBasicResult(null);
      setFillResult(null);
      setSelectedJobId(null);
      await load(null);
    } catch (markError) {
      setError(markError instanceof Error ? markError.message : "Failed to mark this job applied.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="page">
      <section className="panel">
        <div className="section-title">
          <h2>Select Job</h2>
          <Link href="/jobs?tab=saved" className="button secondary compact">Saved Jobs</Link>
        </div>
        <div className="filter-row">
          <label className="field-group">
            <span>Saved job</span>
            <select
              className="input"
              value={selectedJobId ?? ""}
              onChange={(event) => {
                const nextJobId = event.target.value ? Number(event.target.value) : null;
                setSelectedJobId(nextJobId);
                setRequestedJobId(nextJobId);
                setSelectionMessage(null);
                if (nextJobId) {
                  window.history.replaceState(null, "", `/apply?jobId=${nextJobId}`);
                } else {
                  window.history.replaceState(null, "", "/apply");
                }
                setActiveMode(null);
                setSelectedPacket(null);
                setAiResult(null);
                setBasicResult(null);
                setFillResult(null);
                setOpenFallbackUrl(null);
              }}
              disabled={loading}
            >
              <option value="">Select a saved job</option>
              {visibleJobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.company} - {job.title} - {job.location} - match {formatScore(job.resume_match_score)} - {job.verification_status}
                </option>
              ))}
            </select>
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={showTestJobs} onChange={(event) => setShowTestJobs(event.target.checked)} />
            Show test/demo jobs
          </label>
        </div>
        {selectedJob ? (
          <>
            <div className="meta-stack">
              <span className="status-tag">Match {formatScore(selectedJob.resume_match_score)}</span>
              <span className={`status-tag status-${selectedJob.verification_status.replace(/_/g, "-")}`}>{selectedJob.verification_status}</span>
              <span className="status-tag">{selectedJob.role_category || "Role unknown"}</span>
            </div>
            <dl className="key-value compact-key-value">
              <dt>Company</dt>
              <dd>{selectedJob.company || "Unknown"}</dd>
              <dt>Title</dt>
              <dd>{selectedJob.title || "Unknown"}</dd>
              <dt>Location</dt>
              <dd>{selectedJob.location || "Unknown"}</dd>
              <dt>Application URL</dt>
              <dd>{selectedJob.url || "No application URL saved"}</dd>
              <dt>Selected job ID</dt>
              <dd>#{selectedJob.id}</dd>
            </dl>
          </>
        ) : !loading ? (
          <p className="subtle">
            {selectionMessage || (requestedJobId ? "Could not find selected job. Choose another saved job." : "Choose a saved job to apply.")}
          </p>
        ) : null}
      </section>

      <section className="panel">
        <h2>Choose Apply Mode</h2>
        <div className="panel-grid">
          <article className="subtle-panel workflow-step">
            <h3>Apply with AI Resume + Questions</h3>
            <p className="subtle">
              Generate or tailor a resume draft, draft long application answers, then open/fill the application. Uses AI only if enabled in Settings.
            </p>
            <button className="button" type="button" onClick={() => void handleAiApply()} disabled={Boolean(disabledReason) || busy !== null} title={disabledReason || undefined}>
              {busy === "ai" ? "Preparing AI-assisted application..." : "Start AI-assisted apply"}
            </button>
          </article>
          <article className="subtle-panel workflow-step">
            <h3>Basic Autofill</h3>
            <p className="subtle">
              Prepare profile values, then fill the real application in visible Chromium when available.
            </p>
            <dl className="key-value compact-key-value">
              <dt>Mode</dt>
              <dd>{formatEnvironmentMode(status)}</dd>
              <dt>Backend</dt>
              <dd>{status?.backend_runtime || "Checking"}</dd>
              <dt>.env loaded</dt>
              <dd>{status ? (status.env_file_loaded ? "Yes" : "No") : "Checking"}</dd>
              <dt>Visible autofill</dt>
              <dd>{status?.visible_autofill_available ? "Available" : "Not available"}</dd>
              <dt>Display</dt>
              <dd>{status ? (status.headed_display_available ? "Available" : "Not available") : "Checking"}</dd>
              <dt>Chromium installed</dt>
              <dd>{status ? (status.chromium_installed ? "Yes" : "No") : "Checking"}</dd>
            </dl>
            <button className="button secondary" type="button" onClick={() => void handleBasicAutofill()} disabled={Boolean(disabledReason) || busy !== null} title={disabledReason || undefined}>
              {busy === "basic" ? "Preparing autofill..." : status?.visible_autofill_available ? "Start Basic Autofill and Open Chromium" : "Start Basic Autofill"}
            </button>
          </article>
        </div>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={fillSensitiveOptionalFields}
            onChange={(event) => setFillSensitiveOptionalFields(event.target.checked)}
          />
          Fill voluntary EEO dropdowns as “Decline to self-identify” when that option exists.
        </label>
        {status && !status.visible_autofill_available ? <p className="message warning">{status.message}</p> : null}
        {disabledReason ? <p className="message warning">{disabledReason}</p> : null}
        <p className="message warning">Review everything and click Submit yourself. CareerAgent never submits.</p>
        {message ? <p className="message success">{message}</p> : null}
        {openFallbackUrl ? (
          <p className="message warning">
            <a className="inline-link" href={openFallbackUrl} target="_blank" rel="noreferrer">
              Open application link
            </a>
          </p>
        ) : null}
        {error ? (
          <p className="message error">
            {error}
          </p>
        ) : null}
      </section>

      <section className="panel">
        <div className="section-title">
          <h2>Action Results</h2>
          {selectedPacket ? <Link className="button secondary compact" href={`/packets/${selectedPacket.id}`}>Review Packet</Link> : null}
        </div>
        {busy === "ai" ? <p className="message">Preparing AI-assisted application...</p> : null}
        {busy === "basic" ? <p className="message">Preparing autofill...</p> : null}
        {busy === "open" ? <p className="message">Opening application without autofill...</p> : null}
        {busy === "fill" ? <p className="message">Opening visible Chromium and filling application...</p> : null}
        {!activeMode && !busy ? <p className="subtle">Choose an apply mode after selecting a saved job.</p> : null}
        {activeMode === "ai" && aiResult ? (
          <section className="subtle-panel stack">
            <h3>AI-assisted apply prepared</h3>
            <dl className="key-value compact-key-value">
              <dt>Packet status</dt>
              <dd>{aiResult.packet_status}</dd>
              <dt>AI status</dt>
              <dd>{aiResult.ai_used ? `Used ${aiResult.provider || "selected provider"}` : "No external AI used"}</dd>
              <dt>Question draft status</dt>
              <dd>{aiResult.packet.application_questions_path ? "Drafted" : "Not available"}</dd>
              <dt>Resume draft</dt>
              <dd>{aiResult.packet.tailored_resume_tex_path || aiResult.packet.tailored_resume_pdf_path || "Not available"}</dd>
            </dl>
            {aiResult.warnings.length > 0 ? (
              <div className="message warning">
                <strong>Warnings</strong>
                <ul className="list">
                  {aiResult.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div className="button-row">
              <Link className="button secondary compact" href={`/packets/${aiResult.packet_id}`}>
                Review Packet
              </Link>
              {selectedJob?.url ? (
                <button className="button secondary compact" type="button" onClick={() => void handleOpenApplication()} disabled={busy !== null}>
                  {busy === "open" ? "Opening..." : "Open Manually Without Autofill"}
                </button>
              ) : null}
              {aiResult.visible_autofill_available && aiResult.can_fill_application ? (
                <button className="button compact" type="button" onClick={() => void runFillApplication(aiResult.packet_id, true)} disabled={busy !== null}>
                  {busy === "fill" ? "Opening Chromium..." : "Fill Application in Chromium"}
                </button>
              ) : (
                <span className="status-tag">Fill Application requires visible local backend.</span>
              )}
            </div>
            {!aiResult.visible_autofill_available ? (
              <SetupInstructions instructions={aiResult.setup_instructions || []} command={aiResult.setup_command || null} />
            ) : null}
            {fillResult ? (
              <FillApplicationResult result={fillResult} busy={busy} onCloseSession={(sessionId) => void handleCloseSession(sessionId)} />
            ) : null}
            {selectedJob ? <AfterManualSubmit busy={busy} onMarkApplied={() => void handleMarkApplied()} /> : null}
          </section>
        ) : null}
        {activeMode === "basic" && basicResult ? (
          <section className={basicResult.success ? "subtle-panel stack" : "warning-panel stack"}>
            <h3>
              {basicResult.visible_autofill_available
                ? "Basic Autofill is ready"
                : "Visible browser required for autofill"}
            </h3>
            {!basicResult.visible_autofill_available ? (
              <p className="subtle">
                To open the application already filled out, CareerAgent must run a visible Playwright browser. A normal
                browser tab can be opened manually, but it cannot be filled by the backend after it opens.
              </p>
            ) : (
              <p className="subtle">
                CareerAgent can open the real application page in visible Chromium, fill safe fields, upload available
                files, and leave the browser open for your manual review.
              </p>
            )}
            <dl className="key-value compact-key-value">
              <dt>Status</dt>
              <dd>{formatBasicStatus(basicResult.status)}</dd>
              <dt>Open URL</dt>
              <dd>{basicResult.open_url || "Not available"}</dd>
              <dt>Browser mode</dt>
              <dd>{basicResult.browser_mode}</dd>
              <dt>Fill Application</dt>
              <dd>{basicResult.can_fill_application ? "Available" : "Fill Application requires visible local backend."}</dd>
              <dt>Packet</dt>
              <dd>{basicResult.packet_id ? `Packet #${basicResult.packet_id} - ${basicResult.packet_status || "available"}` : basicResult.packet_status || "No packet selected"}</dd>
              <dt>Upload status</dt>
              <dd>{basicResult.upload_status || "Manual review required before any upload"}</dd>
            </dl>
            {basicResult.packet_id ? (
              <div className={packetHasWarnings(basicResult) ? "message warning" : "message success"}>
                <strong>Packet available: Packet #{basicResult.packet_id}</strong>
                {packetHasWarnings(basicResult) ? <p>Packet has warnings. Review before uploading manually.</p> : null}
              </div>
            ) : null}
            {basicResult.warnings && basicResult.warnings.length > 0 ? (
              <div className="message warning">
                <strong>Warnings</strong>
                <ul className="list">
                  {basicResult.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div className="button-row">
              {basicResult.visible_autofill_available ? (
                <button className="button compact" type="button" onClick={() => void handleFillApplication()} disabled={busy !== null || !basicResult.can_fill_application}>
                  {busy === "fill" ? "Opening Chromium..." : "Fill Application in Chromium"}
                </button>
              ) : null}
              {basicResult.open_url ? (
                <button className="button secondary compact" type="button" onClick={() => void handleOpenApplication()} disabled={busy !== null}>
                  {busy === "open" ? "Opening..." : "Open Manually Without Autofill"}
                </button>
              ) : null}
              {basicResult.packet_id ? (
                <Link className="button secondary compact" href={`/packets/${basicResult.packet_id}`}>
                  Review Packet
                </Link>
              ) : null}
              {basicResult.visible_autofill_available ? (
                <span className="status-tag status-open">Visible Chromium available</span>
              ) : (
                <span className="status-tag">Fill Application requires visible local backend.</span>
              )}
            </div>
            {!basicResult.visible_autofill_available ? (
              <>
                <p className="subtle">
                  This opens your normal browser. CareerAgent cannot fill this tab. Use it only if you want to complete
                  the application manually.
                </p>
                <CopyApplicationValues values={basicResult.manual_values || []} />
                <SetupInstructions instructions={basicResult.setup_instructions || []} command={basicResult.setup_command || null} />
              </>
            ) : null}
            {fillResult ? (
              <FillApplicationResult result={fillResult} busy={busy} onCloseSession={(sessionId) => void handleCloseSession(sessionId)} />
            ) : null}
            {selectedJob ? <AfterManualSubmit busy={busy} onMarkApplied={() => void handleMarkApplied()} /> : null}
          </section>
        ) : null}
      </section>
    </div>
  );
}
