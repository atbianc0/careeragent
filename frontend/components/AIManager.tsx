"use client";

import { useState } from "react";

import type { AIProviderInfo, AIProviderResult, AIStatus } from "@/lib/api";
import { testAIProvider } from "@/lib/api";

type AIManagerProps = {
  initialStatus: AIStatus;
  initialProviders: AIProviderInfo[];
};

export function AIManager({ initialStatus, initialProviders }: AIManagerProps) {
  const [provider, setProvider] = useState(initialStatus.active_provider || "mock");
  const [prompt, setPrompt] = useState("Write one short safe sentence about reviewing AI drafts manually.");
  const [result, setResult] = useState<AIProviderResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleTest() {
    setTesting(true);
    setError(null);
    try {
      const response = await testAIProvider({
        provider,
        task: "test",
        prompt,
      });
      setResult(response);
    } catch (testError) {
      setResult(null);
      setError(testError instanceof Error ? testError.message : "Failed to test the selected AI provider.");
    } finally {
      setTesting(false);
    }
  }

  return (
    <>
      <section className="panel-grid">
        <article className="panel">
          <h2>Provider Status</h2>
          <dl className="key-value">
            <dt>Configured Provider</dt>
            <dd>{initialStatus.configured_provider}</dd>
            <dt>Active Provider</dt>
            <dd>{initialStatus.active_provider}</dd>
            <dt>OpenAI Available</dt>
            <dd>{initialStatus.openai_available ? "Yes" : "No"}</dd>
            <dt>Local Available</dt>
            <dd>{initialStatus.local_available ? "Yes" : "No"}</dd>
            <dt>API Key Present</dt>
            <dd>{initialStatus.api_key_present ? "Yes" : "No"}</dd>
            <dt>Safety Mode</dt>
            <dd>{initialStatus.safety_mode ? "Enabled" : "Disabled"}</dd>
          </dl>
          <p className="subtle">{initialStatus.message}</p>
        </article>

        <article className="panel">
          <h2>Supported Providers</h2>
          <ul className="list">
            {initialProviders.map((entry) => (
              <li key={entry.name}>
                <strong>{entry.name}</strong>: {entry.available ? "available" : "unavailable"}
                {entry.message ? ` — ${entry.message}` : ""}
              </li>
            ))}
          </ul>
          <p className="subtle">
            The frontend never receives the API key itself. CareerAgent only reports whether a key is present.
          </p>
        </article>
      </section>

      <section className="panel">
        <div className="section-title">
          <h2>Test Provider</h2>
          <span className="subtle">Safe draft output only</span>
        </div>
        <p className="subtle">
          AI output is a draft. Review before using it. CareerAgent should not invent experience, credentials, or work authorization details.
        </p>

        <div className="form-grid">
          <label className="field-group">
            <span>Provider</span>
            <select className="input" value={provider} onChange={(event) => setProvider(event.target.value)}>
              {initialProviders.map((entry) => (
                <option key={entry.name} value={entry.name}>
                  {entry.name} {entry.available ? "" : "(unavailable)"}
                </option>
              ))}
            </select>
          </label>

          <label className="field-group">
            <span>Prompt</span>
            <textarea
              className="textarea"
              rows={6}
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
            />
          </label>
        </div>

        <div className="button-row">
          <button className="button" type="button" onClick={handleTest} disabled={testing}>
            {testing ? "Testing..." : "Run Provider Test"}
          </button>
        </div>

        {error ? <p className="message error">{error}</p> : null}
        {result ? (
          <div className="panel subtle-panel">
            <h3>Test Result</h3>
            <dl className="key-value">
              <dt>Provider</dt>
              <dd>{result.provider}</dd>
              <dt>Success</dt>
              <dd>{result.success ? "Yes" : "No"}</dd>
              <dt>Task</dt>
              <dd>{result.task}</dd>
            </dl>
            {result.content ? <pre className="code-block">{result.content}</pre> : null}
            {result.parsed_json ? <pre className="code-block">{JSON.stringify(result.parsed_json, null, 2)}</pre> : null}
            {result.warnings.length > 0 ? (
              <>
                <h4>Warnings</h4>
                <ul className="list">
                  {result.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </>
            ) : null}
            {result.safety_notes.length > 0 ? (
              <>
                <h4>Safety Notes</h4>
                <ul className="list">
                  {result.safety_notes.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </>
            ) : null}
          </div>
        ) : null}
      </section>
    </>
  );
}
