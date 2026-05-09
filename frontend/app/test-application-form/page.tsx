"use client";

export default function TestApplicationFormPage() {
  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Local Autofill Test</span>
        <h1>CareerAgent Test Application Form</h1>
        <p className="hero-copy">
          This is a fake local test form for CareerAgent autofill testing. Do not enter real sensitive information.
        </p>
      </section>

      <section className="panel">
        <form
          className="stack"
          onSubmit={(event) => {
            event.preventDefault();
          }}
        >
          <div className="panel-grid">
            <label className="field-group">
              <span>First Name</span>
              <input className="input" name="first_name" autoComplete="given-name" />
            </label>
            <label className="field-group">
              <span>Last Name</span>
              <input className="input" name="last_name" autoComplete="family-name" />
            </label>
            <label className="field-group">
              <span>Full Name</span>
              <input className="input" name="full_name" autoComplete="name" />
            </label>
            <label className="field-group">
              <span>Email</span>
              <input className="input" name="email" type="email" autoComplete="email" />
            </label>
            <label className="field-group">
              <span>Phone</span>
              <input className="input" name="phone" type="tel" autoComplete="tel" />
            </label>
            <label className="field-group">
              <span>City</span>
              <input className="input" name="city" autoComplete="address-level2" />
            </label>
            <label className="field-group">
              <span>State</span>
              <input className="input" name="state" autoComplete="address-level1" />
            </label>
            <label className="field-group">
              <span>Zip</span>
              <input className="input" name="zip" autoComplete="postal-code" />
            </label>
            <label className="field-group">
              <span>Country</span>
              <input className="input" name="country" autoComplete="country-name" />
            </label>
            <label className="field-group">
              <span>LinkedIn</span>
              <input className="input" name="linkedin" type="url" />
            </label>
            <label className="field-group">
              <span>GitHub</span>
              <input className="input" name="github" type="url" />
            </label>
            <label className="field-group">
              <span>Portfolio</span>
              <input className="input" name="portfolio" type="url" />
            </label>
            <label className="field-group">
              <span>School</span>
              <input className="input" name="school" />
            </label>
            <label className="field-group">
              <span>Degree</span>
              <input className="input" name="degree" />
            </label>
            <label className="field-group">
              <span>Graduation Date</span>
              <input className="input" name="graduation_date" placeholder="May 2026" />
            </label>
            <label className="field-group">
              <span>Expected salary</span>
              <input className="input" name="salary_expectation" />
            </label>
          </div>

          <div className="panel-grid">
            <label className="field-group">
              <span>Are you authorized to work in the United States?</span>
              <select className="input" name="work_authorized_us">
                <option value="">Select</option>
                <option>Yes</option>
                <option>No</option>
              </select>
            </label>
            <label className="field-group">
              <span>Do you require sponsorship now or in the future?</span>
              <select className="input" name="need_sponsorship_future">
                <option value="">Select</option>
                <option>Yes</option>
                <option>No</option>
              </select>
            </label>
            <label className="field-group">
              <span>Are you willing to relocate?</span>
              <select className="input" name="willing_to_relocate">
                <option value="">Select</option>
                <option>Yes</option>
                <option>No</option>
              </select>
            </label>
          </div>

          <label className="field-group">
            <span>Why are you interested in this company?</span>
            <textarea className="input" name="why_company" rows={4} />
          </label>
          <label className="field-group">
            <span>Tell us about yourself</span>
            <textarea className="input" name="tell_us_about_yourself" rows={4} />
          </label>

          <div className="panel-grid">
            <label className="field-group">
              <span>Resume upload</span>
              <input className="input" name="resume_upload" type="file" accept=".pdf" />
            </label>
            <label className="field-group">
              <span>Cover letter upload</span>
              <input className="input" name="cover_letter_upload" type="file" accept=".pdf" />
            </label>
          </div>

          <section className="warning-panel">
            <h2>Optional EEO Fields</h2>
            <p>These fake fields exist only to confirm CareerAgent skips sensitive optional questions by default.</p>
            <div className="panel-grid">
              <label className="field-group">
                <span>Race/Ethnicity</span>
                <select className="input" name="race_ethnicity">
                  <option value="">Select</option>
                  <option>Prefer not to answer</option>
                  <option>Decline to self-identify</option>
                </select>
              </label>
              <label className="field-group">
                <span>Gender</span>
                <select className="input" name="gender">
                  <option value="">Select</option>
                  <option>Prefer not to answer</option>
                  <option>Decline to self-identify</option>
                </select>
              </label>
              <label className="field-group">
                <span>Veteran Status</span>
                <select className="input" name="veteran_status">
                  <option value="">Select</option>
                  <option>Prefer not to answer</option>
                  <option>Decline to self-identify</option>
                </select>
              </label>
              <label className="field-group">
                <span>Disability Status</span>
                <select className="input" name="disability_status">
                  <option value="">Select</option>
                  <option>Prefer not to answer</option>
                  <option>Decline to self-identify</option>
                </select>
              </label>
            </div>
          </section>

          <section className="warning-panel">
            <h2>Dangerous Fields</h2>
            <p>CareerAgent should detect these and skip them.</p>
            <div className="panel-grid">
              <label className="field-group">
                <span>SSN</span>
                <input className="input" name="ssn" />
              </label>
              <label className="field-group">
                <span>Date of Birth</span>
                <input className="input" name="date_of_birth" placeholder="YYYY-MM-DD" />
              </label>
            </div>
          </section>

          <div className="button-row">
            <button className="button" type="submit">
              Submit Application
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
