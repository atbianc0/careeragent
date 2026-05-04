import Link from "next/link";

import { StatCard } from "@/components/StatCard";
import { getMarketSummary, getPredictionDashboard } from "@/lib/api";

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

function topRequestedSkillsLabel(skills: Array<{ skill: string; count: number }>) {
  if (skills.length === 0) {
    return "Not enough data yet";
  }
  return skills
    .slice(0, 3)
    .map((entry) => `${entry.skill} (${entry.count})`)
    .join(", ");
}

export default async function HomePage() {
  const [market, prediction] = await Promise.all([getMarketSummary(), getPredictionDashboard()]);

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 11 - Prediction and Improvements</span>
        <h1>CareerAgent</h1>
        <p className="hero-copy">
          CareerAgent is a customizable, human-in-the-loop AI job search assistant for importing jobs,
          verifying whether they still appear active, scoring fit and priority, generating reviewable application packets,
          assisting with safe browser autofill, tracking application workflow, summarizing market trends, and using stored history for cautious prediction estimates.
        </p>
        <p className="hero-copy">
          Current Stage: Stage 11 - Prediction and Improvements. Predictions are local, explainable estimates from collected data,
          not guarantees of interviews, offers, or response timing.
        </p>
        <div className="button-row">
          <Link href="/predictions" className="button">
            Open Predictions
          </Link>
          <Link href="/market" className="button">
            Open Market Analytics
          </Link>
          <Link href="/ai" className="button secondary">
            Open AI Settings
          </Link>
          <Link href="/jobs" className="button secondary">
            Review Jobs
          </Link>
          <Link href="/tracker" className="button secondary">
            Open Tracker
          </Link>
        </div>
      </section>

      <section className="panel">
        <div className="section-title">
          <h2>CareerAgent Workflow</h2>
          <span className="subtle">Target agent experience</span>
        </div>
        <div className="workflow-grid">
          <article className="workflow-step">
            <div className="workflow-heading">
              <h3>Setup Profile + Resume</h3>
              <span className="status-tag">Live now</span>
            </div>
            <p className="subtle">
              Create your private profile YAML and base LaTeX resume once, then keep refining them locally.
            </p>
          </article>
          <article className="workflow-step">
            <div className="workflow-heading">
              <h3>Import or Find Jobs</h3>
              <span className="status-tag">Import live now</span>
            </div>
            <p className="subtle">
              Pasted descriptions and pasted URLs work today. Broader automated discovery is still planned.
            </p>
          </article>
          <article className="workflow-step">
            <div className="workflow-heading">
              <h3>Verify + Rank Jobs</h3>
              <span className="status-tag">Verify + rank live now</span>
            </div>
            <p className="subtle">
              CareerAgent verifies saved job URLs, scores fit and priority, and keeps the ranking explainable.
            </p>
          </article>
          <article className="workflow-step">
            <div className="workflow-heading">
              <h3>Generate Application Packet</h3>
              <span className="status-tag status-packet-ready">Live now</span>
            </div>
            <p className="subtle">
              Stage 6 builds tailored packet materials while preserving the user's resume structure and style.
            </p>
          </article>
          <article className="workflow-step">
            <div className="workflow-heading">
              <h3>Autofill in Browser</h3>
              <span className="status-tag status-open">Live now</span>
            </div>
            <p className="subtle">
              Stage 8 opens Chromium, fills safe fields, uploads packet files when available, and stops before any final submit action.
            </p>
          </article>
          <article className="workflow-step">
            <div className="workflow-heading">
              <h3>Track Outcome</h3>
              <span className="status-tag">Live now</span>
            </div>
            <p className="subtle">
              Tracker logging captures packet generation, autofill attempts, follow-ups, manual applications, and outcomes.
            </p>
          </article>
          <article className="workflow-step">
            <div className="workflow-heading">
              <h3>Analyze Market Trends</h3>
              <span className="status-tag">Stage 9 live</span>
            </div>
            <p className="subtle">
              CareerAgent now summarizes pipeline health, requested skills, stale jobs, and observed application outcomes from your saved data.
            </p>
          </article>
          <article className="workflow-step">
            <div className="workflow-heading">
              <h3>Optional AI Drafts</h3>
              <span className="status-tag">Stage 10 live</span>
            </div>
            <p className="subtle">
              MockProvider works with no key, and optional OpenAI drafts can improve parsing, packet drafts, and insight summaries while staying reviewable.
            </p>
          </article>
          <article className="workflow-step">
            <div className="workflow-heading">
              <h3>Predict Next Actions</h3>
              <span className="status-tag">New in Stage 11</span>
            </div>
            <p className="subtle">
              CareerAgent estimates priority, close risk, source quality, role quality, response likelihood, and apply windows from stored history.
            </p>
          </article>
        </div>
      </section>

      <section className="stats-grid">
        <StatCard label="Total Jobs" value={market.total_jobs} hint="All saved jobs currently tracked in PostgreSQL." />
        <StatCard label="Scored Jobs" value={market.scored_jobs} hint="Jobs with Stage 5 scoring available for analytics." />
        <StatCard label="Packet Ready" value={market.packet_ready_jobs} hint="Jobs with Stage 6 packet materials ready for review." />
        <StatCard label="Applied" value={market.applied_jobs} hint="Jobs you manually marked applied after real submission." />
        <StatCard label="Interviews" value={market.interview_jobs} hint="Jobs that have reached interview or recruiter-response stage." />
        <StatCard label="Response Rate" value={formatRate(market.response_rate)} hint="Observed response rate from applied jobs and recorded outcomes." />
        <StatCard label="High Priority Jobs" value={prediction.summary.high_priority_jobs} hint="Jobs estimated worth reviewing first after prediction scoring." />
        <StatCard label="High Close-Risk Jobs" value={prediction.summary.high_close_risk_jobs} hint="Jobs that may need reverification or quick action." />
        <StatCard label="Low Confidence Predictions" value={prediction.summary.low_confidence_predictions} hint="Predictions limited by missing scoring, verification, or outcome history." />
        <StatCard label="Best Observed Apply Day" value={prediction.summary.best_observed_apply_day || "Not enough data"} hint="Observed from your data only, when enough history exists." />
        <StatCard
          label="Avg Match Score"
          value={formatScore(market.average_resume_match_score)}
          hint="Average resume-match score across currently scored jobs."
        />
        <StatCard label="Stale Jobs" value={market.stale_jobs_count} hint="Jobs that look old, likely closed, or due for reverification." />
      </section>

      <section className="panel-grid">
        <article className="panel">
          <div className="section-title">
            <h2>What Works Now</h2>
          </div>
          <ul className="list">
            <li>Private profile YAML and LaTeX resume editing with safe public fallbacks.</li>
            <li>Rule-based job import, parsing, verification, and priority scoring.</li>
            <li>Tailored Stage 6 application packet generation with private output folders.</li>
            <li>Stage 7 tracker logging for application opens, follow-ups, and manual outcomes.</li>
            <li>Stage 8 Playwright-based browser autofill that stops before submit.</li>
            <li>Stage 9 pipeline, skill, score, stale-job, and response-rate analytics.</li>
          </ul>
        </article>

        <article className="panel">
          <h2>Current Stage 11</h2>
          <ul className="list">
            <li>Prediction scores combine existing priority with source, role, response, and close-risk signals.</li>
            <li>Small datasets are labeled low confidence instead of overstated.</li>
            <li>Exports exclude profile, resume, packet contents, generated files, notes, and secrets.</li>
          </ul>
          <p className="subtle">{market.note}</p>
          <p className="subtle">Top requested skills so far: {topRequestedSkillsLabel(market.top_requested_skills)}</p>
        </article>

        <article className="panel">
          <h2>Explore Next</h2>
          <ul className="list">
            <li>Open Predictions to recalculate cautious priority, response, and close-risk estimates.</li>
            <li>Open Market Analytics to review role, source, location, and outcome trends.</li>
            <li>Use Tracker to compare packet-ready jobs against jobs you have actually applied to.</li>
            <li>Export JSON or CSV from the Market page for personal analysis.</li>
          </ul>
        </article>

        <article className="panel">
          <h2>Coming Next</h2>
          <ul className="list">
            <li>Future stages can refine predictions with user feedback and stronger follow-up planning.</li>
            <li>Future local-model support can plug into the LocalLLMProvider placeholder.</li>
          </ul>
        </article>

        <article className="warning-panel">
          <h2>Safety Boundary</h2>
          <p>
            CareerAgent is designed to stay human-in-the-loop. It may support research,
            verification, drafting, analytics, and browser autofill, but it must never click final submit.
          </p>
          <p>Manual review and manual submission are required every time.</p>
        </article>
      </section>
    </div>
  );
}
