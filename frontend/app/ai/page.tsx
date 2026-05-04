import Link from "next/link";

import { AIManager } from "@/components/AIManager";
import { getAIProviders, getAIStatus } from "@/lib/api";

export default async function AIPage() {
  const [status, providers] = await Promise.all([getAIStatus(), getAIProviders()]);

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 10 - AI Provider Integration</span>
        <h1>AI</h1>
        <p className="hero-copy">
          CareerAgent now supports an optional AI provider layer for job parsing, packet drafting, and market insights while
          preserving deterministic fallbacks and manual review.
        </p>
        <p className="hero-copy">
          To enable OpenAI, set <code>AI_PROVIDER=openai</code> and <code>OPENAI_API_KEY</code> in your private <code>.env</code>,
          then restart the app. The frontend never receives the key.
        </p>
        <div className="button-row">
          <Link href="/jobs" className="button secondary">
            Open Jobs
          </Link>
          <Link href="/market" className="button secondary">
            Open Market Analytics
          </Link>
        </div>
      </section>

      <AIManager initialStatus={status} initialProviders={providers.providers} />
    </div>
  );
}
