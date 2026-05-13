import { StatCard } from "@/components/StatCard";
import { getJobCandidates, getMarketSummary, getPredictionDashboard } from "@/lib/api";

export default async function HomePage() {
  const [market, prediction, candidates] = await Promise.all([
    getMarketSummary(),
    getPredictionDashboard(),
    getJobCandidates().catch(() => []),
  ]);

  const waitingCandidates = candidates.filter((candidate) => !candidate.imported_job_id && candidate.filter_status !== "duplicate").length;
  const nextActions = [
    waitingCandidates > 0 ? `${waitingCandidates} candidate${waitingCandidates === 1 ? "" : "s"} waiting to save` : null,
    market.verified_jobs < market.total_jobs ? `${Math.max(market.total_jobs - market.verified_jobs, 0)} job${market.total_jobs - market.verified_jobs === 1 ? "" : "s"} need verification` : null,
    market.scored_jobs < market.total_jobs ? `${Math.max(market.total_jobs - market.scored_jobs, 0)} job${market.total_jobs - market.scored_jobs === 1 ? "" : "s"} need scoring` : null,
    prediction.summary.high_priority_jobs > 0 ? `${prediction.summary.high_priority_jobs} high-priority job${prediction.summary.high_priority_jobs === 1 ? "" : "s"} to review` : null,
  ].filter(Boolean);

  return (
    <div className="page">
      <section className="stats-grid">
        <StatCard label="Saved Jobs" value={market.total_jobs} hint="Jobs currently in your pipeline." />
        <StatCard label="Candidates Waiting" value={waitingCandidates} hint="Discovered candidates not yet imported." />
        <StatCard label="Scored Jobs" value={market.scored_jobs} hint="Jobs with fit and priority scores." />
        <StatCard label="Packets Ready" value={market.packet_ready_jobs} hint="Jobs with generated application materials." />
        <StatCard label="Applications Opened" value={market.application_opened_jobs} hint="Application links opened through CareerAgent." />
        <StatCard label="Applied" value={market.applied_jobs} hint="Jobs manually marked as submitted." />
      </section>

      <section className="panel">
        <div className="section-title">
          <h2>Next Recommended Actions</h2>
          <span className="subtle">What to do next</span>
        </div>
        {nextActions.length === 0 ? (
          <p className="subtle">You are caught up. Discover more jobs or review insights when you are ready.</p>
        ) : (
          <ul className="list">
            {nextActions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="warning-panel">
        <h2>Safety Boundary</h2>
        <p>CareerAgent never submits applications, never clicks final submit/apply/confirm buttons, and never bypasses login walls or CAPTCHAs.</p>
      </section>
    </div>
  );
}
