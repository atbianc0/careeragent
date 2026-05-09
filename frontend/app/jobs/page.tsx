import Link from "next/link";

import { JobFinderManager } from "@/components/JobFinderManager";
import { JobsManager } from "@/components/JobsManager";

const jobTabs = [
  { key: "discover", label: "Discover" },
  { key: "candidates", label: "Candidates" },
  { key: "saved", label: "Saved Jobs" },
  { key: "recommended", label: "Recommended" },
  { key: "manual", label: "Manual Import" },
];

export default async function JobsPage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>;
}) {
  const params = await searchParams;
  const activeTab = jobTabs.some((tab) => tab.key === params.tab) ? params.tab || "saved" : "saved";
  const workflowSteps = [
    { label: "Find Jobs", href: "/jobs?tab=discover" },
    { label: "Review Candidates", href: "/jobs?tab=candidates" },
    { label: "Import Saved Jobs", href: "/jobs" },
    { label: "Verify", href: "/jobs" },
    { label: "Score", href: "/jobs" },
    { label: "Generate Packet", href: "/applications?tab=packets" },
    { label: "Apply/Autofill", href: "/applications?tab=autofill" },
    { label: "Track Outcome", href: "/applications" },
  ];

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Saved Jobs Pipeline</span>
        <h1>Jobs</h1>
        <p className="hero-copy">
          Find, review, save, verify, and score jobs.
        </p>
        <p className="hero-copy">
          Job details handle packet generation, safe autofill, application status, and follow-up tracking.
        </p>
        <nav className="workflow-strip" aria-label="Agent workflow">
          {workflowSteps.map((step, index) => (
            <Link href={step.href} className="workflow-link" key={`${step.label}-${index}`}>
              <span className="workflow-index">{index + 1}</span>
              <span>{step.label}</span>
            </Link>
          ))}
        </nav>
        <div className="button-row">
          <Link href="/jobs?tab=discover" className="button">
            Discover Jobs
          </Link>
          <Link href="/applications" className="button secondary">
            Open Applications
          </Link>
          <Link href="/insights" className="button secondary">
            Open Insights
          </Link>
        </div>
      </section>

      <nav className="tab-nav" aria-label="Jobs workflow tabs">
        {jobTabs.map((tab) => (
          <Link
            className={activeTab === tab.key ? "tab-link active" : "tab-link"}
            href={tab.key === "saved" ? "/jobs" : `/jobs?tab=${tab.key}`}
            key={tab.key}
          >
            {tab.label}
          </Link>
        ))}
      </nav>

      {activeTab === "discover" || activeTab === "candidates" ? <JobFinderManager /> : null}
      {activeTab === "saved" ? <JobsManager view="saved" /> : null}
      {activeTab === "recommended" ? <JobsManager view="recommended" /> : null}
      {activeTab === "manual" ? <JobsManager view="manual" /> : null}
    </div>
  );
}
