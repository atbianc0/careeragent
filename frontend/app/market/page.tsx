import { StatCard } from "@/components/StatCard";
import { getMarketSummary } from "@/lib/api";

export default async function MarketPage() {
  const summary = await getMarketSummary();

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Market Snapshot</span>
        <h1>Market</h1>
        <p className="hero-copy">
          The market dashboard starts with placeholder analytics now and is designed to expand
          into weekly trends, source quality, verification rates, and response tracking later.
        </p>
      </section>

      <section className="stats-grid">
        <StatCard label="Jobs Found" value={summary.jobs_found} hint="Current seeded inventory." />
        <StatCard
          label="Applications Opened"
          value={summary.applications_opened}
          hint="Placeholder tracker metric."
        />
        <StatCard
          label="Packets Ready"
          value={summary.packets_ready}
          hint="Will rise once packet generation is implemented."
        />
        <StatCard
          label="Verified Open Jobs"
          value={summary.verified_open_jobs}
          hint="Availability metrics will become real in Stage 4."
        />
      </section>

      <section className="panel">
        <h2>Top Target Locations</h2>
        <div className="pill-list">
          {summary.top_locations.map((location) => (
            <span className="pill" key={location}>
              {location}
            </span>
          ))}
        </div>
        <p className="subtle">{summary.note}</p>
      </section>
    </div>
  );
}

