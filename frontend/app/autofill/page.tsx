import { getAutofillStatus } from "@/lib/api";

export default async function AutofillPage() {
  const status = await getAutofillStatus();

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Autofill Safety Boundary</span>
        <h1>Autofill</h1>
        <p className="hero-copy">
          Autofill is planned for a later stage. CareerAgent may fill forms in Chromium later,
          but the user will always review the result manually before submitting.
        </p>
      </section>

      <section className="warning-panel">
        <h2>Never Auto-Submit</h2>
        <p>{status.message}</p>
        <p>{status.manual_review_required}</p>
      </section>

      <section className="panel">
        <h2>Planned Behavior</h2>
        <ul className="list">
          <li>Launch headed Chromium using Playwright.</li>
          <li>Fill high-confidence factual fields only when safe.</li>
          <li>Stop before any final submit, apply, confirm, or completion action.</li>
          <li>User always performs the final review and the final click.</li>
        </ul>
      </section>
    </div>
  );
}

