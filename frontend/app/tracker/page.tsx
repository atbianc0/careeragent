import { TrackerBoard } from "@/components/TrackerBoard";

export default function TrackerPage() {
  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 7 - Tracker + Action Logging</span>
        <h1>Tracker</h1>
        <p className="hero-copy">
          Track the application workflow across saved jobs, packet generation, application-link opens, manual submissions,
          follow-ups, and outcomes.
        </p>
        <p className="hero-copy">
          CareerAgent still does not submit applications. The user manually reviews, manually applies, and manually updates
          final outcomes.
        </p>
      </section>

      <TrackerBoard />
    </div>
  );
}
