"use client";

import { useEffect, useState } from "react";

import {
  type ProfileData,
  type ProfileDocument,
  type ProfileStatus,
  createPrivateProfile,
  getProfile,
  getProfileStatus,
  saveProfile
} from "@/lib/api";

function toLines(values: string[]) {
  return values.join("\n");
}

function fromLines(value: string) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

const emptyProfile: ProfileData = {
  personal: { name: "", email: "", phone: "", location: "" },
  education: { school: "", degree: "", graduation: "" },
  links: { linkedin: "", github: "", portfolio: "" },
  target_roles: [],
  skills: [],
  application_defaults: {
    work_authorized_us: false,
    need_sponsorship_now: false,
    need_sponsorship_future: false,
    willing_to_relocate: false,
    preferred_locations: []
  },
  question_policy: {
    answer_work_authorization: false,
    answer_sponsorship: false,
    answer_relocation: false,
    answer_salary_expectation: "",
    answer_demographic_questions: "",
    never_lie: true
  },
  writing_style: {
    tone: "",
    avoid: []
  }
};

export function ProfileEditor() {
  const [profile, setProfile] = useState<ProfileData>(emptyProfile);
  const [documentInfo, setDocumentInfo] = useState<ProfileDocument | null>(null);
  const [status, setStatus] = useState<ProfileStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);

    try {
      const [profileResponse, statusResponse] = await Promise.all([getProfile(), getProfileStatus()]);
      setProfile(profileResponse.profile);
      setDocumentInfo(profileResponse);
      setStatus(statusResponse);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load profile data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleCreatePrivateProfile() {
    setSubmitting(true);
    setMessage(null);
    setError(null);

    try {
      const response = await createPrivateProfile();
      const statusResponse = await getProfileStatus();
      setProfile(response.profile);
      setDocumentInfo(response);
      setStatus(statusResponse);
      setMessage(response.message || "Private profile is ready.");
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Failed to create the private profile.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSaveProfile() {
    setSubmitting(true);
    setMessage(null);
    setError(null);

    try {
      const response = await saveProfile(profile);
      const statusResponse = await getProfileStatus();
      setProfile(response.profile);
      setDocumentInfo(response);
      setStatus(statusResponse);
      setMessage(response.message || "Saved profile successfully.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to save the profile.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <section className="panel">
        <p className="subtle">Loading profile data...</p>
      </section>
    );
  }

  return (
    <div className="page">
      <section className="panel">
        <div className="section-title">
          <h2>Profile Source</h2>
          <span className="status-tag">{documentInfo?.source || status?.active_source || "unknown"}</span>
        </div>
        <p className="subtle">
          Active file: <code>{documentInfo?.path || status?.private_profile_path || "Unavailable"}</code>
        </p>
        <p className="subtle">{status?.github_safety_note}</p>
        <ul className="list">
          <li>Example files are safe public templates.</li>
          <li>Private files are local and gitignored.</li>
          <li>Do not put API keys or secrets in profile YAML.</li>
          <li>Generated PDFs and outputs are ignored.</li>
        </ul>
        <div className="button-row">
          <button className="button secondary" type="button" onClick={handleCreatePrivateProfile} disabled={submitting}>
            Create Private Profile From Example
          </button>
          <button className="button" type="button" onClick={handleSaveProfile} disabled={submitting}>
            Save Profile
          </button>
        </div>
        {message ? <p className="message success">{message}</p> : null}
        {error ? <p className="message error">{error}</p> : null}
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>Personal</h2>
          <div className="form-grid">
            <label className="field-group">
              <span>Name</span>
              <input
                className="input"
                value={profile.personal.name}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    personal: { ...current.personal, name: event.target.value }
                  }))
                }
              />
            </label>
            <label className="field-group">
              <span>Email</span>
              <input
                className="input"
                value={profile.personal.email}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    personal: { ...current.personal, email: event.target.value }
                  }))
                }
              />
            </label>
            <label className="field-group">
              <span>Phone</span>
              <input
                className="input"
                value={profile.personal.phone}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    personal: { ...current.personal, phone: event.target.value }
                  }))
                }
              />
            </label>
            <label className="field-group">
              <span>Location</span>
              <input
                className="input"
                value={profile.personal.location}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    personal: { ...current.personal, location: event.target.value }
                  }))
                }
              />
            </label>
          </div>
        </article>

        <article className="panel">
          <h2>Education</h2>
          <div className="form-grid">
            <label className="field-group">
              <span>School</span>
              <input
                className="input"
                value={profile.education.school}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    education: { ...current.education, school: event.target.value }
                  }))
                }
              />
            </label>
            <label className="field-group">
              <span>Degree</span>
              <input
                className="input"
                value={profile.education.degree}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    education: { ...current.education, degree: event.target.value }
                  }))
                }
              />
            </label>
            <label className="field-group">
              <span>Graduation</span>
              <input
                className="input"
                value={profile.education.graduation}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    education: { ...current.education, graduation: event.target.value }
                  }))
                }
              />
            </label>
          </div>
        </article>

        <article className="panel">
          <h2>Links</h2>
          <div className="form-grid">
            <label className="field-group">
              <span>LinkedIn</span>
              <input
                className="input"
                value={profile.links.linkedin}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    links: { ...current.links, linkedin: event.target.value }
                  }))
                }
              />
            </label>
            <label className="field-group">
              <span>GitHub</span>
              <input
                className="input"
                value={profile.links.github}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    links: { ...current.links, github: event.target.value }
                  }))
                }
              />
            </label>
            <label className="field-group">
              <span>Portfolio</span>
              <input
                className="input"
                value={profile.links.portfolio}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    links: { ...current.links, portfolio: event.target.value }
                  }))
                }
              />
            </label>
          </div>
        </article>

        <article className="panel">
          <h2>Target Roles</h2>
          <label className="field-group">
            <span>One role per line</span>
            <textarea
              className="textarea"
              rows={6}
              value={toLines(profile.target_roles)}
              onChange={(event) =>
                setProfile((current) => ({
                  ...current,
                  target_roles: fromLines(event.target.value)
                }))
              }
            />
          </label>
        </article>

        <article className="panel">
          <h2>Skills</h2>
          <label className="field-group">
            <span>One skill per line</span>
            <textarea
              className="textarea"
              rows={8}
              value={toLines(profile.skills)}
              onChange={(event) =>
                setProfile((current) => ({
                  ...current,
                  skills: fromLines(event.target.value)
                }))
              }
            />
          </label>
        </article>

        <article className="panel">
          <h2>Application Defaults</h2>
          <div className="checkbox-grid">
            <label className="checkbox-row">
              <input
                checked={profile.application_defaults.work_authorized_us}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    application_defaults: {
                      ...current.application_defaults,
                      work_authorized_us: event.target.checked
                    }
                  }))
                }
                type="checkbox"
              />
              <span>Work authorized in the US</span>
            </label>
            <label className="checkbox-row">
              <input
                checked={profile.application_defaults.need_sponsorship_now}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    application_defaults: {
                      ...current.application_defaults,
                      need_sponsorship_now: event.target.checked
                    }
                  }))
                }
                type="checkbox"
              />
              <span>Need sponsorship now</span>
            </label>
            <label className="checkbox-row">
              <input
                checked={profile.application_defaults.need_sponsorship_future}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    application_defaults: {
                      ...current.application_defaults,
                      need_sponsorship_future: event.target.checked
                    }
                  }))
                }
                type="checkbox"
              />
              <span>Need sponsorship in the future</span>
            </label>
            <label className="checkbox-row">
              <input
                checked={profile.application_defaults.willing_to_relocate}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    application_defaults: {
                      ...current.application_defaults,
                      willing_to_relocate: event.target.checked
                    }
                  }))
                }
                type="checkbox"
              />
              <span>Willing to relocate</span>
            </label>
          </div>
          <label className="field-group">
            <span>Preferred locations, one per line</span>
            <textarea
              className="textarea"
              rows={5}
              value={toLines(profile.application_defaults.preferred_locations)}
              onChange={(event) =>
                setProfile((current) => ({
                  ...current,
                  application_defaults: {
                    ...current.application_defaults,
                    preferred_locations: fromLines(event.target.value)
                  }
                }))
              }
            />
          </label>
        </article>

        <article className="panel">
          <h2>Question Policy</h2>
          <div className="checkbox-grid">
            <label className="checkbox-row">
              <input
                checked={profile.question_policy.answer_work_authorization}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    question_policy: {
                      ...current.question_policy,
                      answer_work_authorization: event.target.checked
                    }
                  }))
                }
                type="checkbox"
              />
              <span>Answer work authorization</span>
            </label>
            <label className="checkbox-row">
              <input
                checked={profile.question_policy.answer_sponsorship}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    question_policy: {
                      ...current.question_policy,
                      answer_sponsorship: event.target.checked
                    }
                  }))
                }
                type="checkbox"
              />
              <span>Answer sponsorship questions</span>
            </label>
            <label className="checkbox-row">
              <input
                checked={profile.question_policy.answer_relocation}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    question_policy: {
                      ...current.question_policy,
                      answer_relocation: event.target.checked
                    }
                  }))
                }
                type="checkbox"
              />
              <span>Answer relocation questions</span>
            </label>
            <label className="checkbox-row">
              <input
                checked={profile.question_policy.never_lie}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    question_policy: {
                      ...current.question_policy,
                      never_lie: event.target.checked
                    }
                  }))
                }
                type="checkbox"
              />
              <span>Never lie</span>
            </label>
          </div>
          <div className="form-grid">
            <label className="field-group">
              <span>Salary expectation policy</span>
              <input
                className="input"
                value={profile.question_policy.answer_salary_expectation}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    question_policy: {
                      ...current.question_policy,
                      answer_salary_expectation: event.target.value
                    }
                  }))
                }
              />
            </label>
            <label className="field-group">
              <span>Demographic question policy</span>
              <input
                className="input"
                value={profile.question_policy.answer_demographic_questions}
                onChange={(event) =>
                  setProfile((current) => ({
                    ...current,
                    question_policy: {
                      ...current.question_policy,
                      answer_demographic_questions: event.target.value
                    }
                  }))
                }
              />
            </label>
          </div>
        </article>

        <article className="panel">
          <h2>Writing Style</h2>
          <label className="field-group">
            <span>Tone</span>
            <textarea
              className="textarea"
              rows={3}
              value={profile.writing_style.tone}
              onChange={(event) =>
                setProfile((current) => ({
                  ...current,
                  writing_style: { ...current.writing_style, tone: event.target.value }
                }))
              }
            />
          </label>
          <label className="field-group">
            <span>Avoid phrases, one per line</span>
            <textarea
              className="textarea"
              rows={5}
              value={toLines(profile.writing_style.avoid)}
              onChange={(event) =>
                setProfile((current) => ({
                  ...current,
                  writing_style: { ...current.writing_style, avoid: fromLines(event.target.value) }
                }))
              }
            />
          </label>
        </article>
      </section>
    </div>
  );
}

