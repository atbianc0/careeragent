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
        <span className="eyebrow">Stage 8 - Browser Autofill with Playwright</span>
        <h1>Autofill</h1>
        <p className="hero-copy">
          Launch a visible Chromium browser, preview CareerAgent’s safe autofill plan, upload generated packet files when
          available, and stop before any final submit action.
        </p>
        <p className="hero-copy">
          CareerAgent never clicks Submit, Apply, Confirm, Finish, or similar final buttons. Manual review and manual
          submission are always required.
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
