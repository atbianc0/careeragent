import Link from "next/link";

import { ProfileEditor } from "@/components/ProfileEditor";
import { ResumeEditor } from "@/components/ResumeEditor";

const tabs = [
  { key: "profile", label: "Profile" },
  { key: "resume", label: "Resume" },
  { key: "defaults", label: "Application Defaults" },
  { key: "style", label: "Writing Style" },
];

function tabHref(key: string) {
  return key === "profile" ? "/profile" : `/profile?tab=${key}`;
}

export default async function ProfilePage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>;
}) {
  const params = await searchParams;
  const activeTab = tabs.some((tab) => tab.key === params.tab) ? params.tab || "profile" : "profile";

  return (
    <div className="page">
      <nav className="tab-nav" aria-label="Profile tabs">
        {tabs.map((tab) => (
          <Link className={activeTab === tab.key ? "tab-link active" : "tab-link"} href={tabHref(tab.key)} key={tab.key}>
            {tab.label}
          </Link>
        ))}
      </nav>

      {activeTab === "profile" ? <ProfileEditor /> : null}
      {activeTab === "resume" ? <ResumeEditor /> : null}
      {activeTab === "defaults" || activeTab === "style" ? (
        <section className="panel">
          <h2>{activeTab === "defaults" ? "Application Defaults" : "Writing Style"}</h2>
          <p className="subtle">
            These values live in the profile YAML. Open the Profile tab to edit the underlying fields safely.
          </p>
        </section>
      ) : null}
    </div>
  );
}
