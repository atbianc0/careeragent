import Link from "next/link";

import { JobsManager } from "@/components/JobsManager";

export default function JobsPage() {
  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 11 - Prediction and Improvements</span>
        <h1>Jobs</h1>
        <p className="hero-copy">
          Import jobs from pasted descriptions or pasted URLs, preview the parsing,
          save them to PostgreSQL, verify whether the saved job links still appear active, score them against your profile and resume,
          generate reviewable application packets, track your manual application workflow, and feed the market analytics dashboard with real saved data.
        </p>
        <p className="hero-copy">
          Each saved job now moves through the agent workflow: verify still hiring, score fit and priority, generate a Stage 6 packet,
          log Stage 7 actions like opening the application and marking it applied, use Stage 8 browser autofill while still
          stopping before any final submit action, review Stage 9 analytics for stale jobs, skill gaps, and observed response trends,
          optionally use Stage 10 AI drafts, and use Stage 11 predictions as cautious guidance without ever making an API key required.
        </p>
        <div className="button-row">
          <Link href="/predictions" className="button">
            Open Predictions
          </Link>
          <Link href="/market" className="button secondary">
            Open Market Analytics
          </Link>
          <Link href="/ai" className="button secondary">
            Open AI Settings
          </Link>
          <Link href="/tracker" className="button secondary">
            Open Tracker
          </Link>
        </div>
      </section>

      <JobsManager />
    </div>
  );
}
