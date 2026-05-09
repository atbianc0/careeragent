import Link from "next/link";

import { StatCard } from "@/components/StatCard";
import { getJobCandidates, getMarketSummary, getPredictionDashboard, getTrackerSummary } from "@/lib/api";

function actionCard(title: string, body: string, href: string, label: string) {
  return (
    <article className="workflow-step" key={title}>
      <div className="workflow-heading">
        <h3>{title}</h3>
      </div>
      <p className="subtle">{body}</p>
      <Link href={href} className="button secondary compact">
        {label}
      </Link>
    </article>
  );
}

export default async function HomePage() {
  const [market, prediction, tracker, candidates] = await Promise.all([
    getMarketSummary(),
    getPredictionDashboard(),
    getTrackerSummary(),
    getJobCandidates().catch(() => []),
  ]);

  const waitingCandidates = candidates.filter((candidate) => !candidate.imported_job_id && candidate.filter_status !== "duplicate").length;
  const nextActions = [
    waitingCandidates > 0 ? `${waitingCandidates} candidate${waitingCandidates === 1 ? "" : "s"} waiting to import` : null,
    market.verified_jobs < market.total_jobs ? `${Math.max(market.total_jobs - market.verified_jobs, 0)} job${market.total_jobs - market.verified_jobs === 1 ? "" : "s"} need verification` : null,
    market.scored_jobs < market.total_jobs ? `${Math.max(market.total_jobs - market.scored_jobs, 0)} job${market.total_jobs - market.scored_jobs === 1 ? "" : "s"} need scoring` : null,
    prediction.summary.high_priority_jobs > 0 ? `${prediction.summary.high_priority_jobs} high-priority job${prediction.summary.high_priority_jobs === 1 ? "" : "s"} to review` : null,
    tracker.follow_up_count > 0 ? `${tracker.follow_up_count} follow-up${tracker.follow_up_count === 1 ? "" : "s"} pending` : null,
  ].filter(Boolean);

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Agent Command Center</span>
        <h1>CareerAgent</h1>
        <p className="hero-copy">
          A human-in-the-loop job search assistant for finding jobs, reviewing candidates, generating application packets,
          applying manually, tracking outcomes, and learning from your pipeline.
        </p>
        <div className="button-row">
          <Link href="/jobs?tab=discover" className="button">
            Find Jobs
          </Link>
          <Link href="/jobs" className="button secondary">
            Review Saved Jobs
          </Link>
          <Link href="/applications" className="button secondary">
            Track Applications
          </Link>
          <Link href="/insights" className="button secondary">
            View Insights
          </Link>
        </div>
      </section>

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

      <section className="workflow-grid">
        {actionCard("Find Jobs", "Discover candidates from known ATS boards and company career pages.", "/jobs?tab=discover", "Discover")}
        {actionCard("Review Candidates", "Import only the jobs you want in the saved pipeline.", "/jobs?tab=candidates", "Review")}
        {actionCard("Score Saved Jobs", "Verify availability and rank fit before investing time.", "/jobs", "Open Jobs")}
        {actionCard("Generate Packets", "Create tailored resume, cover letter, notes, and application answers.", "/applications?tab=packets", "Open Packets")}
        {actionCard("Apply / Autofill", "Open applications manually or run safe visible autofill when available.", "/applications?tab=autofill", "Apply Safely")}
        {actionCard("Track Outcomes", "Mark applications, follow-ups, interviews, rejections, offers, and notes.", "/applications", "Track")}
        {actionCard("View Insights", "Review market patterns, predictions, skills, and source quality.", "/insights", "Analyze")}
      </section>

      <section className="warning-panel">
        <h2>Safety Boundary</h2>
        <p>CareerAgent never submits applications, never clicks final submit/apply/confirm buttons, and never bypasses login walls or CAPTCHAs.</p>
      </section>
    </div>
  );
}
