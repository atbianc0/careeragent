import { StatCard } from "@/components/StatCard";
import { getMarketSummary, getTrackerSummary } from "@/lib/api";

export default async function HomePage() {
  const [market, tracker] = await Promise.all([getMarketSummary(), getTrackerSummary()]);
  const topPriorityLabel = market.top_priority_job ? market.top_priority_job.title : "None yet";
  const topPriorityHint = market.top_priority_job
    ? `${market.top_priority_job.company} • priority ${market.top_priority_job.overall_priority_score}`
    : "Verify and score jobs to surface ranked recommendations.";

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 7 - Tracker + Action Logging</span>
        <h1>CareerAgent</h1>
        <p className="hero-copy">
          CareerAgent is a customizable, human-in-the-loop AI job search assistant for importing jobs,
          checking whether saved job links still appear active, ranking them by fit and priority, and generating reviewable application packets
          while keeping the user in control of every final application step and tracked application outcome.
        </p>
        <p className="hero-copy">
          Current Stage: Stage 7 — Tracker + Action Logging. CareerAgent now tracks the application workflow, still does not submit applications,
          and Stage 8 will add browser autofill while stopping before submit.
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
              <span className="status-tag">Live now</span>
            </div>
            <p className="subtle">
              Stage 7 now tracks application progress, follow-ups, packet views, and outcomes after manual submission.
            </p>
          </article>
        </div>
      </section>

      <section className="stats-grid">
        <StatCard label="Jobs Found" value={tracker.total_jobs} hint="Saved PostgreSQL job records across the tracker workflow." />
        <StatCard label="Packets Ready" value={tracker.packet_ready_count} hint="Jobs with a Stage 6 packet ready for review." />
        <StatCard label="Applications Opened" value={tracker.application_opened_count} hint="Jobs whose application links were opened through CareerAgent." />
        <StatCard label="Applied" value={tracker.applied_count} hint="Jobs the user manually submitted and marked applied." />
        <StatCard label="Follow Ups" value={tracker.follow_up_count} hint="Jobs with a pending follow-up reminder in the app." />
        <StatCard label="Interviews" value={tracker.interview_count} hint="Jobs that reached an interview or recruiter response stage." />
        <StatCard label="Offers" value={tracker.offer_count} hint="Jobs that reached offer stage." />
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
            <li>Stage 7 tracker logging for application-link opens, notes, follow-ups, and manual outcomes.</li>
            <li>PostgreSQL-backed saved job records and detailed job pages.</li>
          </ul>
        </article>

        <article className="panel">
          <h2>Current Stage 7</h2>
          <ul className="list">
            <li>CareerAgent now tracks the application workflow after jobs are imported, verified, scored, and packeted.</li>
            <li>Users still manually review and submit every application.</li>
            <li>Follow-ups, interviews, rejections, and offers are logged without automating submission.</li>
          </ul>
          <p className="subtle">{market.note}</p>
        </article>

        <article className="panel">
          <h2>Coming Next</h2>
          <ul className="list">
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
