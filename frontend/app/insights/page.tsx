import Link from "next/link";

import { StatCard } from "@/components/StatCard";
import { type Job, getAppliedJobs, getInsightsTrackerSummary, getMarketDashboard, getPredictionDashboard, getSavedJobs } from "@/lib/api";

const tabs = [
  { key: "tracker", label: "Tracker" },
  { key: "market", label: "Market" },
  { key: "predictions", label: "Predictions" },
  { key: "skills", label: "Skills" },
  { key: "sources", label: "Sources" },
];

function tabHref(key: string) {
  return key === "tracker" ? "/insights" : `/insights?tab=${key}`;
}

function formatScore(value: number | null | undefined) {
  return value === null || value === undefined ? "0.0" : value.toFixed(1);
}

function isTestJob(job: Job) {
  const combined = `${job.source} ${job.application_status} ${job.company} ${job.title} ${job.url}`.toLowerCase();
  return ["local_test", "stage10_smoke", "autofill diagnostic", "careeragent test company", "test company", "localhost"].some((token) =>
    combined.includes(token),
  );
}

export default async function InsightsPage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>;
}) {
  const params = await searchParams;
  const activeTab = tabs.some((tab) => tab.key === params.tab) ? params.tab || "tracker" : "tracker";
  const [market, prediction, tracker, savedJobs, appliedJobs] = await Promise.all([
    getMarketDashboard(),
    getPredictionDashboard(),
    getInsightsTrackerSummary(),
    getSavedJobs().catch(() => []),
    getAppliedJobs().catch(() => []),
  ]);
  const visibleSavedJobs = savedJobs.filter((job) => !isTestJob(job));
  const visibleAppliedJobs = appliedJobs.filter((job) => !isTestJob(job));
  const visibleAppliedCount = visibleAppliedJobs.length;
  const interviewCount = visibleAppliedJobs.filter((job) => job.application_status === "interview" || job.interview_at).length;
  const rejectedCount = visibleAppliedJobs.filter((job) => job.application_status === "rejected" || job.rejected_at).length;
  const offerCount = visibleAppliedJobs.filter((job) => job.application_status === "offer" || job.offer_at).length;

  return (
    <div className="page">
      <nav className="tab-nav" aria-label="Insights tabs">
        {tabs.map((tab) => (
          <Link className={activeTab === tab.key ? "tab-link active" : "tab-link"} href={tabHref(tab.key)} key={tab.key}>
            {tab.label}
          </Link>
        ))}
      </nav>

      {activeTab === "tracker" ? (
        <>
          <section className="stats-grid">
            <StatCard label="Saved" value={visibleSavedJobs.length} hint="Saved jobs not yet marked applied." />
            <StatCard label="Applied" value={visibleAppliedCount} hint="Jobs manually marked applied." />
            <StatCard label="Interview" value={interviewCount} hint="Applied jobs with interview outcome." />
            <StatCard label="Rejected" value={rejectedCount} hint="Applied jobs with rejected outcome." />
            <StatCard label="Offer" value={offerCount} hint="Applied jobs with offer outcome." />
          </section>
          <section className="panel">
            <div className="section-title">
              <h2>Recent Activity</h2>
              <span className="subtle">{tracker.recent_events.length} events</span>
            </div>
            {tracker.recent_events.length === 0 ? (
              <p className="subtle">No application activity yet.</p>
            ) : (
              <div className="timeline-list">
                {tracker.recent_events.slice(0, 12).map((event) => (
                  <article className="timeline-item" key={event.id}>
                    <strong>{event.job ? `${event.job.company} - ${event.job.title}` : `Job #${event.job_id}`}</strong>
                    <p className="subtle">{event.event_type.replace(/_/g, " ")} • {new Date(event.event_time).toLocaleString()}</p>
                    {event.notes ? <p className="subtle">{event.notes}</p> : null}
                  </article>
                ))}
              </div>
            )}
          </section>
          <section className="panel">
            <h2>Application Status Timeline</h2>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Count</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(tracker.counts_by_status)
                    .filter(([status]) => status !== "follow_up")
                    .map(([status, count]) => (
                      <tr key={status}>
                        <td>{status.replace(/_/g, " ")}</td>
                        <td>{count}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}

      {activeTab === "market" ? (
        <>
          <section className="stats-grid">
            <StatCard label="Total Jobs" value={market.pipeline_summary.total_jobs} hint="All saved jobs in the pipeline." />
            <StatCard label="Scored Jobs" value={market.pipeline_summary.scored_jobs} hint="Jobs with fit and priority scores." />
            <StatCard label="Packet Ready" value={market.pipeline_summary.packet_ready_jobs} hint="Jobs with generated packet materials." />
            <StatCard label="Applied" value={market.pipeline_summary.applied_jobs} hint="Jobs manually marked as applied." />
          </section>
          <section className="panel">
            <div className="section-title">
              <h2>Market Analytics</h2>
              <Link className="button secondary compact" href="/market">
                Open Full Market Page
              </Link>
            </div>
            <p className="subtle">The full market page includes exports, status breakdowns, stale jobs, and AI-assisted insight drafts.</p>
          </section>
        </>
      ) : null}

      {activeTab === "predictions" ? (
        <>
          <section className="stats-grid">
            <StatCard label="High Priority" value={prediction.summary.high_priority_jobs} hint="Jobs worth reviewing first." />
            <StatCard label="High Close Risk" value={prediction.summary.high_close_risk_jobs} hint="Jobs that may need reverification." />
            <StatCard label="Low Confidence" value={prediction.summary.low_confidence_predictions} hint="Prediction estimates with limited evidence." />
          </section>
          <section className="panel">
            <div className="section-title">
              <h2>Predictions</h2>
              <Link className="button secondary compact" href="/predictions">
                Open Full Predictions Page
              </Link>
            </div>
            <p className="subtle">Prediction estimates remain cautious and evidence-based. They are not guarantees of response or offers.</p>
          </section>
        </>
      ) : null}

      {activeTab === "skills" ? (
        <section className="panel">
          <h2>Skills</h2>
          {market.skills.requested_skills.length === 0 ? (
            <p className="subtle">Import and score jobs to see requested skills and possible gaps.</p>
          ) : (
            <div className="pill-list">
              {market.skills.requested_skills.slice(0, 20).map((skill) => (
                <span className="pill" key={skill.skill}>
                  {skill.skill} ({skill.count})
                </span>
              ))}
            </div>
          )}
        </section>
      ) : null}

      {activeTab === "sources" ? (
        <section className="panel">
          <h2>Sources</h2>
          {(prediction.source_quality.sources || []).length === 0 ? (
            <p className="subtle">Import more jobs and outcomes to estimate source quality.</p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Jobs</th>
                    <th>Quality</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {(prediction.source_quality.sources || []).slice(0, 12).map((row) => (
                    <tr key={row.name}>
                      <td>{row.source || row.name}</td>
                      <td>{row.total_jobs}</td>
                      <td>{formatScore(row.source_quality_score)}</td>
                      <td>{row.sample_size_warning ? "Low sample" : "Useful sample"}</td>
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
