import Link from "next/link";

import { StatCard } from "@/components/StatCard";
import { getMarketDashboard, getMarketExport, getMarketInsights, type MarketDashboard } from "@/lib/api";

function formatScore(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "0.0";
  }
  return value.toFixed(1);
}

function formatRate(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "Not enough data yet";
  }
  return `${value.toFixed(1)}%`;
}

function activityTotal(row: MarketDashboard["activity_over_time"]["series"][number]) {
  return (
    row.jobs_imported +
    row.jobs_verified +
    row.jobs_scored +
    row.packets_generated +
    row.application_links_opened +
    row.applications_marked_applied +
    row.interviews +
    row.rejections +
    row.offers
  );
}

function BreakdownTable({
  title,
  rows,
}: {
  title: string;
  rows: Array<{
    name: string;
    count: number;
    average_resume_match_score?: number;
    average_priority_score?: number;
    applied_count?: number;
    interview_count?: number;
  }>;
}) {
  return (
    <article className="panel">
      <h2>{title}</h2>
      {rows.length === 0 ? (
        <p className="subtle">Not enough data yet.</p>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Count</th>
                <th>Avg Match</th>
                <th>Avg Priority</th>
                <th>Applied</th>
                <th>Interview</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 10).map((row) => (
                <tr key={row.name}>
                  <td>{row.name}</td>
                  <td>{row.count}</td>
                  <td>{formatScore(row.average_resume_match_score ?? 0)}</td>
                  <td>{formatScore(row.average_priority_score ?? 0)}</td>
                  <td>{row.applied_count ?? 0}</td>
                  <td>{row.interview_count ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}

function StatusBreakdownTable({
  title,
  rows,
}: {
  title: string;
  rows: Array<{ name: string; count: number }>;
}) {
  return (
    <article className="panel">
      <h2>{title}</h2>
      {rows.length === 0 ? (
        <p className="subtle">Not enough data yet.</p>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Count</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.name}>
                  <td>{row.name}</td>
                  <td>{row.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}

function SkillList({
  title,
  rows,
  emptyMessage,
}: {
  title: string;
  rows: Array<{
    skill: string;
    count: number;
    required_count?: number;
    preferred_count?: number;
    missing_required_count?: number;
    missing_preferred_count?: number;
  }>;
  emptyMessage: string;
}) {
  return (
    <article className="panel">
      <h2>{title}</h2>
      {rows.length === 0 ? (
        <p className="subtle">{emptyMessage}</p>
      ) : (
        <ul className="list">
          {rows.slice(0, 12).map((row) => (
            <li key={row.skill}>
              {row.skill}: {row.count}
              {row.required_count !== undefined ? ` - required ${row.required_count}` : ""}
              {row.preferred_count !== undefined ? ` - preferred ${row.preferred_count}` : ""}
              {row.missing_required_count !== undefined ? ` - missing required ${row.missing_required_count}` : ""}
              {row.missing_preferred_count !== undefined ? ` - missing preferred ${row.missing_preferred_count}` : ""}
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

function ScoreJobsTable({
  title,
  rows,
  emptyMessage,
}: {
  title: string;
  rows: Array<{
    job_id: number;
    company: string;
    title: string;
    role_category: string;
    resume_match_score: number;
    overall_priority_score: number;
    verification_status: string;
  }>;
  emptyMessage: string;
}) {
  return (
    <article className="panel">
      <h2>{title}</h2>
      {rows.length === 0 ? (
        <p className="subtle">{emptyMessage}</p>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Job</th>
                <th>Role</th>
                <th>Resume Match</th>
                <th>Priority</th>
                <th>Verification</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.job_id}-${row.title}`}>
                  <td>
                    <Link href={`/jobs/${row.job_id}`} className="job-link">
                      {row.title}
                    </Link>
                    <div className="subtle">{row.company}</div>
                  </td>
                  <td>{row.role_category}</td>
                  <td>{formatScore(row.resume_match_score)}</td>
                  <td>{formatScore(row.overall_priority_score)}</td>
                  <td>{row.verification_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}

function ResponseRatesTable({
  title,
  rows,
}: {
  title: string;
  rows: Array<{
    name: string;
    applied_count: number;
    response_count: number;
    response_rate: number | null;
    interview_count: number;
    interview_rate: number | null;
    offer_count: number;
    offer_rate: number | null;
    rejected_count: number;
    sample_size_warning: boolean;
  }>;
}) {
  return (
    <article className="panel">
      <h2>{title}</h2>
      {rows.length === 0 ? (
        <p className="subtle">Response rate needs applied jobs and outcomes.</p>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Applied</th>
                <th>Responses</th>
                <th>Response Rate</th>
                <th>Interviews</th>
                <th>Offers</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 10).map((row) => (
                <tr key={row.name}>
                  <td>
                    {row.name}
                    {row.sample_size_warning ? <div className="subtle">Small sample size</div> : null}
                  </td>
                  <td>{row.applied_count}</td>
                  <td>{row.response_count}</td>
                  <td>{formatRate(row.response_rate)}</td>
                  <td>{row.interview_count}</td>
                  <td>{row.offer_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}

type MarketPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function MarketPage({ searchParams }: MarketPageProps) {
  await searchParams;
  const [dashboard, insights] = await Promise.all([
    getMarketDashboard(),
    getMarketInsights(),
  ]);
  const exportJsonUrl = getMarketExport("json");
  const exportCsvUrl = getMarketExport("csv");
  const activityRows = dashboard.activity_over_time.series.filter((row) => activityTotal(row) > 0);

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 11 - Prediction and Improvements</span>
        <h1>Market</h1>
        <p className="hero-copy">
          CareerAgent now summarizes pipeline, skill, score, verification, and outcome trends based on the real data you
          have collected so far.
        </p>
        <p className="hero-copy">
          Market analytics are descriptive. Prediction estimates live on a separate page and should be used as cautious guidance, not certainty.
        </p>
        <div className="button-row">
          <Link href="/predictions" className="button">
            View Predictions
          </Link>
          <Link href="/jobs" className="button secondary">
            Open Jobs
          </Link>
          <Link href="/tracker" className="button secondary">
            Open Tracker
          </Link>
          <a href={exportJsonUrl} className="button secondary" target="_blank" rel="noreferrer">
            Export JSON
          </a>
          <a href={exportCsvUrl} className="button secondary" target="_blank" rel="noreferrer">
            Export CSV
          </a>
        </div>
      </section>

      <section className="stats-grid">
        <StatCard label="Total Jobs" value={dashboard.pipeline_summary.total_jobs} hint="All saved jobs in your collected dataset." />
        <StatCard label="Verified Jobs" value={dashboard.pipeline_summary.verified_jobs} hint="Jobs that have verification data or a recent check." />
        <StatCard label="Scored Jobs" value={dashboard.pipeline_summary.scored_jobs} hint="Jobs that have Stage 5 match scoring data." />
        <StatCard label="Packet Ready" value={dashboard.pipeline_summary.packet_ready_jobs} hint="Jobs with generated packet materials ready." />
        <StatCard label="Applied" value={dashboard.pipeline_summary.applied_jobs} hint="Jobs marked applied or later in the workflow." />
        <StatCard label="Interviews" value={dashboard.pipeline_summary.interview_jobs} hint="Jobs currently in interview stage." />
        <StatCard label="Offers" value={dashboard.pipeline_summary.offer_jobs} hint="Jobs currently marked as offers." />
        <StatCard label="Response Rate" value={formatRate(dashboard.outcome_summary.response_rate)} hint="Observed responses from your applied jobs so far." />
      </section>

      {dashboard.pipeline_summary.total_jobs === 0 ? (
        <section className="warning-panel">
          <h2>Not Enough Data Yet</h2>
          <p>Import jobs to see market analytics.</p>
          <p>CareerAgent will populate role, skill, score, outcome, and stale-job trends after you start saving jobs.</p>
        </section>
      ) : null}

      <section className="panel">
        <div className="section-title">
          <h2>Predictions</h2>
          <Link href="/predictions" className="inline-link">
            View Predictions
          </Link>
        </div>
        <p className="subtle">
          The Market page describes what has happened in your stored data. The Predictions page uses those same records
          to estimate priority, close risk, source quality, role quality, response likelihood, and apply windows with confidence labels.
        </p>
      </section>

      <section className="panel-grid">
        <BreakdownTable title="Jobs by Role Category" rows={dashboard.jobs_by_role} />
        <BreakdownTable title="Jobs by Source" rows={dashboard.jobs_by_source} />
        <StatusBreakdownTable title="Jobs by Verification Status" rows={dashboard.jobs_by_verification_status} />
        <StatusBreakdownTable title="Jobs by Application Status" rows={dashboard.jobs_by_application_status} />
        <BreakdownTable title="Top Companies" rows={dashboard.jobs_by_company} />
        <BreakdownTable title="Top Locations" rows={dashboard.jobs_by_location} />
      </section>

      <section className="panel-grid">
        <SkillList
          title="Top Requested Skills"
          rows={dashboard.skills.requested_skills}
          emptyMessage="Import more jobs to see requested skill patterns."
        />
        <SkillList
          title="Top Missing Skills"
          rows={dashboard.skills.missing_skills}
          emptyMessage="Score more jobs to see missing-skill analytics."
        />
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>Score Summary</h2>
          <dl className="key-value">
            <dt>Average Resume Match</dt>
            <dd>{formatScore(dashboard.score_summary.average_resume_match_score)}</dd>
            <dt>Median Resume Match</dt>
            <dd>{formatScore(dashboard.score_summary.median_resume_match_score)}</dd>
            <dt>Average Priority</dt>
            <dd>{formatScore(dashboard.score_summary.average_overall_priority_score)}</dd>
            <dt>Average Skill Match</dt>
            <dd>{formatScore(dashboard.score_summary.average_skill_match_score)}</dd>
            <dt>Average Role Match</dt>
            <dd>{formatScore(dashboard.score_summary.average_role_match_score)}</dd>
            <dt>Average Location Score</dt>
            <dd>{formatScore(dashboard.score_summary.average_location_score)}</dd>
          </dl>
          {dashboard.score_summary.message ? <p className="subtle">{dashboard.score_summary.message}</p> : null}
        </article>

        <article className="panel">
          <h2>Score Distribution</h2>
          {dashboard.score_summary.score_distribution.length > 0 ? (
            <ul className="list">
              {dashboard.score_summary.score_distribution.map((bucket) => (
                <li key={bucket.bucket}>
                  {bucket.bucket}: {bucket.count}
                </li>
              ))}
            </ul>
          ) : (
            <p className="subtle">Score jobs to see distribution buckets.</p>
          )}
        </article>

        <article className="panel">
          <h2>Verification Summary</h2>
          <dl className="key-value">
            <dt>Average Verification Score</dt>
            <dd>{formatScore(dashboard.verification_summary.average_verification_score)}</dd>
            <dt>Average Likely Closed Score</dt>
            <dd>{formatScore(dashboard.verification_summary.average_likely_closed_score)}</dd>
            <dt>Checked Recently</dt>
            <dd>{dashboard.verification_summary.jobs_checked_recently}</dd>
            <dt>Likely Closed Jobs</dt>
            <dd>{dashboard.verification_summary.likely_closed_jobs_count}</dd>
            <dt>Closed Jobs</dt>
            <dd>{dashboard.verification_summary.closed_jobs_count}</dd>
            <dt>Stale Jobs</dt>
            <dd>{dashboard.verification_summary.stale_jobs_count}</dd>
          </dl>
        </article>
      </section>

      <section className="panel-grid">
        <ScoreJobsTable
          title="Top Scored Jobs"
          rows={dashboard.score_summary.top_scored_jobs}
          emptyMessage="Score jobs to see the strongest matches."
        />
        <ScoreJobsTable
          title="Lower Scored Jobs"
          rows={dashboard.score_summary.low_scored_jobs}
          emptyMessage="Score jobs to see lower-priority matches."
        />
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>Outcome Summary</h2>
          <dl className="key-value">
            <dt>Applied Count</dt>
            <dd>{dashboard.outcome_summary.applied_count}</dd>
            <dt>Interview Count</dt>
            <dd>{dashboard.outcome_summary.interview_count}</dd>
            <dt>Rejected Count</dt>
            <dd>{dashboard.outcome_summary.rejected_count}</dd>
            <dt>Offer Count</dt>
            <dd>{dashboard.outcome_summary.offer_count}</dd>
            <dt>Response Rate</dt>
            <dd>{formatRate(dashboard.outcome_summary.response_rate)}</dd>
            <dt>Interview Rate</dt>
            <dd>{formatRate(dashboard.outcome_summary.interview_rate)}</dd>
            <dt>Offer Rate</dt>
            <dd>{formatRate(dashboard.outcome_summary.offer_rate)}</dd>
          </dl>
          {dashboard.outcome_summary.message ? <p className="subtle">{dashboard.outcome_summary.message}</p> : null}
          {dashboard.response_rates.sample_size_warning ? (
            <p className="subtle">Some response-rate groups have small sample sizes, so treat them cautiously.</p>
          ) : null}
        </article>

        <ResponseRatesTable title="Response Rates by Role" rows={dashboard.response_rates.by_role} />
        <ResponseRatesTable title="Response Rates by Source" rows={dashboard.response_rates.by_source} />
        <ResponseRatesTable title="Response Rates by Company" rows={dashboard.response_rates.by_company} />
      </section>

      <section className="panel">
        <h2>Activity Over Time</h2>
        <p className="subtle">
          Historical import and workflow activity from the last {dashboard.activity_over_time.days} days in your collected data.
        </p>
        {activityRows.length === 0 ? (
          <p className="subtle">No tracked activity in this time window yet.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Imported</th>
                  <th>Verified</th>
                  <th>Scored</th>
                  <th>Packets</th>
                  <th>Opened</th>
                  <th>Applied</th>
                  <th>Interviews</th>
                  <th>Rejections</th>
                  <th>Offers</th>
                </tr>
              </thead>
              <tbody>
                {activityRows.map((row) => (
                  <tr key={row.date}>
                    <td>{row.date}</td>
                    <td>{row.jobs_imported}</td>
                    <td>{row.jobs_verified}</td>
                    <td>{row.jobs_scored}</td>
                    <td>{row.packets_generated}</td>
                    <td>{row.application_links_opened}</td>
                    <td>{row.applications_marked_applied}</td>
                    <td>{row.interviews}</td>
                    <td>{row.rejections}</td>
                    <td>{row.offers}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Stale Jobs</h2>
        {dashboard.stale_jobs.length === 0 ? (
          <p className="subtle">No stale or likely closed jobs were detected right now.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Verification</th>
                  <th>Likely Closed Score</th>
                  <th>Days Since First Seen</th>
                  <th>Suggested Action</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.stale_jobs.map((job) => (
                  <tr key={job.job_id}>
                    <td>
                      <Link href={`/jobs/${job.job_id}`} className="job-link">
                        {job.title}
                      </Link>
                      <div className="subtle">{job.company}</div>
                    </td>
                    <td>{job.verification_status}</td>
                    <td>{formatScore(job.likely_closed_score)}</td>
                    <td>{job.days_since_first_seen ?? "Unknown"}</td>
                    <td>{job.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Recommended Insights</h2>
        {insights.length === 0 ? (
          <p className="subtle">Import more jobs to see rule-based insights.</p>
        ) : (
          <ul className="list">
            {insights.map((insight) => (
              <li key={`${insight.category}-${insight.title}`}>
                <strong>{insight.title}:</strong> {insight.detail}
              </li>
            ))}
          </ul>
        )}
        <p className="subtle">Insights are generated from saved jobs, tracker events, and source data using local processing.</p>
        <p className="subtle">{dashboard.note}</p>
      </section>
    </div>
  );
}
