import Link from "next/link";

import { StatCard } from "@/components/StatCard";
import { getMarketDashboard, getPredictionDashboard } from "@/lib/api";

const tabs = [
  { key: "market", label: "Market" },
  { key: "predictions", label: "Predictions" },
  { key: "skills", label: "Skills" },
  { key: "sources", label: "Sources" },
];

function tabHref(key: string) {
  return key === "market" ? "/insights" : `/insights?tab=${key}`;
}

function formatScore(value: number | null | undefined) {
  return value === null || value === undefined ? "0.0" : value.toFixed(1);
}

export default async function InsightsPage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>;
}) {
  const params = await searchParams;
  const activeTab = tabs.some((tab) => tab.key === params.tab) ? params.tab || "market" : "market";
  const [market, prediction] = await Promise.all([getMarketDashboard(), getPredictionDashboard()]);

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Insights</span>
        <h1>Insights</h1>
        <p className="hero-copy">
          Review market trends, skill gaps, source quality, and prediction estimates.
        </p>
      </section>

      <nav className="tab-nav" aria-label="Insights tabs">
        {tabs.map((tab) => (
          <Link className={activeTab === tab.key ? "tab-link active" : "tab-link"} href={tabHref(tab.key)} key={tab.key}>
            {tab.label}
          </Link>
        ))}
      </nav>

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
