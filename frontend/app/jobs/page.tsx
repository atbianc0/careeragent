import { JobsManager } from "@/components/JobsManager";

export default function JobsPage() {
  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 6 - Application Packet Generation</span>
        <h1>Jobs</h1>
        <p className="hero-copy">
          Import jobs from pasted descriptions or pasted URLs, preview the rule-based parsing,
          save them to PostgreSQL, verify whether the saved job links still appear active, score them against your profile and resume,
          and generate reviewable application packets for the jobs you want to pursue.
        </p>
        <p className="hero-copy">
          Each saved job now moves through the agent workflow: verify still hiring, score fit and priority, generate a Stage 6 packet,
          then later prepare for Stage 8 autofill assistance and manual review and submission.
        </p>
      </section>

      <JobsManager />
    </div>
  );
}
