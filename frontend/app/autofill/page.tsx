import { AutofillManager } from "@/components/AutofillManager";
import { getAutofillSafety, getAutofillStatus } from "@/lib/api";

export default async function AutofillPage({
  searchParams,
}: {
  searchParams: Promise<{ jobId?: string }>;
}) {
  const { jobId } = await searchParams;
  const numericJobId = jobId ? Number(jobId) : null;

  const [status, safety] = await Promise.all([
    getAutofillStatus(),
    getAutofillSafety().catch(() => ({
      blocked_final_action_words: [],
      safety_rules: [],
    })),
  ]);

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Autofill</span>
        <h1>Autofill</h1>
        <p className="hero-copy">
          Open the application manually or let CareerAgent fill a visible browser session. CareerAgent never submits.
        </p>
      </section>

      <AutofillManager
        status={status}
        safety={safety}
        initialJobId={numericJobId && Number.isInteger(numericJobId) && numericJobId > 0 ? numericJobId : null}
      />
    </div>
  );
}
