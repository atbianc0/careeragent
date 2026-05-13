"use client";

import { useState } from "react";

import type { AIProviderInfo, AIProviderResult, AIStatus } from "@/lib/api";
import { testAIProvider } from "@/lib/api";

type AIManagerProps = {
  initialStatus: AIStatus;
  initialProviders: AIProviderInfo[];
};

export function AIManager({ initialStatus, initialProviders }: AIManagerProps) {
  const [prompt, setPrompt] = useState("Write one short safe sentence about reviewing AI drafts manually.");
  const [result, setResult] = useState<AIProviderResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleTest() {
    setTesting(true);
    setError(null);
    try {
      const response = await testAIProvider({
        task: "draft_cover_letter",
        prompt,
        user_enabled: true,
        user_triggered: true,
        max_output_tokens: 120,
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
            <dt>Selected AI_PROVIDER</dt>
            <dd>{initialStatus.active_ai_provider}</dd>
            <dt>Effective Runtime Provider</dt>
            <dd>{initialStatus.active_provider}</dd>
            <dt>Current Model</dt>
            <dd>{initialStatus.current_model}</dd>
            <dt>OpenAI Available</dt>
            <dd>{initialStatus.openai_available ? "Yes" : "No"}</dd>
            <dt>Gemini Available</dt>
            <dd>{initialStatus.gemini_available ? "Yes" : "No"}</dd>
            <dt>OpenAI Key Present</dt>
            <dd>{initialStatus.api_key_present ? "Yes" : "No"}</dd>
            <dt>Gemini Key Present</dt>
            <dd>{initialStatus.gemini_key_present ? "Yes" : "No"}</dd>
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
            The frontend never receives provider keys. CareerAgent only reports whether keys are present.
          </p>
        </article>
      </section>

      <section className="panel">
        <div className="section-title">
          <h2>Test Provider</h2>
          <span className="subtle">Safe draft output only</span>
        </div>
          <p className="subtle">
            This test uses the selected AI_PROVIDER from your environment and sends one short allowed writing-assist prompt.
            External calls only happen when AI_ALLOW_EXTERNAL_CALLS=true and the selected provider key is configured.
          </p>

        <div className="form-grid">
          <label className="field-group">
            <span>Selected provider</span>
            <input className="input" value={initialStatus.active_ai_provider || initialStatus.configured_provider} readOnly />
          </label>
          <label className="field-group">
            <span>Test action</span>
            <input className="input" value="draft_cover_letter" readOnly />
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
            {testing ? "Testing..." : "Run Selected Provider Test"}
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
              <dt>External API Used</dt>
              <dd>{result.raw?.api_used === true ? "Yes" : "No"}</dd>
              <dt>Model</dt>
              <dd>{typeof result.raw?.model === "string" ? result.raw.model : initialStatus.current_model}</dd>
              <dt>Blocked Reason</dt>
              <dd>{typeof result.raw?.blocked_reason === "string" ? result.raw.blocked_reason : "None"}</dd>
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
