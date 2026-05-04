"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { StatCard } from "@/components/StatCard";
import {
  type PredictionDashboard,
  type PredictionJobRow,
  type PredictionQualityRow,
  type PredictionRecalculateSummary,
  exportPredictionData,
  getPredictionDashboard,
  recalculatePredictions,
} from "@/lib/api";

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

function formatConfidence(value: number | null | undefined, label?: string) {
  const score = value === null || value === undefined ? "0.00" : value.toFixed(2);
  return label ? `${label} (${score})` : score;
}

function formatAction(value: string) {
  return value.replace(/_/g, " ");
}

function getStatusClassName(status: string) {
  return `status-tag status-${status.replace(/_/g, "-")}`;
}

function PredictionJobsTable({
  title,
  rows,
  emptyMessage,
}: {
  title: string;
  rows: PredictionJobRow[];
  emptyMessage: string;
}) {
  return (
    <section className="panel">
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
                <th>Source</th>
                <th>Priority</th>
                <th>Close Risk</th>
                <th>Response</th>
                <th>Confidence</th>
                <th>Suggested Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((job) => (
                <tr key={`${title}-${job.job_id}`}>
                  <td>
                    <Link href={`/jobs/${job.job_id}`} className="job-link">
                      <strong>{job.title}</strong>
                    </Link>
                    <div className="subtle">{job.company}</div>
                  </td>
                  <td>{job.role_category || "Other"}</td>
                  <td>{job.source}</td>
                  <td className="score">{formatScore(job.predicted_priority_score)}</td>
                  <td>
                    <span className={getStatusClassName(job.risk_label)}>{formatScore(job.predicted_close_risk_score)}</span>
                    <div className="subtle">{job.risk_label}</div>
                  </td>
                  <td className="score">{formatScore(job.predicted_response_score)}</td>
                  <td>{formatConfidence(job.prediction_confidence, job.prediction_confidence_label)}</td>
                  <td>{formatAction(job.suggested_action)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function QualityTable({
  title,
  rows,
  scoreKey,
  labelKey,
  emptyMessage,
}: {
  title: string;
  rows: PredictionQualityRow[];
  scoreKey: "source_quality_score" | "role_quality_score";
  labelKey: "source" | "role_category";
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
                <th>Name</th>
                <th>Total Jobs</th>
                <th>Applied</th>
                <th>Response Rate</th>
                <th>Interview Rate</th>
                <th>Avg Priority</th>
                <th>Quality</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 10).map((row) => (
                <tr key={`${title}-${row.name}`}>
                  <td>
                    {row[labelKey] || row.name}
                    {row.sample_size_warning ? <div className="subtle">Small sample size</div> : null}
                  </td>
                  <td>{row.total_jobs}</td>
                  <td>{row.applied_jobs}</td>
                  <td>{formatRate(row.response_rate)}</td>
                  <td>{formatRate(row.interview_rate)}</td>
                  <td>{formatScore(row.average_priority_score)}</td>
                  <td>{formatScore(row[scoreKey] ?? 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}

function DayRows({ rows }: { rows: Array<{ weekday: string; count: number }> }) {
  if (rows.length === 0) {
    return <p className="subtle">Not enough data yet.</p>;
  }
  return (
    <ul className="list">
      {rows.map((row) => (
        <li key={row.weekday}>
          {row.weekday}: {row.count}
        </li>
      ))}
    </ul>
  );
}

export default function PredictionsPage() {
  const [dashboard, setDashboard] = useState<PredictionDashboard | null>(null);
  const [summary, setSummary] = useState<PredictionRecalculateSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadDashboard() {
    setLoading(true);
    try {
      const response = await getPredictionDashboard();
      setDashboard(response);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load predictions.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRecalculate() {
    setRecalculating(true);
    setError(null);
    setSummary(null);
    try {
      const response = await recalculatePredictions();
      setSummary(response);
      await loadDashboard();
    } catch (recalculateError) {
      setError(recalculateError instanceof Error ? recalculateError.message : "Failed to recalculate predictions.");
    } finally {
      setRecalculating(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  const exportJsonUrl = exportPredictionData("json");
  const exportCsvUrl = exportPredictionData("csv");
  const sourceRows = dashboard?.source_quality.sources || [];
  const roleRows = dashboard?.role_quality.roles || [];

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 11 - Prediction and Improvements</span>
        <h1>Predictions</h1>
        <p className="hero-copy">
          CareerAgent now estimates application priority, close risk, response likelihood, source quality, role quality,
          and apply-window signals from your stored data.
        </p>
        <p className="hero-copy">
          These are cautious estimates, not guarantees. Small datasets stay low confidence, and CareerAgent avoids making
          response or timing claims when there is not enough history.
        </p>
        <div className="button-row">
          <button className="button" type="button" onClick={handleRecalculate} disabled={recalculating}>
            {recalculating ? "Recalculating..." : "Recalculate Predictions"}
          </button>
          <Link href="/jobs" className="button secondary">
            Open Jobs
          </Link>
          <Link href="/market" className="button secondary">
            Open Market
          </Link>
          <a href={exportJsonUrl} className="button secondary" target="_blank" rel="noreferrer">
            Export JSON
          </a>
          <a href={exportCsvUrl} className="button secondary" target="_blank" rel="noreferrer">
            Export CSV
          </a>
        </div>
        {error ? <p className="message error">{error}</p> : null}
        {summary ? (
          <p className="message success">
            {summary.message} Updated {summary.updated_jobs} of {summary.total_jobs} jobs.
          </p>
        ) : null}
      </section>

      {loading || !dashboard ? (
        <section className="panel">
          <p className="subtle">Loading prediction dashboard...</p>
        </section>
      ) : (
        <>
          <section className="stats-grid">
            <StatCard label="High Priority Jobs" value={dashboard.summary.high_priority_jobs} hint="Jobs estimated above 70 priority and not already in an applied or terminal status." />
            <StatCard label="High Close-Risk Jobs" value={dashboard.summary.high_close_risk_jobs} hint="Jobs that may need reverification, fast action, or closure review." />
            <StatCard label="Low Confidence" value={dashboard.summary.low_confidence_predictions} hint="Predictions with limited scoring, verification, or outcome history." />
            <StatCard label="Best Observed Apply Day" value={dashboard.summary.best_observed_apply_day || "Not enough data"} hint="Based only on your collected history when enough data exists." />
          </section>

          {dashboard.summary.warning ? (
            <section className="warning-panel">
              <h2>Limited Data</h2>
              <p>{dashboard.summary.warning}</p>
              <p>Import and score jobs before predictions become useful. Track applications and outcomes to improve response estimates.</p>
            </section>
          ) : null}

          <PredictionJobsTable
            title="Top Priority Jobs"
            rows={dashboard.top_priority_jobs}
            emptyMessage="Import and score jobs before predictions become useful."
          />

          <PredictionJobsTable
            title="Close Risk"
            rows={dashboard.high_close_risk_jobs}
            emptyMessage="No high close-risk jobs are currently estimated."
          />

          <section className="panel-grid">
            <article className="panel">
              <h2>Response Likelihood</h2>
              <dl className="key-value">
                <dt>Applied Jobs</dt>
                <dd>{dashboard.response_likelihood_summary.applied_jobs}</dd>
                <dt>Responses</dt>
                <dd>{dashboard.response_likelihood_summary.response_count}</dd>
                <dt>Avg Response Estimate</dt>
                <dd>{formatScore(dashboard.response_likelihood_summary.average_predicted_response_score)}</dd>
              </dl>
              {dashboard.response_likelihood_summary.warning ? (
                <p className="subtle">{dashboard.response_likelihood_summary.warning}</p>
              ) : (
                <p className="subtle">Response estimates use stored outcomes and stay conservative.</p>
              )}
            </article>

            <article className="panel">
              <h2>Apply Windows</h2>
              <dl className="key-value">
                <dt>Recommended Days</dt>
                <dd>{dashboard.apply_windows.recommended_focus_days.join(", ") || "Not enough data"}</dd>
                <dt>Confidence</dt>
                <dd>{formatConfidence(dashboard.apply_windows.confidence_score, dashboard.apply_windows.confidence)}</dd>
                <dt>Based On</dt>
                <dd>{dashboard.apply_windows.based_on.replace(/_/g, " ")}</dd>
              </dl>
              {dashboard.apply_windows.warning ? <p className="subtle">{dashboard.apply_windows.warning}</p> : null}
              {dashboard.apply_windows.default_guidance.length > 0 ? (
                <ul className="list">
                  {dashboard.apply_windows.default_guidance.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
            </article>
          </section>

          <section className="panel-grid">
            <QualityTable
              title="Source Quality"
              rows={sourceRows}
              scoreKey="source_quality_score"
              labelKey="source"
              emptyMessage="Track applications and outcomes to estimate source quality."
            />
            <QualityTable
              title="Role Quality"
              rows={roleRows}
              scoreKey="role_quality_score"
              labelKey="role_category"
              emptyMessage="Track applications and outcomes to estimate role quality."
            />
          </section>

          <section className="panel-grid">
            <article className="panel">
              <h2>Observed Best Import Days</h2>
              <DayRows rows={dashboard.apply_windows.observed_best_import_days} />
            </article>
            <article className="panel">
              <h2>Observed Best Application Days</h2>
              <DayRows rows={dashboard.apply_windows.observed_best_application_days} />
            </article>
            <article className="panel">
              <h2>Busiest Job Days</h2>
              <DayRows rows={dashboard.apply_windows.busiest_job_days} />
            </article>
          </section>

          <section className="panel">
            <h2>Prediction Insights</h2>
            {dashboard.insights.length === 0 ? (
              <p className="subtle">Import and score jobs before prediction insights become useful.</p>
            ) : (
              <ul className="list">
                {dashboard.insights.map((insight) => (
                  <li key={`${insight.category}-${insight.title}`}>
                    <strong>{insight.title}:</strong> {insight.detail}
                  </li>
                ))}
              </ul>
            )}
            <p className="subtle">{dashboard.note}</p>
          </section>
        </>
      )}
    </div>
  );
}
