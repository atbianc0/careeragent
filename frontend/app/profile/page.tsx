import { getProfile } from "@/lib/api";

export default async function ProfilePage() {
  const profile = await getProfile();

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Read-Only Profile</span>
        <h1>Profile</h1>
        <p className="hero-copy">
          This page reads from <code>data/profile.yaml</code> when present and falls back to{" "}
          <code>data/profile.example.yaml</code>. Editing from the UI is planned for Stage 2.
        </p>
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>Personal</h2>
          <dl className="key-value">
            <dt>Name</dt>
            <dd>{profile.personal.name || "Not set yet"}</dd>
            <dt>Email</dt>
            <dd>{profile.personal.email || "Not set yet"}</dd>
            <dt>Phone</dt>
            <dd>{profile.personal.phone || "Not set yet"}</dd>
            <dt>Location</dt>
            <dd>{profile.personal.location || "Not set yet"}</dd>
          </dl>
        </article>

        <article className="panel">
          <h2>Education</h2>
          <dl className="key-value">
            <dt>School</dt>
            <dd>{profile.education.school}</dd>
            <dt>Degree</dt>
            <dd>{profile.education.degree}</dd>
            <dt>Graduation</dt>
            <dd>{profile.education.graduation}</dd>
          </dl>
        </article>

        <article className="panel">
          <h2>Target Roles</h2>
          <div className="pill-list">
            {profile.target_roles.map((role) => (
              <span className="pill" key={role}>
                {role}
              </span>
            ))}
          </div>
        </article>

        <article className="panel">
          <h2>Skills</h2>
          <div className="pill-list">
            {profile.skills.map((skill) => (
              <span className="pill" key={skill}>
                {skill}
              </span>
            ))}
          </div>
        </article>

        <article className="panel">
          <h2>Links</h2>
          <dl className="key-value">
            <dt>LinkedIn</dt>
            <dd>{profile.links.linkedin || "Not set yet"}</dd>
            <dt>GitHub</dt>
            <dd>{profile.links.github || "Not set yet"}</dd>
            <dt>Portfolio</dt>
            <dd>{profile.links.portfolio || "Not set yet"}</dd>
          </dl>
        </article>

        <article className="panel">
          <h2>Application Defaults</h2>
          <dl className="key-value">
            <dt>US Authorized</dt>
            <dd>{profile.application_defaults.work_authorized_us ? "Yes" : "No"}</dd>
            <dt>Sponsorship Now</dt>
            <dd>{profile.application_defaults.need_sponsorship_now ? "Yes" : "No"}</dd>
            <dt>Sponsorship Later</dt>
            <dd>{profile.application_defaults.need_sponsorship_future ? "Yes" : "No"}</dd>
            <dt>Relocate</dt>
            <dd>{profile.application_defaults.willing_to_relocate ? "Yes" : "No"}</dd>
          </dl>
          <p className="subtle">
            Preferred locations: {profile.application_defaults.preferred_locations.join(", ")}
          </p>
        </article>

        <article className="panel">
          <h2>Question Policy</h2>
          <ul className="list">
            <li>Work authorization answers: {String(profile.question_policy.answer_work_authorization)}</li>
            <li>Sponsorship answers: {String(profile.question_policy.answer_sponsorship)}</li>
            <li>Relocation answers: {String(profile.question_policy.answer_relocation)}</li>
            <li>Salary expectations: {profile.question_policy.answer_salary_expectation}</li>
            <li>Demographic questions: {profile.question_policy.answer_demographic_questions}</li>
            <li>Never lie: {String(profile.question_policy.never_lie)}</li>
          </ul>
        </article>

        <article className="panel">
          <h2>Writing Style</h2>
          <p className="subtle">{profile.writing_style.tone}</p>
          <ul className="list">
            {profile.writing_style.avoid.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      </section>
    </div>
  );
}
