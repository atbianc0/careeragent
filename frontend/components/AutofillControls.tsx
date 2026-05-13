"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import {
  type ApplicationPacket,
  type AutofillManualValue,
  type AutofillStartResponse,
  type Job,
  autofillScreenshotUrl,
  closeAutofillSession,
  getPacketsForJob,
  openApplicationLink,
  startAutofill,
} from "@/lib/api";

type AutofillControlsProps = {
  job: Job;
  initialPackets?: ApplicationPacket[];
  initialPacketId?: number | null;
  configuredBrowserMode?: string;
  visibleBrowserAvailable?: boolean;
  onAutofillComplete?: () => Promise<void> | void;
};

const EMPTY_PACKETS: ApplicationPacket[] = [];

const VISIBLE_AUTOFILL_SETUP = `docker compose stop backend
docker compose up -d db frontend

cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
DATABASE_URL="postgresql://careeragent:careeragent@localhost:5432/careeragent" PLAYWRIGHT_HEADLESS=false python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000`;

const CHROMIUM_INSTALL_COMMAND = `cd backend
source .venv/bin/activate
python -m playwright install chromium`;

function getPacketsKey(packets: ApplicationPacket[]) {
  return packets.map((packet) => `${packet.id}:${packet.generation_status}:${packet.updated_at}`).join(",");
}

function getPreferredPacketId(packets: ApplicationPacket[], initialPacketId: number | null) {
  if (initialPacketId !== null && packets.some((packet) => packet.id === initialPacketId)) {
    return initialPacketId;
  }
  return packets[0]?.id ?? null;
}

function CopyableApplicationValues({ values, diagnostic = false }: { values: AutofillManualValue[]; diagnostic?: boolean }) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  if (values.length === 0) {
    return null;
  }

  async function copyValue(key: string, value: string) {
    await navigator.clipboard.writeText(value);
    setCopiedKey(key);
    window.setTimeout(() => setCopiedKey(null), 1200);
  }

  return (
    <section className="stack">
      <h4>Copyable Application Values</h4>
      <p className="subtle">
        {diagnostic
          ? "These are the values used by the hidden diagnostic session. Open a visible browser or your normal browser to apply for real."
          : "These values can help if you choose to finish the application manually."}
      </p>
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
    </section>
  );
}

function VisibleAutofillSetup({ showTitle = true }: { showTitle?: boolean }) {
  return (
    <section className="warning-panel">
      {showTitle ? <strong>Visible local backend required</strong> : null}
      <p>Visible autofill is not available in the current Docker/headless environment.</p>
      <pre className="code-block">{VISIBLE_AUTOFILL_SETUP}</pre>
    </section>
  );
}

function ChromiumMissingSetup({ summary }: { summary: AutofillStartResponse }) {
  return (
    <section className="warning-panel">
      <strong>Playwright Chromium is missing</strong>
      <p>{summary.message}</p>
      <pre className="code-block">{summary.fix_command || CHROMIUM_INSTALL_COMMAND}</pre>
      <p className="subtle">
        {summary.details || "Run this from the same activated backend virtualenv that starts uvicorn."}
      </p>
    </section>
  );
}

function AutofillResult({ summary, onSessionClosed }: { summary: AutofillStartResponse; onSessionClosed?: () => Promise<void> | void }) {
  const [closingSession, setClosingSession] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const isDiagnostic = summary.session_mode === "headless_test";
  const isVisibleRequired =
    summary.status === "visible_browser_required" ||
    summary.status === "visible_browser_unavailable" ||
    summary.status === "browser_display_unavailable";
  const isChromiumMissing = summary.status === "playwright_chromium_missing";
  const noPageLoadedStatuses = new Set([
    "browser_closed",
    "invalid_or_truncated_url",
    "navigation_failed",
    "page_blocked_or_unavailable",
    "workday_manual_required",
  ]);
  const hideRunStats = isVisibleRequired || isChromiumMissing || noPageLoadedStatuses.has(summary.status);

  async function copyUrl() {
    await navigator.clipboard.writeText(summary.opened_url);
    setCopiedUrl(true);
    window.setTimeout(() => setCopiedUrl(false), 1200);
  }

  async function handleCloseSession() {
    if (!summary.session_id) {
      return;
    }
    setClosingSession(true);
    try {
      await closeAutofillSession(summary.session_id);
      await onSessionClosed?.();
    } finally {
      setClosingSession(false);
    }
  }

  return (
    <div className="stack">
      <h3>{isDiagnostic ? "Headless Diagnostic Result" : "Fill Application Result"}</h3>

      {isDiagnostic ? (
        <section className="warning-panel">
          <strong>Diagnostic only</strong>
          <p>
            This ran in a hidden browser to test field detection. You cannot continue from this session, and CareerAgent
            did not mark the job as applied or autofill completed.
          </p>
        </section>
      ) : null}

      {isVisibleRequired ? (
        <>
          <VisibleAutofillSetup />
          <p className="subtle">Use Open in Browser as the manual fallback in this environment.</p>
        </>
      ) : null}

      {isChromiumMissing ? <ChromiumMissingSetup summary={summary} /> : null}

      {summary.status === "workday_manual_required" ? (
        <section className="warning-panel">
          <strong>Workday manual flow recommended</strong>
          <p>CareerAgent could not open this Workday page with Playwright. Use Open in Browser or paste the direct application form URL.</p>
          <div className="button-row">
            <a className="button secondary compact" href={summary.opened_url} target="_blank" rel="noreferrer">
              Open in Browser
            </a>
            <button className="button secondary compact" type="button" onClick={() => void copyUrl()}>
              {copiedUrl ? "Copied" : "Copy URL"}
            </button>
            <Link className="button secondary compact" href={`/jobs/${summary.job_id}`}>
              View Details
            </Link>
          </div>
        </section>
      ) : null}

      {summary.status === "invalid_or_truncated_url" ? (
        <section className="warning-panel">
          <strong>This URL looks truncated</strong>
          <p>This URL looks truncated. Re-import the job with the full URL.</p>
          <div className="button-row">
            <button className="button secondary compact" type="button" onClick={() => void copyUrl()}>
              {copiedUrl ? "Copied" : "Copy URL"}
            </button>
            <Link className="button secondary compact" href={`/jobs/${summary.job_id}`}>
              View Details
            </Link>
          </div>
        </section>
      ) : null}

      {summary.status === "navigation_failed" || summary.status === "page_blocked_or_unavailable" ? (
        <section className="warning-panel">
          <strong>CareerAgent could not open this page in Chromium</strong>
          <p>{summary.message}</p>
          <div className="button-row">
            <a className="button secondary compact" href={summary.opened_url} target="_blank" rel="noreferrer">
              Open in Browser
            </a>
            <button className="button secondary compact" type="button" onClick={() => void copyUrl()}>
              {copiedUrl ? "Copied" : "Copy URL"}
            </button>
            <Link className="button secondary compact" href={`/jobs/${summary.job_id}`}>
              Back to Job
            </Link>
          </div>
        </section>
      ) : null}

      {summary.status === "browser_closed" ? (
        <section className="warning-panel">
          <strong>The browser was closed</strong>
          <p>The browser was closed. Start a new Fill Application session if needed.</p>
        </section>
      ) : null}

      {summary.status === "no_fields_detected" ? (
        <section className="warning-panel">
          <strong>No form fields detected</strong>
          <p>{summary.no_fields_reason || "This may not be the actual application form."}</p>
          <p>{summary.recommended_next_action || "Use Open in Browser, use the local test form, or save a direct application form URL."}</p>
        </section>
      ) : null}

      {summary.status === "no_fields_filled" ? (
        <section className="warning-panel">
          <strong>No fields were safely filled</strong>
          <p>
            CareerAgent detected fields but did not find enough high-confidence truthful values to fill them. Review the
            field results, generate a packet if files are missing, or use Open in Browser.
          </p>
        </section>
      ) : null}

      {!hideRunStats ? (
        <dl className="key-value compact-key-value">
          <dt>Status</dt>
          <dd>{summary.status}</dd>
          <dt>Mode</dt>
          <dd>{isDiagnostic ? "Headless diagnostic" : summary.browser_mode}</dd>
          <dt>Can Continue</dt>
          <dd>{summary.can_continue_in_browser ? "Yes" : "No"}</dd>
          <dt>Session ID</dt>
          <dd>{summary.session_id || "None"}</dd>
          <dt>Opened URL</dt>
          <dd>{summary.opened_url}</dd>
          <dt>Fields Detected</dt>
          <dd>{summary.fields_detected}</dd>
          <dt>{isDiagnostic ? "Diagnostic Fields Filled" : "Fields Filled"}</dt>
          <dd>{summary.fields_filled}</dd>
          <dt>Fields Skipped</dt>
          <dd>{summary.fields_skipped}</dd>
          <dt>Files Uploaded</dt>
          <dd>{summary.files_uploaded.length > 0 ? summary.files_uploaded.join(", ") : "None uploaded"}</dd>
          <dt>Screenshot</dt>
          <dd>
            {summary.screenshot_url ? (
              <a className="inline-link" href={autofillScreenshotUrl(summary.screenshot_url)} target="_blank" rel="noreferrer">
                View screenshot
              </a>
            ) : (
              "Not available"
            )}
          </dd>
        </dl>
      ) : null}

      {summary.status === "visible_session_started" && summary.session_id ? (
        <section className="warning-panel">
          <strong>Visible browser opened</strong>
          <p>Continue in Chromium and submit manually when you are ready.</p>
          <button className="button secondary compact" type="button" onClick={() => void handleCloseSession()} disabled={closingSession}>
            {closingSession ? "Closing..." : "Close Session"}
          </button>
        </section>
      ) : null}

      {summary.screenshot_url ? (
        <figure className="stack">
          <figcaption className="subtle">This screenshot shows what the hidden diagnostic browser saw.</figcaption>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="screenshot-preview" src={autofillScreenshotUrl(summary.screenshot_url)} alt="Headless diagnostic screenshot" />
        </figure>
      ) : null}

      {!hideRunStats ? <CopyableApplicationValues values={summary.manual_values} diagnostic={isDiagnostic} /> : null}

      {!hideRunStats && summary.blocked_actions.length > 0 ? (
        <>
          <h4>Blocked Final Actions</h4>
          <ul className="list">
            {summary.blocked_actions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </>
      ) : null}

      {!hideRunStats && summary.warnings.length > 0 ? (
        <>
          <h4>Warnings</h4>
          <ul className="list">
            {summary.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </>
      ) : null}

      {!hideRunStats ? (
        <details className="details-block">
          <summary>Field Results</summary>
          <div className="timeline-list">
            {summary.field_results.map((result, index) => (
              <div className="timeline-item" key={`${result.field_key}-${index}`}>
                <strong>
                  {result.label || result.field_key} - {result.filled ? "filled" : "skipped"}
                </strong>
                <p className="subtle">
                  {result.field_key} - confidence {result.confidence}
                </p>
                <p className="subtle">{result.reason}</p>
              </div>
            ))}
          </div>
        </details>
      ) : null}
    </div>
  );
}

export function AutofillControls({
  job,
  initialPackets = EMPTY_PACKETS,
  initialPacketId = null,
  configuredBrowserMode = "headless",
  visibleBrowserAvailable = false,
  onAutofillComplete,
}: AutofillControlsProps) {
  const initialPacketsKey = useMemo(() => getPacketsKey(initialPackets), [initialPackets]);
  const [packets, setPackets] = useState<ApplicationPacket[]>(() => initialPackets);
  const [loadingPackets, setLoadingPackets] = useState(initialPackets.length === 0);
  const [packetError, setPacketError] = useState<string | null>(null);
  const [selectedPacketId, setSelectedPacketId] = useState<number | null>(
    () => getPreferredPacketId(initialPackets, initialPacketId),
  );
  const [allowBaseResumeUpload, setAllowBaseResumeUpload] = useState(false);
  const [fillSensitiveOptionalFields, setFillSensitiveOptionalFields] = useState(false);
  const [fillSummary, setFillSummary] = useState<AutofillStartResponse | null>(null);
  const [diagnosticSummary, setDiagnosticSummary] = useState<AutofillStartResponse | null>(null);
  const [busyAction, setBusyAction] = useState<"open" | "fill" | "diagnostic" | null>(null);
  const [openMessage, setOpenMessage] = useState<string | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);
  const [fillMessage, setFillMessage] = useState<string | null>(null);
  const [fillError, setFillError] = useState<string | null>(null);
  const packetsKey = useMemo(() => getPacketsKey(packets), [packets]);
  const canUseApplicationUrl = Boolean(job.url.trim());
  const isHeadlessMode = configuredBrowserMode === "headless";

  useEffect(() => {
    setPackets(initialPackets);
    setSelectedPacketId(getPreferredPacketId(initialPackets, initialPacketId));
    setPacketError(null);
    setFillSummary(null);
    setDiagnosticSummary(null);
    setOpenMessage(null);
    setOpenError(null);
    setFillMessage(null);
    setFillError(null);
  }, [job.id, initialPacketId, initialPacketsKey, initialPackets]);

  useEffect(() => {
    let cancelled = false;

    async function loadPackets() {
      setLoadingPackets(true);
      setPacketError(null);
      setPackets((currentPackets) => {
        if (getPacketsKey(currentPackets) === initialPacketsKey) {
          return currentPackets;
        }
        return initialPackets;
      });

      try {
        const response = await getPacketsForJob(job.id);
        if (cancelled) {
          return;
        }
        setPackets((currentPackets) => {
          if (getPacketsKey(currentPackets) === getPacketsKey(response)) {
            return currentPackets;
          }
          return response;
        });
        setPacketError(null);
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setPacketError(loadError instanceof Error ? loadError.message : "Failed to load packets for this job.");
      } finally {
        if (!cancelled) {
          setLoadingPackets(false);
        }
      }
    }

    void loadPackets();

    return () => {
      cancelled = true;
    };
  }, [job.id, initialPacketsKey]);

  useEffect(() => {
    setSelectedPacketId((currentSelected) => {
      if (currentSelected !== null && packets.some((packet) => packet.id === currentSelected)) {
        return currentSelected;
      }
      return getPreferredPacketId(packets, initialPacketId);
    });
  }, [job.id, initialPacketId, packetsKey]);

  useEffect(() => {
    setFillSummary(null);
    setDiagnosticSummary(null);
    setOpenMessage(null);
    setOpenError(null);
    setFillMessage(null);
    setFillError(null);
  }, [job.id]);

  function buildPayload() {
    return {
      job_id: job.id,
      packet_id: selectedPacketId,
      allow_base_resume_upload: allowBaseResumeUpload,
      fill_sensitive_optional_fields: fillSensitiveOptionalFields,
    };
  }

  async function handleOpenInBrowser() {
    setBusyAction("open");
    setOpenMessage(null);
    setOpenError(null);
    setFillMessage(null);
    setFillError(null);
    setFillSummary(null);

    try {
      const response = await openApplicationLink(job.id);
      window.open(response.url, "_blank", "noopener,noreferrer");
      setOpenMessage("Application opened in your browser. CareerAgent logged this. Complete and submit manually, then return and mark applied.");
      await onAutofillComplete?.();
    } catch (error) {
      setOpenError(error instanceof Error ? error.message : "Failed to open the application link.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleFillApplication() {
    setBusyAction("fill");
    setOpenMessage(null);
    setOpenError(null);
    setFillMessage(null);
    setFillError(null);
    setFillSummary(null);

    try {
      setFillMessage(`Starting Fill Application for Job #${job.id}: ${job.title}`);
      const response = await startAutofill({
        ...buildPayload(),
        mode: "visible_review",
        keep_browser_open: true,
      });
      setFillSummary(response);
      if (
        response.status === "visible_browser_required" ||
        response.status === "browser_display_unavailable" ||
        response.status === "playwright_chromium_missing" ||
        response.status === "workday_manual_required" ||
        response.status === "invalid_or_truncated_url" ||
        response.status === "navigation_failed" ||
        response.status === "page_blocked_or_unavailable" ||
        response.status === "browser_closed"
      ) {
        setFillMessage(null);
        setFillError(response.message);
      } else if (response.status === "visible_session_started") {
        setFillMessage("Visible browser opened. Continue in Chromium and submit manually.");
      } else {
        setFillMessage(response.message);
      }
      await onAutofillComplete?.();
    } catch (error) {
      setFillError(error instanceof Error ? error.message : "Failed to start visible browser autofill.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRunHeadlessDiagnostic() {
    setBusyAction("diagnostic");
    setFillMessage(null);
    setFillError(null);
    setDiagnosticSummary(null);

    try {
      const response = await startAutofill({
        ...buildPayload(),
        mode: "headless_test",
        keep_browser_open: false,
        keep_open_seconds: 0,
      });
      setDiagnosticSummary(response);
      await onAutofillComplete?.();
    } catch (error) {
      setFillError(error instanceof Error ? error.message : "Failed to run the headless diagnostic.");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="stack">
      <p className="subtle">
        Use Open in Browser for manual applications. Use Fill Application when visible browser autofill is available.
        CareerAgent fills safe fields, stops before submit, and leaves the browser open for you.
      </p>

      {!canUseApplicationUrl ? <p className="message error">No application URL is available for this job.</p> : null}
      <section className="subtle-panel">
        <h3>Selected Job</h3>
        <p className="subtle">
          #{job.id} • {job.company} • {job.title}
        </p>
        <p className="subtle">{job.url}</p>
      </section>
      {packetError ? <p className="message error">{packetError}</p> : null}

      {!loadingPackets && packets.length === 0 ? (
        <section className="warning-panel">
          <strong>No application packet selected</strong>
          <p>Generate a packet before Fill Application if you want CareerAgent to upload a tailored resume/cover letter.</p>
          <Link className="button secondary compact" href={`/jobs/${job.id}`}>
            View Details
          </Link>
        </section>
      ) : null}

      <div className="filter-row">
        <label className="field-group">
          <span>Packet</span>
          <select
            className="input"
            value={selectedPacketId ?? ""}
            onChange={(event) => setSelectedPacketId(event.target.value ? Number(event.target.value) : null)}
            disabled={loadingPackets || busyAction !== null}
          >
            <option value="">Latest packet / none selected</option>
            {packets.map((packet) => (
              <option key={packet.id} value={packet.id}>
                Packet #{packet.id} - {packet.generation_status}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="stack">
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={allowBaseResumeUpload}
            onChange={(event) => setAllowBaseResumeUpload(event.target.checked)}
            disabled={busyAction !== null}
          />
          <span>Allow compiled base resume upload if no packet resume PDF exists</span>
        </label>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={fillSensitiveOptionalFields}
            onChange={(event) => setFillSensitiveOptionalFields(event.target.checked)}
            disabled={busyAction !== null}
          />
          <span>Fill sensitive optional EEO fields only with "Prefer not to answer" when available</span>
        </label>
        {fillSensitiveOptionalFields ? (
          <p className="subtle">
            Sensitive optional fields stay conservative. CareerAgent still skips SSN, date of birth, and fields it
            cannot classify safely.
          </p>
        ) : null}
      </div>

      <section className="panel-grid">
        <article className="subtle-panel workflow-step">
          <h3>Open in Browser</h3>
          <p className="subtle">Manual. Opens your normal browser. No autofill.</p>
          <button className="button secondary" type="button" onClick={() => void handleOpenInBrowser()} disabled={!canUseApplicationUrl || busyAction !== null}>
            {busyAction === "open" ? "Opening..." : "Open in Browser"}
          </button>
        </article>

        <article className="subtle-panel workflow-step">
          <h3>Fill Application</h3>
          <p className="subtle">Visible browser autofill. Fills safe fields and leaves the browser open.</p>
          {!visibleBrowserAvailable ? (
            <p className="subtle">Visible autofill requires local backend. Current mode: {isHeadlessMode ? "headless Docker" : "headed unavailable"}.</p>
          ) : null}
          <button className="button" type="button" onClick={() => void handleFillApplication()} disabled={!canUseApplicationUrl || busyAction !== null}>
            {busyAction === "fill" ? "Filling..." : "Fill Application"}
          </button>
        </article>
      </section>

      {openMessage ? <p className="message success">{openMessage}</p> : null}
      {openError ? <p className="message error">{openError}</p> : null}
      {fillMessage ? <p className="message success">{fillMessage}</p> : null}
      {fillError ? <p className="message error">{fillError}</p> : null}

      {fillSummary ? <AutofillResult summary={fillSummary} onSessionClosed={onAutofillComplete} /> : null}

      <details className="details-block">
        <summary>Advanced diagnostics</summary>
        <div className="stack">
          <p className="subtle">
            Runs in a hidden browser to test field detection. You cannot continue from this session. Not for real applications.
          </p>
          <button
            className="button secondary"
            type="button"
            onClick={() => void handleRunHeadlessDiagnostic()}
            disabled={!canUseApplicationUrl || busyAction !== null}
          >
            {busyAction === "diagnostic" ? "Running..." : "Run Headless Field Detection Test"}
          </button>
          {diagnosticSummary ? <AutofillResult summary={diagnosticSummary} /> : null}
        </div>
      </details>
    </div>
  );
}
