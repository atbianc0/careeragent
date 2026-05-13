import Link from "next/link";

import { AIManager } from "@/components/AIManager";
import {
  getAIProviders,
  getAIStatus,
  getAutofillSessions,
  getAutofillStatus,
  getJobSourceSummary,
  getProfileStatus,
  getResumeStatus,
} from "@/lib/api";

const tabs = [
  { key: "ai", label: "AI Provider" },
  { key: "environment", label: "Environment" },
  { key: "safety", label: "Safety" },
  { key: "data", label: "Data/GitHub Safety" },
];

function tabHref(key: string) {
  return key === "ai" ? "/settings" : `/settings?tab=${key}`;
}

export default async function SettingsPage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>;
}) {
  const params = await searchParams;
  const activeTab = tabs.some((tab) => tab.key === params.tab) ? params.tab || "ai" : "ai";
  const [aiStatus, providers, autofillStatus, autofillSessions, sourceSummary, profileStatus, resumeStatus] = await Promise.all([
    getAIStatus(),
    getAIProviders(),
    getAutofillStatus(),
    getAutofillSessions().catch(() => []),
    getJobSourceSummary().catch(() => ({
      total_sources: 0,
      enabled_sources: 0,
      valid_sources: 0,
      partial_sources: 0,
      by_ats_type: {},
      last_imported_at: null,
      last_discovery_run_at: null,
    })),
    getProfileStatus(),
    getResumeStatus(),
  ]);

  return (
    <div className="page">
      <nav className="tab-nav" aria-label="Settings tabs">
        {tabs.map((tab) => (
          <Link className={activeTab === tab.key ? "tab-link active" : "tab-link"} href={tabHref(tab.key)} key={tab.key}>
            {tab.label}
          </Link>
        ))}
      </nav>

      {activeTab === "ai" ? (
        <>
          <section className="warning-panel">
            <h2>AI Provider Policy</h2>
            <p>
              CareerAgent uses one AI provider at a time. Choose <code>mock</code>, <code>openai</code>, or <code>gemini</code> with <code>AI_PROVIDER</code>.
              Core job search, parsing, matching, scoring, insights, and autofill remain local/rule-based.
            </p>
            <div className="panel-grid">
              <article className="panel subtle-panel">
                <h3>Selected Provider</h3>
                <dl className="key-value">
                  <dt>Active AI provider</dt>
                  <dd>{aiStatus.active_ai_provider}</dd>
                  <dt>External AI calls enabled</dt>
                  <dd>{aiStatus.ai_allow_external_calls ? "AI_ALLOW_EXTERNAL_CALLS=true" : "AI_ALLOW_EXTERNAL_CALLS=false"}</dd>
                  <dt>OpenAI configured</dt>
                  <dd>{aiStatus.openai_configured ? "Configured" : "Missing key"}</dd>
                  <dt>Gemini configured</dt>
                  <dd>{aiStatus.gemini_configured ? "Configured" : "Missing key"}</dd>
                  <dt>Current model</dt>
                  <dd>{aiStatus.current_model}</dd>
                  <dt>OpenAI model</dt>
                  <dd>{aiStatus.openai_model || "gpt-4o-mini"}</dd>
                  <dt>Gemini model</dt>
                  <dd>{aiStatus.gemini_model || "gemini-2.5-flash"}</dd>
                </dl>
              </article>
              <article className="panel subtle-panel">
                <h3>Allowed AI Assist</h3>
                <ul className="list">
                  <li>OpenAI or Gemini: tailored resume suggestions, cover letters, recruiter messages, long application answers, and one-time Job Finder keyword generation.</li>
                  <li>Only the selected <code>AI_PROVIDER</code> is used, even if both provider keys are configured.</li>
                  <li>All AI writing output is draft-only and must be reviewed manually.</li>
                </ul>
              </article>
              <article className="panel subtle-panel">
                <h3>Never API-Driven</h3>
                <ul className="list">
                  <li>Job URL parsing, matching, scoring, verification, insights, saved-source search, autofill, and applying stay local/rule-based.</li>
                  <li>CareerAgent does not scrape search engine HTML, LinkedIn, or Indeed automatically.</li>
                  <li>CareerAgent never auto-submits applications or clicks final apply/send/confirm buttons.</li>
                </ul>
              </article>
            </div>
            {!aiStatus.ai_allow_external_calls ? (
              <p className="message error">
                External AI calls are disabled. Set <code>AI_ALLOW_EXTERNAL_CALLS=true</code> to allow the selected provider after explicit user action.
              </p>
            ) : null}
            {aiStatus.active_ai_provider === "mock" ? <p className="message">Mock provider selected. No external AI credits will be used.</p> : null}
            {aiStatus.active_ai_provider === "openai" ? <p className="message">OpenAI selected. Only OpenAI will be used for allowed AI actions.</p> : null}
            {aiStatus.active_ai_provider === "gemini" ? <p className="message">Gemini selected. Only Gemini will be used for allowed AI actions.</p> : null}
            {aiStatus.both_provider_keys_configured ? (
              <p className="message">Both OpenAI and Gemini keys are configured, but only the selected AI_PROVIDER is used.</p>
            ) : null}
          </section>
          <AIManager initialStatus={aiStatus} initialProviders={providers.providers} />
        </>
      ) : null}

      {activeTab === "environment" ? (
        <section className="panel-grid">
          <article className="panel">
            <h2>Autofill Health</h2>
            <dl className="key-value">
              <dt>Backend browser mode</dt>
              <dd>{autofillStatus.configured_browser_mode}</dd>
              <dt>Visible autofill available</dt>
              <dd>{autofillStatus.visible_autofill_available ? "Yes" : "No"}</dd>
              <dt>Chromium</dt>
              <dd>{autofillStatus.chromium_installed ? "Yes" : "No"}</dd>
              <dt>Can continue from autofill</dt>
              <dd>{autofillStatus.can_continue_from_autofill ? "Yes" : "No"}</dd>
              <dt>Active sessions</dt>
              <dd>{autofillSessions.length || autofillStatus.active_sessions.length}</dd>
            </dl>
            <p className="subtle">
              {autofillStatus.visible_autofill_available
                ? "Visible review is available for safe field filling."
                : autofillStatus.environment_note || "Run the backend in headed mode with Chromium installed for visible review."}
            </p>
          </article>
          <article className="panel">
            <h2>Source Database Health</h2>
            <dl className="key-value">
              <dt>Total sources</dt>
              <dd>{sourceSummary.total_sources}</dd>
              <dt>Enabled sources</dt>
              <dd>{sourceSummary.enabled_sources}</dd>
              <dt>Valid/partial sources</dt>
              <dd>{sourceSummary.valid_sources}</dd>
              <dt>Partial sources</dt>
              <dd>{sourceSummary.partial_sources}</dd>
              <dt>Last import</dt>
              <dd>{sourceSummary.last_imported_at ? new Date(sourceSummary.last_imported_at).toLocaleString() : "None"}</dd>
              <dt>Last discovery run</dt>
              <dd>{sourceSummary.last_discovery_run_at ? new Date(sourceSummary.last_discovery_run_at).toLocaleString() : "None"}</dd>
            </dl>
            {Object.keys(sourceSummary.by_ats_type).length > 0 ? (
              <div className="pill-list">
                {Object.entries(sourceSummary.by_ats_type).map(([type, count]) => (
                  <span className="pill" key={type}>
                    {type.replace("_", " ")} ({count})
                  </span>
                ))}
              </div>
            ) : (
              <p className="subtle">No saved sources yet. Import job_sources.csv from job-database-script.</p>
            )}
            <div className="button-row">
              <Link className="button secondary compact" href="/jobs?tab=discover">
                Open Job Finder
              </Link>
            </div>
          </article>
          <article className="panel">
            <h2>LaTeX Resume Compiler</h2>
            <dl className="key-value">
              <dt>Compiler</dt>
              <dd>{resumeStatus.compiler_name || "Not found"}</dd>
              <dt>PDF Compile</dt>
              <dd>{resumeStatus.latex_compiler_available ? "Available" : "Unavailable"}</dd>
              <dt>Last PDF</dt>
              <dd>{resumeStatus.last_compile_output_path || "None yet"}</dd>
            </dl>
          </article>
        </section>
      ) : null}

      {activeTab === "safety" ? (
        <section className="warning-panel">
          <h2>Safety Boundary</h2>
          <ul className="list">
            <li>CareerAgent never auto-submits applications.</li>
            <li>CareerAgent never clicks final submit, apply, confirm, finish, or send buttons.</li>
            <li>CareerAgent never bypasses login walls, CAPTCHAs, or anti-bot protections.</li>
            <li>AI output is draft/reviewable and must not invent profile or resume facts.</li>
            <li>LinkedIn and Indeed discovery is manual pasted links only.</li>
          </ul>
        </section>
      ) : null}

      {activeTab === "data" ? (
        <section className="panel-grid">
          <article className="panel">
            <h2>Profile Data</h2>
            <dl className="key-value">
              <dt>Active source</dt>
              <dd>{profileStatus.active_source}</dd>
              <dt>Private profile</dt>
              <dd>{profileStatus.private_profile_exists ? "Exists locally" : "Not created yet"}</dd>
            </dl>
            <p className="subtle">{profileStatus.github_safety_note}</p>
          </article>
          <article className="panel">
            <h2>Resume Data</h2>
            <dl className="key-value">
              <dt>Active source</dt>
              <dd>{resumeStatus.active_source}</dd>
              <dt>Private resume</dt>
              <dd>{resumeStatus.private_resume_exists ? "Exists locally" : "Not created yet"}</dd>
            </dl>
            <p className="subtle">{resumeStatus.github_safety_note}</p>
          </article>
        </section>
      ) : null}
    </div>
  );
}
