import Link from "next/link";

import { TrackerBoard } from "@/components/TrackerBoard";

export default function TrackerPage() {
  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 7 - Tracker + Action Logging</span>
        <h1>Tracker</h1>
        <p className="hero-copy">
          Track the application workflow across saved jobs, packet generation, autofill attempts, application-link opens,
          manual submissions, follow-ups, and outcomes.
        </p>
        <p className="hero-copy">
          CareerAgent still does not submit applications. The user manually reviews browser autofill, manually applies,
          manually updates final outcomes, and can compare tracked outcomes against market analytics and predictions.
        </p>
        <div className="button-row">
          <Link href="/market" className="button secondary">
            Open Market Analytics
          </Link>
          <Link href="/predictions" className="button secondary">
            Open Predictions
          </Link>
          <Link href="/ai" className="button secondary">
            Open AI Settings
          </Link>
          <Link href="/autofill" className="button secondary">
            Open Autofill
          </Link>
        </div>
      </section>

      <TrackerBoard />
    </div>
  );
}
