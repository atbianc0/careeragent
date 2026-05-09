import Link from "next/link";

import { AutofillManager } from "@/components/AutofillManager";
import { TrackerBoard } from "@/components/TrackerBoard";
import { getAutofillSafety, getAutofillStatus, getPackets, getTrackerJobs } from "@/lib/api";

const tabs = [
  { key: "tracker", label: "Tracker" },
  { key: "packets", label: "Packets" },
  { key: "autofill", label: "Autofill" },
  { key: "followups", label: "Follow-ups" },
];

function tabHref(key: string) {
  return key === "tracker" ? "/applications" : `/applications?tab=${key}`;
}

export default async function ApplicationsPage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string; jobId?: string }>;
}) {
  const params = await searchParams;
  const activeTab = tabs.some((tab) => tab.key === params.tab) ? params.tab || "tracker" : "tracker";

  const numericJobId = params.jobId ? Number(params.jobId) : null;
  const [packets, trackerJobs] = await Promise.all([getPackets().catch(() => []), getTrackerJobs().catch(() => [])]);
  const followUps = trackerJobs.filter((job) => job.follow_up_at || job.application_status === "follow_up");

  const autofillData =
    activeTab === "autofill"
      ? await Promise.all([
          getAutofillStatus(),
          getAutofillSafety().catch(() => ({ blocked_final_action_words: [], safety_rules: [] })),
        ])
      : null;

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Applications</span>
        <h1>Applications</h1>
        <p className="hero-copy">
          Generate packets, open applications, track status, manage follow-ups, and use safe autofill without ever submitting automatically.
        </p>
      </section>

      <nav className="tab-nav" aria-label="Applications tabs">
        {tabs.map((tab) => (
          <Link className={activeTab === tab.key ? "tab-link active" : "tab-link"} href={tabHref(tab.key)} key={tab.key}>
            {tab.label}
          </Link>
        ))}
      </nav>

      {activeTab === "tracker" ? <TrackerBoard /> : null}

      {activeTab === "packets" ? (
        <section className="panel">
          <div className="section-title">
            <h2>Packets</h2>
            <Link className="button secondary compact" href="/packets">
              Open Packet Library
            </Link>
          </div>
          {packets.length === 0 ? (
            <p className="subtle">No packets yet. Open a scored job detail page and generate an application packet.</p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Packet</th>
                    <th>Job</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {packets.slice(0, 20).map((packet) => (
                    <tr key={packet.id}>
                      <td>#{packet.id}</td>
                      <td>
                        <strong>{packet.job?.title || "Unknown title"}</strong>
                        <div className="subtle">{packet.job?.company || "Unknown company"}</div>
                      </td>
                      <td>{packet.generation_status}</td>
                      <td>
                        <Link className="button secondary compact" href={`/packets/${packet.id}`}>
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
      ) : null}

      {activeTab === "autofill" && autofillData ? (
        <AutofillManager
          status={autofillData[0]}
          safety={autofillData[1]}
          initialJobId={numericJobId && Number.isInteger(numericJobId) && numericJobId > 0 ? numericJobId : null}
        />
      ) : null}

      {activeTab === "followups" ? (
        <section className="panel">
          <h2>Follow-ups</h2>
          {followUps.length === 0 ? (
            <p className="subtle">No pending follow-ups. Jobs with follow-up dates will appear here.</p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Job</th>
                    <th>Status</th>
                    <th>Follow-up</th>
                    <th>Open</th>
                  </tr>
                </thead>
                <tbody>
                  {followUps.map((job) => (
                    <tr key={job.id}>
                      <td>
                        <strong>{job.title}</strong>
                        <div className="subtle">{job.company}</div>
                      </td>
                      <td>{job.application_status}</td>
                      <td>{job.follow_up_at || "Due status set"}</td>
                      <td>
                        <Link className="button secondary compact" href={`/jobs/${job.id}`}>
                          Open Job
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}
