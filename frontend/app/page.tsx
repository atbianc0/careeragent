import { StatCard } from "@/components/StatCard";
import { getMarketSummary } from "@/lib/api";

export default async function HomePage() {
  const market = await getMarketSummary();
  const topPriorityLabel = market.top_priority_job ? market.top_priority_job.title : "None yet";
  const topPriorityHint = market.top_priority_job
    ? `${market.top_priority_job.company} • priority ${market.top_priority_job.overall_priority_score}`
    : "Verify and score jobs to surface ranked recommendations.";

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 6 - Application Packet Generation</span>
        <h1>CareerAgent</h1>
        <p className="hero-copy">
          CareerAgent is a customizable, human-in-the-loop AI job search assistant for importing jobs,
          checking whether saved job links still appear active, ranking them by fit and priority, and generating reviewable application packets
          while keeping the user in control of every final application step.
        </p>
        <p className="hero-copy">
          Current Stage: Stage 6 — Application Packet Generation. Stages 1 through 5 are complete. Users still manually review and submit;
          autofill assistance comes later.
        </p>
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
              Stage 4 verifies saved job URLs and Stage 5 now scores fit, freshness, and priority with explainable evidence.
            </p>
          </article>
          <article className="workflow-step">
            <div className="workflow-heading">
              <h3>Generate Application Packet</h3>
              <span className="status-tag status-packet-ready">Live now</span>
            </div>
            <p className="subtle">
              Stage 6 builds tailored packet materials while preserving the user’s resume structure and style.
            </p>
          </article>
          <article className="workflow-step">
            <div className="workflow-heading">
              <h3>Autofill in Browser</h3>
              <span className="planned-chip">Planned</span>
            </div>
            <p className="subtle">
              Stage 8 will open Chromium, fill safe fields, upload files, and stop before any final submit action.
            </p>
          </article>
          <article className="workflow-step">
            <div className="workflow-heading">
              <h3>Manual Review + Submit</h3>
              <span className="status-tag">Always manual</span>
            </div>
            <p className="subtle">
              CareerAgent never auto-submits. The user always reviews the application and submits it themselves.
            </p>
          </article>
          <article className="workflow-step">
            <div className="workflow-heading">
              <h3>Track Outcome</h3>
              <span className="planned-chip">Planned</span>
            </div>
            <p className="subtle">
              Stage 7 will track application progress, follow-ups, and outcomes after manual submission.
            </p>
          </article>
        </div>
      </section>

      <section className="stats-grid">
        <StatCard label="Jobs Found" value={market.jobs_found} hint="Saved PostgreSQL job records, including optional sample/demo rows if enabled." />
        <StatCard label="Verified Jobs" value={market.verified_checked_jobs} hint="Jobs checked recently with Stage 4 verification." />
        <StatCard label="Scored Jobs" value={market.scored_jobs_count} hint="Jobs scored against the current profile and base resume." />
        <StatCard label="Packets Ready" value={market.packets_ready} hint="Jobs with at least one completed Stage 6 packet." />
        <StatCard label="Top Recommended Job" value={topPriorityLabel} hint={topPriorityHint} />
      </section>

      <section className="panel-grid">
        <article className="panel">
          <div className="section-title">
            <h2>What Works Now</h2>
          </div>
          <ul className="list">
            <li>Profile YAML editing with private-file fallback to the safe public example.</li>
            <li>LaTeX resume editing with optional PDF compilation when a compiler is installed.</li>
            <li>Job import from pasted descriptions and pasted URLs.</li>
            <li>Rule-based job parsing into structured fields without AI calls.</li>
            <li>Stage 4 verification for one job or all saved jobs with evidence and status estimates.</li>
            <li>Stage 5 scoring for one job or all saved jobs with ranked recommendations.</li>
            <li>Stage 6 application packet generation with private packet folders and frontend previews.</li>
            <li>PostgreSQL-backed saved job records and detailed job pages.</li>
          </ul>
        </article>

        <article className="panel">
          <h2>Current Stage 6</h2>
          <ul className="list">
            <li>CareerAgent can now generate reviewable application packets for selected jobs.</li>
            <li>Tailored resumes stay conservative and preserve the original LaTeX structure and style.</li>
            <li>Users still manually review and submit every application.</li>
          </ul>
          <p className="subtle">{market.note}</p>
        </article>

        <article className="panel">
          <h2>Coming Next</h2>
          <ul className="list">
            <li>Stage 7: tracker logging for manual applications and follow-ups.</li>
            <li>Stage 8: browser autofill assistance with manual final submission only.</li>
            <li>Optional future AI providers for more advanced drafting, while keeping deterministic fallbacks.</li>
          </ul>
        </article>

        <article className="warning-panel">
          <h2>Safety Boundary</h2>
          <p>
            CareerAgent is designed to stay human-in-the-loop. It may support research,
            verification, drafting, and later browser autofill, but it must never click final submit.
          </p>
          <p>Manual review and manual submission are required every time.</p>
        </article>
      </section>
    </div>
  );
}
