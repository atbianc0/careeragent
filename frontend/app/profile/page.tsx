import { ProfileEditor } from "@/components/ProfileEditor";

export default function ProfilePage() {
  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Stage 2 - Profile System</span>
        <h1>Profile</h1>
        <p className="hero-copy">
          Edit the job-search profile used by CareerAgent. The app loads the private local YAML
          file when present and falls back to the safe public example template otherwise.
        </p>
      </section>

      <ProfileEditor />
    </div>
  );
}
