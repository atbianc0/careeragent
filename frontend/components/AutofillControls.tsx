"use client";

import { useEffect, useState } from "react";

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

function serializePreviewValues(values: Record<string, unknown>) {
  return JSON.stringify(values, null, 2);
}

export function AutofillControls({
  job,
  initialPackets = [],
  initialPacketId = null,
  onAutofillComplete,
}: AutofillControlsProps) {
  const [packets, setPackets] = useState<ApplicationPacket[]>(initialPackets);
  const [loadingPackets, setLoadingPackets] = useState(initialPackets.length === 0);
  const [packetError, setPacketError] = useState<string | null>(null);
  const [selectedPacketId, setSelectedPacketId] = useState<number | null>(
    initialPacketId ?? initialPackets[0]?.id ?? null,
  );
  const [allowBaseResumeUpload, setAllowBaseResumeUpload] = useState(false);
  const [fillSensitiveOptionalFields, setFillSensitiveOptionalFields] = useState(false);
  const [preview, setPreview] = useState<AutofillPreviewResponse | null>(null);
  const [summary, setSummary] = useState<AutofillStartResponse | null>(null);
  const [busyAction, setBusyAction] = useState<"preview" | "start" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPackets() {
      setLoadingPackets(true);
      try {
        const response = await getPacketsForJob(job.id);
        if (cancelled) {
          return;
        }
        setPackets(response);
        setSelectedPacketId((current) => {
          if (initialPacketId) {
            return initialPacketId;
          }
          if (current && response.some((packet) => packet.id === current)) {
            return current;
          }
          return response[0]?.id ?? null;
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

    setPackets(initialPackets);
    setSelectedPacketId(initialPacketId ?? initialPackets[0]?.id ?? null);
    setPreview(null);
    setSummary(null);
    setMessage(null);
    setError(null);
    void loadPackets();

    return () => {
      cancelled = true;
    };
  }, [job.id, initialPacketId, initialPackets]);

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
      setMessage(response.message);
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
          <dl className="key-value compact-key-value">
            <dt>Status</dt>
            <dd>{summary.status}</dd>
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
