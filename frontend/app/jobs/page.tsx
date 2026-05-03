import { JobsManager } from "@/components/JobsManager";

export default function JobsPage() {
  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 7 - Tracker + Action Logging</span>
        <h1>Jobs</h1>
        <p className="hero-copy">
          Import jobs from pasted descriptions or pasted URLs, preview the rule-based parsing,
          save them to PostgreSQL, verify whether the saved job links still appear active, score them against your profile and resume,
          generate reviewable application packets, and track your manual application workflow in one place.
        </p>
        <p className="hero-copy">
          Each saved job now moves through the agent workflow: verify still hiring, score fit and priority, generate a Stage 6 packet,
          log Stage 7 actions like opening the application and marking it applied, then later prepare for Stage 8 autofill assistance.
        </p>
      </section>

      <JobsManager />
    </div>
  );
}
