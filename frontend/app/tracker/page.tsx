export default function TrackerPage() {
  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Tracker Placeholder</span>
        <h1>Tracker</h1>
        <p className="hero-copy">
          The tracker will become the timeline for saved jobs, verification checks, packet
          generation, autofill sessions, manual applications, interviews, and follow-ups.
        </p>
      </section>

      <section className="panel">
        <h2>What Later Stages Add</h2>
        <ul className="list">
          <li>Application event logging with timestamps and notes.</li>
          <li>Status transitions such as packet-ready, manually applied, interview, and offer.</li>
          <li>Action history so users can see what CareerAgent prepared and what they reviewed.</li>
        </ul>
      </section>
    </div>
  );
}

