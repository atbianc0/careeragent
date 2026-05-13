"use client";

export default function LeverRdTestFormPage() {
  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow">Local Lever-Style Test</span>
        <h1>Baseball Operations R&amp;D Intern</h1>
        <p className="hero-copy">San Francisco Giants style application form for safe CareerAgent autofill testing.</p>
      </section>

      <section className="panel">
        <form
          className="stack posting-form"
          onSubmit={(event) => {
            event.preventDefault();
          }}
        >
          <section className="subtle-panel stack">
            <h2>Resume/CV</h2>
            <label className="field-group posting-form-question">
              <span>Resume/CV *</span>
              <input className="input" name="resume" type="file" accept=".pdf" required />
            </label>
          </section>

          <section className="subtle-panel stack">
            <h2>Contact Information</h2>
            <div className="panel-grid">
              <label className="field-group posting-form-question">
                <span>Full name *</span>
                <input className="input" name="name" autoComplete="name" required />
              </label>
              <label className="field-group posting-form-question">
                <span>Pronouns</span>
                <select className="input" name="pronouns">
                  <option value="">Select</option>
                  <option>He/him</option>
                  <option>She/her</option>
                  <option>They/them</option>
                  <option>Prefer not to say</option>
                </select>
              </label>
              <label className="field-group posting-form-question">
                <span>Email *</span>
                <input className="input" name="email" type="email" autoComplete="email" required />
              </label>
              <label className="field-group posting-form-question">
                <span>Phone *</span>
                <input className="input" name="phone" type="tel" autoComplete="tel" required />
              </label>
              <label className="field-group posting-form-question">
                <span>Current location *</span>
                <input className="input" name="location" placeholder="City, State" required />
              </label>
              <label className="field-group posting-form-question">
                <span>Current company</span>
                <input className="input" name="current_company" />
              </label>
              <label className="field-group posting-form-question">
                <span>LinkedIn URL</span>
                <input className="input" name="linkedin" type="url" />
              </label>
            </div>
          </section>

          <section className="subtle-panel stack">
            <h2>R&amp;D Intern Questions</h2>
            <label className="field-group posting-form-question">
              <span>
                1. Your draft model gives your first-round draft pick a 30% chance of being an &quot;A-grade&quot; hitter. He is sent
                to low-A to begin his pro career. You know that in low-A, future A-grade hitters average a 10% xBH rate,
                while the rest of the population averages an 8% xBH rate. A scout observes his first game of pro ball,
                where he goes 3-for-4 with a single, a double, and a HR. Based on his first game, how would you update his
                chances of being an A-grade hitter? Show your work and comment on the sensitivity of your calculation to
                the given xBH rates.
              </span>
              <textarea className="input" name="question_1_bayesian_xbh" rows={6} required />
            </label>
            <label className="field-group posting-form-question">
              <span>
                2a. A pitcher has thrown N + 0.1 innings so far this year, where N is a whole number, and his ERA is
                between 3 and 4. What is the minimum value of N such that there are exactly four possible values of ERA?
                Please provide an argument for your answer.
              </span>
              <textarea className="input" name="question_2a_era_values" rows={5} required />
            </label>
            <label className="field-group posting-form-question">
              <span>
                2b. What is the smallest value N such that for all M &ge; N there are at least four possible values of ERA?
                Please provide an argument for your answer.
              </span>
              <textarea className="input" name="question_2b_era_smallest_n" rows={5} required />
            </label>
            <label className="field-group posting-form-question">
              <span>
                3a. A hitter has a mid-season stat line with 312 PA, .286 avg, 3 hr, .350 babip, and 55% groundball rate.
                Based on this stat line, what can you infer about this hitter? What are you confident in or not confident in?
              </span>
              <textarea className="input" name="question_3a_hitter_inference" rows={5} required />
            </label>
            <label className="field-group posting-form-question">
              <span>
                3b. Now consider the same stat line, but instead of a 55% groundball rate, the hitter has a 55% flyball
                rate. How does this change your inferences? How do you feel about the sustainability of this performance?
              </span>
              <textarea className="input" name="question_3b_flyball_rate" rows={5} required />
            </label>
          </section>

          <section className="warning-panel stack">
            <h2>Voluntary EEO</h2>
            <div className="panel-grid">
              <label className="field-group posting-form-question">
                <span>Gender</span>
                <select className="input" name="gender">
                  <option value="">Select</option>
                  <option>Prefer not to answer</option>
                  <option>Woman</option>
                  <option>Man</option>
                  <option>Non-binary</option>
                </select>
              </label>
              <label className="field-group posting-form-question">
                <span>Race</span>
                <select className="input" name="race">
                  <option value="">Select</option>
                  <option>Prefer not to answer</option>
                  <option>Decline to self-identify</option>
                </select>
              </label>
              <label className="field-group posting-form-question">
                <span>Veteran status</span>
                <select className="input" name="veteran_status">
                  <option value="">Select</option>
                  <option>Prefer not to answer</option>
                  <option>I am not a protected veteran</option>
                </select>
              </label>
            </div>
          </section>

          <label className="checkbox-row posting-form-question">
            <input type="checkbox" name="future_opportunities" />
            Contact me about future job opportunities.
          </label>

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
