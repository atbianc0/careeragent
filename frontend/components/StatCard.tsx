type StatCardProps = {
  label: string;
  value: number | string;
  hint: string;
};

export function StatCard({ label, value, hint }: StatCardProps) {
  return (
    <article className="stat-card">
      <p className="label">{label}</p>
      <p className="value">{value}</p>
      <p className="hint">{hint}</p>
    </article>
  );
}

