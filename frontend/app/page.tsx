import { StatCard } from "@/components/StatCard";
import { getJobs, getMarketSummary } from "@/lib/api";

export default async function HomePage() {
  const [jobs, market] = await Promise.all([getJobs(), getMarketSummary()]);

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 2 - Profile + LaTeX Resume System</span>
        <h1>CareerAgent</h1>
        <p className="hero-copy">
          CareerAgent is a customizable, human-in-the-loop assistant for finding jobs,
          verifying whether they are still open, generating tailored application packets,
          and eventually helping fill application forms without ever auto-submitting.
        </p>
        <p className="hero-copy">
          This stage adds editable YAML profile management, editable LaTeX resume management,
          private local file workflows, and optional PDF compilation when a LaTeX compiler is available.
        </p>
      </section>

      <section className="stats-grid">
        <StatCard label="Jobs Found" value={jobs.length} hint="Seeded sample jobs from the backend." />
        <StatCard
          label="Applications Opened"
          value={market.applications_opened}
          hint="Placeholder tracker count for the foundation stage."
        />
        <StatCard
          label="Packets Ready"
          value={market.packets_ready}
          hint="Packet generation arrives in later stages."
        />
        <StatCard
          label="Verified Open Jobs"
          value={market.verified_open_jobs}
          hint="Availability-aware prioritization starts in future stages."
        />
      </section>

      <section className="panel-grid">
        <article className="panel">
          <div className="section-title">
            <h2>What Exists Today</h2>
          </div>
          <ul className="list">
            <li>FastAPI routes for editable profile, editable resume, jobs, tracker, packets, market, and autofill.</li>
            <li>PostgreSQL-backed SQLAlchemy models for jobs, events, and application packets.</li>
            <li>Private and example file fallback for profile YAML and base LaTeX resume files.</li>
            <li>Basic Next.js app shell with profile and resume editors plus the future-stage workflow pages.</li>
          </ul>
        </article>

        <article className="warning-panel">
          <h2>Safety Boundary</h2>
          <p>
            CareerAgent is designed to stay human-in-the-loop. It may support research,
            drafting, and later browser autofill, but it must never click final submit.
          </p>
          <p>
            Manual review and manual submission are required every time.
          </p>
        </article>
      </section>
    </div>
  );
}
