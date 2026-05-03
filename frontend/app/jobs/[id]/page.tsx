import Link from "next/link";

import { JobDetailView } from "@/components/JobDetailView";
import { getJob } from "@/lib/api";

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const numericId = Number(id);

  if (!Number.isInteger(numericId) || numericId <= 0) {
    return (
      <div className="page">
        <section className="warning-panel">
          <h1>Job Not Found</h1>
          <p>The provided job id is invalid.</p>
          <Link href="/jobs" className="inline-link">
            Back to Jobs
          </Link>
        </section>
      </div>
    );
  }

  const job = await getJob(numericId).catch(() => null);
  if (!job) {
    return (
      <div className="page">
        <section className="warning-panel">
          <h1>Job Not Found</h1>
          <p>CareerAgent could not load that job record.</p>
          <Link href="/jobs" className="inline-link">
            Back to Jobs
          </Link>
        </section>
      </div>
    );
  }

  return <JobDetailView initialJob={job} />;
}
