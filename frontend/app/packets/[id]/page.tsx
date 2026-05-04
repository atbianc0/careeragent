import Link from "next/link";

import { AutofillControls } from "@/components/AutofillControls";
import { ApplicationPacketFilePreview, getPacket, getPacketFile } from "@/lib/api";

function getStatusClassName(status: string) {
  return `status-tag status-${status.replace(/_/g, "-")}`;
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

function parseJson(content: string): Record<string, unknown> | null {
  try {
    return JSON.parse(content) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function previewTitle(fileKey: string) {
  const labels: Record<string, string> = {
    cover_letter: "cover_letter.md",
    recruiter_message: "recruiter_message.md",
    application_questions: "application_questions.md",
    application_notes: "application_notes.md",
    change_summary: "change_summary.md",
    tailored_resume_tex: "tailored_resume.tex",
    job_summary: "job_summary.json",
    packet_metadata: "packet_metadata.json",
  };
  return labels[fileKey] || fileKey;
}

export default async function PacketDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const numericId = Number(id);

  if (!Number.isInteger(numericId) || numericId <= 0) {
    return (
      <div className="page">
        <section className="warning-panel">
          <h1>Packet Not Found</h1>
          <p>The provided packet id is invalid.</p>
          <Link href="/packets" className="inline-link">
            Back to Packets
          </Link>
        </section>
      </div>
    );
  }

  const packet = await getPacket(numericId).catch(() => null);
  if (!packet) {
    return (
      <div className="page">
        <section className="warning-panel">
          <h1>Packet Not Found</h1>
          <p>CareerAgent could not load that application packet.</p>
          <Link href="/packets" className="inline-link">
            Back to Packets
          </Link>
        </section>
      </div>
    );
  }

  const fileKeys = [
    "cover_letter",
    "recruiter_message",
    "application_questions",
    "application_notes",
    "change_summary",
    "tailored_resume_tex",
    "job_summary",
    "packet_metadata",
  ];
  const previewResults = await Promise.allSettled(fileKeys.map((fileKey) => getPacketFile(packet.id, fileKey)));
  const previews = previewResults.reduce<Record<string, ApplicationPacketFilePreview>>((accumulator, result, index) => {
    if (result.status === "fulfilled") {
      accumulator[fileKeys[index]] = result.value;
    }
    return accumulator;
  }, {});
  const metadata = previews.packet_metadata ? parseJson(previews.packet_metadata.content) : null;
  const safetyNotes = Array.isArray(metadata?.safety_notes) ? metadata?.safety_notes : [];

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 6 Packet Detail</span>
        <h1>{packet.job?.title || "Application Packet"}</h1>
        <p className="hero-copy">
          {packet.job?.company || "Unknown Company"} • packet #{packet.id}
        </p>
        <p className="hero-copy">
          Review all generated materials manually before using them. CareerAgent does not submit applications, and opening
          this page logs a packet view in the tracker.
        </p>
        <div className="button-row">
          <Link href="/packets" className="button secondary">
            Back to Packets
          </Link>
          {packet.job ? (
            <Link href={`/jobs/${packet.job.id}`} className="button secondary">
              Back to Job
            </Link>
          ) : null}
          {packet.job ? (
            <Link href={`/autofill?jobId=${packet.job.id}`} className="button secondary">
              Open Autofill Page
            </Link>
          ) : null}
        </div>
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>Packet Metadata</h2>
          <dl className="key-value">
            <dt>Packet ID</dt>
            <dd>#{packet.id}</dd>
            <dt>Status</dt>
            <dd>
              <span className={getStatusClassName(packet.generation_status)}>{packet.generation_status}</span>
            </dd>
            <dt>Generated</dt>
            <dd>{formatDateTime(packet.generated_at)}</dd>
            <dt>Packet Folder</dt>
            <dd>{packet.packet_path}</dd>
            <dt>Resume PDF</dt>
            <dd>{packet.tailored_resume_pdf_path || "Not available"}</dd>
            <dt>Generation Note</dt>
            <dd>{packet.generation_error || "No errors recorded."}</dd>
          </dl>
        </article>

        <article className="panel">
          <h2>Generated Files</h2>
          <ul className="list">
            {[
              packet.tailored_resume_tex_path,
              packet.tailored_resume_pdf_path,
              packet.cover_letter_path,
              packet.recruiter_message_path,
              packet.application_questions_path,
              packet.application_notes_path,
              packet.change_summary_path,
              packet.job_summary_path,
              packet.packet_metadata_path,
            ]
              .filter(Boolean)
              .map((path) => (
                <li key={path}>{path}</li>
              ))}
          </ul>
        </article>

        <article className="panel">
          <h2>Safety Notes</h2>
          {safetyNotes.length > 0 ? (
            <ul className="list">
              {safetyNotes.map((item) => (
                <li key={String(item)}>{String(item)}</li>
              ))}
            </ul>
          ) : (
            <p className="subtle">No extra safety notes were found in packet metadata.</p>
          )}
        </article>
      </section>

      {packet.job ? (
        <section className="panel">
          <h2>Start Autofill for This Packet</h2>
          <p className="subtle">
            CareerAgent will use this packet when possible, fill safe fields only, and stop before any final submit
            action. You must review and submit manually.
          </p>
          <AutofillControls job={packet.job} initialPackets={[packet]} initialPacketId={packet.id} />
        </section>
      ) : null}

      <section className="panel-grid">
        {fileKeys.map((fileKey) => {
          const preview = previews[fileKey];
          return (
            <article className="panel" key={fileKey}>
              <h2>{previewTitle(fileKey)}</h2>
              {preview ? (
                <details className="details-block" open={fileKey !== "tailored_resume_tex"}>
                  <summary>Preview</summary>
                  <pre className="code-block">{preview.content}</pre>
                </details>
              ) : (
                <p className="subtle">Preview unavailable for this file.</p>
              )}
            </article>
          );
        })}
      </section>
    </div>
  );
}
