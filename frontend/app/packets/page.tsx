import Link from "next/link";

import { getPackets } from "@/lib/api";

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

function countFiles(packet: {
  tailored_resume_tex_path: string | null;
  tailored_resume_pdf_path: string | null;
  cover_letter_path: string | null;
  recruiter_message_path: string | null;
  application_questions_path: string | null;
  application_notes_path: string | null;
  change_summary_path: string | null;
  job_summary_path: string | null;
  packet_metadata_path: string | null;
}) {
  return [
    packet.tailored_resume_tex_path,
    packet.tailored_resume_pdf_path,
    packet.cover_letter_path,
    packet.recruiter_message_path,
    packet.application_questions_path,
    packet.application_notes_path,
    packet.change_summary_path,
    packet.job_summary_path,
    packet.packet_metadata_path,
  ].filter(Boolean).length;
}

export default async function PacketsPage() {
  const packets = await getPackets().catch(() => []);

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 6 - Application Packet Generation</span>
        <h1>Packets</h1>
        <p className="hero-copy">
          Stage 6 generates reviewable application packets. It does not submit applications.
        </p>
        <p className="hero-copy">
          Generated outputs stay private in the local `outputs/application_packets/` folder and remain gitignored.
        </p>
      </section>

      <section className="panel">
        <div className="section-title">
          <h2>Generated Packets</h2>
          <span className="subtle">{packets.length} saved</span>
        </div>
        {packets.length === 0 ? (
          <p className="subtle">
            No packets have been generated yet. Open a scored job detail page and click Generate Application Packet.
          </p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Packet</th>
                  <th>Job</th>
                  <th>Generated</th>
                  <th>Status</th>
                  <th>Files</th>
                  <th>Packet Folder</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {packets.map((packet) => (
                  <tr key={packet.id}>
                    <td>#{packet.id}</td>
                    <td>
                      <div className="status-stack">
                        <strong>{packet.job?.title || "Unknown Title"}</strong>
                        <span className="subtle">{packet.job?.company || "Unknown Company"}</span>
                      </div>
                    </td>
                    <td>{formatDateTime(packet.generated_at)}</td>
                    <td>
                      <div className="status-stack">
                        <span className={getStatusClassName(packet.generation_status)}>{packet.generation_status}</span>
                        <span className="subtle">{packet.generation_error || "No errors recorded."}</span>
                      </div>
                    </td>
                    <td>{countFiles(packet)}</td>
                    <td>{packet.packet_path}</td>
                    <td>
                      <Link href={`/packets/${packet.id}`} className="button secondary compact">
                        View Packet
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
