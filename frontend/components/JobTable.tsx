import { Job } from "@/lib/api";

type JobTableProps = {
  jobs: Job[];
};

function formatScore(value: number) {
  return value.toFixed(1);
}

export function JobTable({ jobs }: JobTableProps) {
  if (jobs.length === 0) {
    return <p className="subtle">No jobs available yet.</p>;
  }

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Company</th>
            <th>Title</th>
            <th>Location</th>
            <th>Verification</th>
            <th>Verification Score</th>
            <th>Resume Match</th>
            <th>Priority Score</th>
            <th>Application Status</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id}>
              <td>{job.company}</td>
              <td>
                <strong>{job.title}</strong>
              </td>
              <td>{job.location}</td>
              <td>
                <span className="status-tag">{job.verification_status}</span>
              </td>
              <td className="score">{formatScore(job.verification_score)}</td>
              <td className="score">{formatScore(job.resume_match_score)}</td>
              <td className="score">{formatScore(job.overall_priority_score)}</td>
              <td>{job.application_status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

