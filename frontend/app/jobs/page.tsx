import { JobTable } from "@/components/JobTable";
import { getJobs } from "@/lib/api";

export default async function JobsPage() {
  const jobs = await getJobs();

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Sample Job Inventory</span>
        <h1>Jobs</h1>
        <p className="hero-copy">
          Stage 1 seeds sample jobs from the backend so we can validate the data model,
          scoring fields, and UI shape before building real import and verification flows.
        </p>
      </section>

      <section className="panel">
        <div className="section-title">
          <h2>Current Jobs</h2>
          <span className="subtle">{jobs.length} records</span>
        </div>
        <JobTable jobs={jobs} />
      </section>
    </div>
  );
}

