import { ResumeEditor } from "@/components/ResumeEditor";

export default function ResumePage() {
  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 2 - Resume System</span>
        <h1>Resume</h1>
        <p className="hero-copy">
          Edit the base LaTeX resume source, keep the private file local and gitignored, and
          optionally compile a PDF when a LaTeX compiler is available.
        </p>
      </section>

      <ResumeEditor />
    </div>
  );
}

