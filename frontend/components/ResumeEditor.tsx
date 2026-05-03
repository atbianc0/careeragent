"use client";

import { useEffect, useState } from "react";

import {
  type ResumeCompileResult,
  type ResumeDocument,
  type ResumeStatus,
  compileResume,
  createPrivateResume,
  getResume,
  getResumeStatus,
  saveResume
} from "@/lib/api";

export function ResumeEditor() {
  const [resume, setResume] = useState<ResumeDocument | null>(null);
  const [status, setStatus] = useState<ResumeStatus | null>(null);
  const [content, setContent] = useState("");
  const [compileResult, setCompileResult] = useState<ResumeCompileResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);

    try {
      const [resumeResponse, statusResponse] = await Promise.all([getResume(), getResumeStatus()]);
      setResume(resumeResponse);
      setStatus(statusResponse);
      setContent(resumeResponse.content);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load resume data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleCreatePrivateResume() {
    setSubmitting(true);
    setMessage(null);
    setError(null);

    try {
      const response = await createPrivateResume();
      const statusResponse = await getResumeStatus();
      setResume(response);
      setStatus(statusResponse);
      setContent(response.content);
      setMessage(response.message || "Private resume is ready.");
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Failed to create the private resume.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSaveResume() {
    setSubmitting(true);
    setMessage(null);
    setError(null);

    try {
      const response = await saveResume(content);
      const statusResponse = await getResumeStatus();
      setResume(response);
      setStatus(statusResponse);
      setContent(response.content);
      setMessage(response.message || "Saved resume successfully.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to save the resume.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCompileResume() {
    setSubmitting(true);
    setMessage(null);
    setError(null);

    try {
      const response = await compileResume();
      const statusResponse = await getResumeStatus();
      setCompileResult(response);
      setStatus(statusResponse);
      setMessage(response.message);
    } catch (compileError) {
      setError(compileError instanceof Error ? compileError.message : "Failed to compile the resume.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <section className="panel">
        <p className="subtle">Loading resume data...</p>
      </section>
    );
  }

  return (
    <div className="page">
      <section className="panel">
        <div className="section-title">
          <h2>Resume Source</h2>
          <span className="status-tag">{resume?.source || status?.active_source || "unknown"}</span>
        </div>
        <p className="subtle">
          Active file: <code>{resume?.path || status?.private_resume_path || "Unavailable"}</code>
        </p>
        <p className="subtle">{status?.github_safety_note}</p>
        <ul className="list">
          <li>Example files are safe public templates.</li>
          <li>Your real resume should live in <code>data/resume/base_resume.tex</code>, which is ignored by Git.</li>
          <li>Save before compiling so the latest LaTeX source is written to disk.</li>
          <li>Generated PDFs and outputs are ignored.</li>
        </ul>
        <p className="subtle">
          LaTeX compiler:{" "}
          {status?.latex_compiler_available
            ? status.compiler_name || "Available"
            : "Not installed. Compile may fail until xelatex or pdflatex is available."}
        </p>
        <div className="button-row">
          <button className="button secondary" type="button" onClick={handleCreatePrivateResume} disabled={submitting}>
            Create Private Resume From Example
          </button>
          <button className="button" type="button" onClick={handleSaveResume} disabled={submitting}>
            Save Resume
          </button>
          <button className="button ghost" type="button" onClick={handleCompileResume} disabled={submitting}>
            Compile PDF
          </button>
        </div>
        {message ? <p className="message success">{message}</p> : null}
        {error ? <p className="message error">{error}</p> : null}
      </section>

      <section className="panel">
        <div className="section-title">
          <h2>LaTeX Source</h2>
          <span className="subtle">Editable source for the active base resume</span>
        </div>
        <textarea
          className="textarea code-editor"
          rows={24}
          spellCheck={false}
          value={content}
          onChange={(event) => setContent(event.target.value)}
        />
      </section>

      <section className="panel">
        <h2>Compile Result</h2>
        {compileResult ? (
          <div className="meta-stack">
            <p className={`message ${compileResult.success ? "success" : "error"}`}>{compileResult.message}</p>
            <dl className="key-value">
              <dt>Success</dt>
              <dd>{compileResult.success ? "Yes" : "No"}</dd>
              <dt>Source</dt>
              <dd>{compileResult.source}</dd>
              <dt>Compiler</dt>
              <dd>{compileResult.compiler || "Not available"}</dd>
              <dt>Input</dt>
              <dd>
                <code>{compileResult.input_path || "Unavailable"}</code>
              </dd>
              <dt>Output</dt>
              <dd>
                <code>{compileResult.output_path || "No PDF generated"}</code>
              </dd>
            </dl>
            <details>
              <summary>Compiler logs</summary>
              <pre className="code-block">{compileResult.logs || "No compiler logs were produced."}</pre>
            </details>
          </div>
        ) : (
          <p className="subtle">
            No compile has been run yet. It is okay if compilation fails because LaTeX is not installed.
          </p>
        )}
      </section>
    </div>
  );
}

