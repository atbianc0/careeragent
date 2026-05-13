import Link from "next/link";

import { JobFinderManager } from "@/components/JobFinderManager";
import { JobsManager } from "@/components/JobsManager";

type JobsTab = "discover" | "saved" | "applied" | "manual";

const jobTabs = [
  { key: "discover", label: "Discover" },
  { key: "saved", label: "Saved Jobs" },
  { key: "applied", label: "Applied Jobs" },
  { key: "manual", label: "Manual Import" },
] satisfies Array<{ key: JobsTab; label: string }>;

function normalizeTab(value: string | undefined): JobsTab {
  if (value === "saved_jobs" || value === "savedJobs") {
    return "saved";
  }
  if (value === "manual_import") {
    return "manual";
  }
  if (value === "discover" || value === "saved" || value === "applied" || value === "manual") {
    return value;
  }
  return "discover";
}

export default async function JobsPage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>;
}) {
  const params = await searchParams;
  const activeTab = normalizeTab(params.tab);

  return (
    <div className="page">
      <nav className="tab-nav" aria-label="Jobs workflow tabs">
        {jobTabs.map((tab) => (
          <Link
            className={activeTab === tab.key ? "tab-link active" : "tab-link"}
            href={`/jobs?tab=${tab.key}`}
            key={tab.key}
          >
            {tab.label}
          </Link>
        ))}
      </nav>

      {activeTab === "discover" ? <JobFinderManager /> : null}
      {activeTab === "saved" ? <JobsManager view="saved" /> : null}
      {activeTab === "applied" ? <JobsManager view="applied" /> : null}
      {activeTab === "manual" ? <JobsManager view="manual" /> : null}
    </div>
  );
}
