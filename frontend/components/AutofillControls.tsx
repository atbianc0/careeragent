"use client";

import { useEffect, useMemo, useState } from "react";

import {
  type ApplicationPacket,
  type AutofillPreviewResponse,
  type AutofillStartResponse,
  type Job,
  getPacketsForJob,
  previewAutofill,
  startAutofill,
} from "@/lib/api";

type AutofillControlsProps = {
  job: Job;
  initialPackets?: ApplicationPacket[];
  initialPacketId?: number | null;
  onAutofillComplete?: () => Promise<void> | void;
};

const EMPTY_PACKETS: ApplicationPacket[] = [];

function serializePreviewValues(values: Record<string, unknown>) {
  return JSON.stringify(values, null, 2);
}

function getPacketsKey(packets: ApplicationPacket[]) {
  return packets.map((packet) => `${packet.id}:${packet.generation_status}:${packet.updated_at}`).join(",");
}

function getPreferredPacketId(packets: ApplicationPacket[], initialPacketId: number | null) {
  if (initialPacketId !== null && packets.some((packet) => packet.id === initialPacketId)) {
    return initialPacketId;
  }
  return packets[0]?.id ?? null;
}

export function AutofillControls({
  job,
  initialPackets = EMPTY_PACKETS,
  initialPacketId = null,
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
  const [preview, setPreview] = useState<AutofillPreviewResponse | null>(null);
  const [summary, setSummary] = useState<AutofillStartResponse | null>(null);
  const [busyAction, setBusyAction] = useState<"preview" | "start" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const packetsKey = useMemo(() => getPacketsKey(packets), [packets]);

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
    setPreview(null);
    setSummary(null);
    setMessage(null);
    setError(null);
  }, [job.id, selectedPacketId]);

  const canAutofill = Boolean(job.url.trim());

  function buildPayload() {
    return {
      job_id: job.id,
      packet_id: selectedPacketId,
      allow_base_resume_upload: allowBaseResumeUpload,
      fill_sensitive_optional_fields: fillSensitiveOptionalFields,
    };
  }

  async function handlePreview() {
    setBusyAction("preview");
    setError(null);
    setMessage(null);

    try {
      const response = await previewAutofill(buildPayload());
      setPreview(response);
      setSummary(null);
      setMessage(response.message);
    } catch (previewError) {
      setError(previewError instanceof Error ? previewError.message : "Failed to preview the autofill plan.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleStart() {
    setBusyAction("start");
    setError(null);
    setMessage(null);

    try {
      const response = await startAutofill(buildPayload());
      setSummary(response);
      setPreview(null);
      if (response.success === false || response.status === "browser_display_unavailable") {
        setError(response.message);
        setMessage(null);
      } else {
        setMessage(response.message);
      }
      await onAutofillComplete?.();
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Failed to start browser autofill.");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="stack">
      <p className="subtle">
        CareerAgent will fill safe, high-confidence fields and stop before submit. You must review the browser and click
        any final submit button manually.
      </p>

      {!canAutofill ? <p className="message error">No application URL is available for this job.</p> : null}
      {packetError ? <p className="message error">{packetError}</p> : null}

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
                Packet #{packet.id} • {packet.generation_status}
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
          <span>Fill sensitive optional EEO fields only with “Prefer not to answer” when available</span>
        </label>
        {fillSensitiveOptionalFields ? (
          <p className="subtle">
            Sensitive optional fields stay conservative in Stage 8. CareerAgent still skips SSN, date of birth, and any
            field it cannot classify safely.
          </p>
        ) : null}
      </div>

      <div className="button-row">
        <button className="button secondary" type="button" onClick={() => void handlePreview()} disabled={!canAutofill || busyAction !== null}>
          {busyAction === "preview" ? "Previewing..." : "Preview Autofill Plan"}
        </button>
        <button className="button" type="button" onClick={() => void handleStart()} disabled={!canAutofill || busyAction !== null}>
          {busyAction === "start" ? "Starting..." : "Start Autofill in Browser"}
        </button>
      </div>

      {message ? <p className="message success">{message}</p> : null}
      {error ? <p className="message error">{error}</p> : null}

      {preview ? (
        <div className="stack">
          <h3>Preview Plan</h3>
          <dl className="key-value compact-key-value">
            <dt>Job ID</dt>
            <dd>#{preview.job_id}</dd>
            <dt>Packet ID</dt>
            <dd>{preview.packet_id ? `#${preview.packet_id}` : "None selected"}</dd>
            <dt>Uploadable Files</dt>
            <dd>{preview.files_available.length > 0 ? preview.files_available.join(", ") : "None available"}</dd>
          </dl>
          {preview.warnings.length > 0 ? (
            <ul className="list">
              {preview.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          ) : (
            <p className="subtle">No extra warnings for this preview.</p>
          )}
          <details className="details-block">
            <summary>Proposed Values</summary>
            <pre className="code-block">{serializePreviewValues(preview.proposed_values)}</pre>
          </details>
        </div>
      ) : null}

      {summary ? (
        <div className="stack">
          <h3>Autofill Result</h3>
          {summary.browser_mode === "headless" && summary.success ? (
            <section className="warning-panel">
              <strong>Manual review required</strong>
              <p>
                Autofill ran in headless mode. CareerAgent did not submit anything. Open the application manually and
                review before submitting.
              </p>
            </section>
          ) : null}
          {summary.status === "browser_display_unavailable" ? (
            <section className="warning-panel">
              <strong>Browser display unavailable</strong>
              <p>
                Headed Chromium cannot run inside this Docker container because there is no display/XServer. Set{" "}
                <code>PLAYWRIGHT_HEADLESS=true</code> in <code>.env</code> or run the backend locally outside Docker
                for visible browser autofill.
              </p>
              {summary.suggested_fix ? <p>{summary.suggested_fix}</p> : null}
            </section>
          ) : null}
          <dl className="key-value compact-key-value">
            <dt>Success</dt>
            <dd>{summary.success ? "Yes" : "No"}</dd>
            <dt>Status</dt>
            <dd>{summary.status}</dd>
            <dt>Browser Mode</dt>
            <dd>{summary.browser_mode}</dd>
            <dt>Opened URL</dt>
            <dd>{summary.opened_url}</dd>
            <dt>Fields Detected</dt>
            <dd>{summary.fields_detected}</dd>
            <dt>Fields Filled</dt>
            <dd>{summary.fields_filled}</dd>
            <dt>Fields Skipped</dt>
            <dd>{summary.fields_skipped}</dd>
            <dt>Files Uploaded</dt>
            <dd>{summary.files_uploaded.length > 0 ? summary.files_uploaded.join(", ") : "None uploaded"}</dd>
          </dl>
          {summary.blocked_actions.length > 0 ? (
            <>
              <h4>Blocked Final Actions</h4>
              <ul className="list">
                {summary.blocked_actions.map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            </>
          ) : null}
          {summary.warnings.length > 0 ? (
            <>
              <h4>Warnings</h4>
              <ul className="list">
                {summary.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </>
          ) : null}
          <details className="details-block">
            <summary>Field Results</summary>
            <div className="timeline-list">
              {summary.field_results.map((result, index) => (
                <div className="timeline-item" key={`${result.field_key}-${index}`}>
                  <strong>
                    {result.label || result.field_key} • {result.filled ? "filled" : "skipped"}
                  </strong>
                  <p className="subtle">
                    {result.field_key} • confidence {result.confidence}
                  </p>
                  <p className="subtle">{result.reason}</p>
                </div>
              ))}
            </div>
          </details>
        </div>
      ) : null}
    </div>
  );
}
