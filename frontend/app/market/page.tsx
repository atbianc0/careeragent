import { StatCard } from "@/components/StatCard";
import { getMarketSummary } from "@/lib/api";

export default async function MarketPage() {
  const summary = await getMarketSummary();

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Planned for Stage 9 - Market Analytics Dashboard</span>
        <h1>Market</h1>
        <p className="hero-copy">
          Full market analytics are still a future-stage feature. Stage 5 now surfaces basic real verification counts,
          score averages, recommendation stats, and requested-skill snapshots from saved job records.
        </p>
      </section>

      <section className="stats-grid">
        <StatCard label="Jobs Found" value={summary.jobs_found} hint="Real saved jobs currently in PostgreSQL." />
        <StatCard
          label="Verified / Checked Jobs"
          value={summary.verified_checked_jobs}
          hint="Jobs checked in the last 7 days."
        />
        <StatCard
          label="Scored Jobs"
          value={summary.scored_jobs_count}
          hint="Jobs that have been compared against the current profile and resume."
        />
        <StatCard
          label="Average Match Score"
          value={summary.average_resume_match_score}
          hint="Average resume-match score across scored jobs."
        />
        <StatCard
          label="Average Priority Score"
          value={summary.average_overall_priority_score}
          hint="Average overall priority score across scored jobs."
        />
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>Verification Status Counts</h2>
          <dl className="key-value">
            <dt>Open</dt>
            <dd>{summary.open_jobs}</dd>
            <dt>Probably Open</dt>
            <dd>{summary.probably_open_jobs}</dd>
            <dt>Unknown</dt>
            <dd>{summary.unknown_jobs}</dd>
            <dt>Possibly Closed</dt>
            <dd>{summary.possibly_closed_jobs}</dd>
            <dt>Likely Closed</dt>
            <dd>{summary.likely_closed_jobs}</dd>
            <dt>Closed</dt>
            <dd>{summary.closed_jobs}</dd>
          </dl>
        </article>

        <article className="panel">
          <h2>Scoring + Coverage</h2>
          <dl className="key-value">
            <dt>Average Verification Score</dt>
            <dd>{summary.average_verification_score}</dd>
            <dt>Average Likely Closed Score</dt>
            <dd>{summary.average_likely_closed_score}</dd>
            <dt>Checked Recently</dt>
            <dd>{summary.checked_recently_count}</dd>
            <dt>Stale Jobs</dt>
            <dd>{summary.stale_jobs_count}</dd>
            <dt>Risky Jobs</dt>
            <dd>{summary.risky_jobs}</dd>
            <dt>Recommendation Count</dt>
            <dd>{summary.recommendation_count}</dd>
          </dl>
          <p className="subtle">
            Packet generation is still a Stage 6 feature, and full market analytics arrive in Stage 9.
          </p>
        </article>

        <article className="panel">
          <h2>Top Role Categories</h2>
          {summary.top_role_categories.length > 0 ? (
            <ul className="list">
              {summary.top_role_categories.map((entry) => (
                <li key={entry.role_category}>
                  {entry.role_category}: avg priority {entry.average_overall_priority_score} across {entry.count} jobs
                </li>
              ))}
            </ul>
          ) : (
            <p className="subtle">No scored role categories yet.</p>
          )}
        </article>

        <article className="panel">
          <h2>Top Requested Skills</h2>
          <div className="pill-list">
            {summary.top_requested_skills.length > 0 ? (
              summary.top_requested_skills.map((entry) => (
                <span className="pill" key={entry.skill}>
                  {entry.skill} ({entry.count})
                </span>
              ))
            ) : (
              <span className="subtle">No requested skills yet.</span>
            )}
          </div>
        </article>

        <article className="panel">
          <h2>Top Recommended Jobs</h2>
          {summary.top_recommended_jobs.length > 0 ? (
            <ul className="list">
              {summary.top_recommended_jobs.map((job) => (
                <li key={job.id}>
                  {job.title} at {job.company}: priority {job.overall_priority_score}, match {job.resume_match_score}, {job.verification_status}
                </li>
              ))}
            </ul>
          ) : (
            <p className="subtle">Score a few jobs first to surface recommendations here.</p>
          )}
        </article>

        <article className="panel">
          <h2>Locations From Saved Jobs</h2>
          <div className="pill-list">
            {summary.top_locations.map((location) => (
              <span className="pill" key={location}>
                {location}
              </span>
            ))}
          </div>
          <p className="subtle">{summary.note}</p>
        </article>
      </section>
    </div>
  );
}
