# CareerAgent

CareerAgent is a customizable, human-in-the-loop job-search and application assistant.

It is designed to help users:

- find relevant jobs
- verify whether jobs are still open
- score jobs by fit and availability
- generate tailored application packets
- track applications and outcomes
- eventually assist with browser autofill in Chromium

CareerAgent must never submit applications automatically.

The user must always review and manually submit every application.

## Current Stage

**Stage 1 — Project Skeleton, Database, Basic UI, README, and Future Roadmap**

Status: Current

Goal: create the full foundation with Next.js, FastAPI, PostgreSQL, Docker, safe public profile and resume templates, private local profile and resume files, placeholder services, and basic pages that later stages can extend cleanly.

## Core Safety Principles

- CareerAgent is human-in-the-loop by design.
- CareerAgent may assist with research, drafting, verification, and later safe autofill.
- CareerAgent must never auto-submit an application.
- CareerAgent must never click final submit, apply, confirm, finalize, or equivalent end-state actions.
- The user always manually reviews and manually submits.
- CareerAgent should never invent experience, achievements, credentials, or answers.

## Tech Stack

- Frontend: Next.js
- Backend: FastAPI
- Database: PostgreSQL
- Local development: Docker Compose
- Browser automation later: Playwright
- Resume generation later: LaTeX
- AI integration later: placeholder/mock provider first, OpenAI later

## How To Run Locally

1. Copy `.env.example` to `.env` and fill in any local settings or API keys there:

```bash
cp .env.example .env
```

2. Copy the safe public profile template to your private local profile file:

```bash
cp data/profile.example.yaml data/profile.yaml
```

3. Copy the safe public resume template to your private local resume file:

```bash
cp data/resume/base_resume.example.tex data/resume/base_resume.tex
```

4. Start the stack:

```bash
docker compose up --build
```

If you skip the profile or resume copy step, the app falls back to the committed example templates so the skeleton still starts cleanly.

5. Open:

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend: [http://localhost:8000](http://localhost:8000)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

## Public GitHub Safety

- Real profile info belongs in `data/profile.yaml`, which is gitignored.
- Real resume content belongs in `data/resume/base_resume.tex`, which is gitignored.
- API keys, tokens, and local secrets belong in `.env`, which is gitignored.
- Only `.env.example`, `data/profile.example.yaml`, and `data/resume/base_resume.example.tex` should be committed as templates.
- Generated application packets, tailored resumes, cover letters, recruiter messages, and other outputs are private and ignored under `outputs/`.
- The app should never log secrets or print full personal profile information unnecessarily.

If private files were already tracked before these ignore rules were added, remove them from Git tracking first:

```bash
git rm --cached data/profile.yaml
git rm --cached data/resume/base_resume.tex
git rm --cached -r outputs/
```

Then commit the `.gitignore` update before pushing.

## Pre-Commit Safety Ideas

- Consider adding `git-secrets` to block obvious secret patterns before commits.
- Consider adding `detect-secrets` to scan for keys, tokens, and other sensitive values.
- Consider adding lightweight `pre-commit` hooks for secret scanning and file-pattern checks.
- This repo does not add that tooling yet, but it is a good next safety step before active development and public pushes.

## Before You Push

Before pushing to GitHub, run:

```bash
git status
git diff --cached
git ls-files | grep -E "profile.yaml|base_resume.tex|.env|outputs|application_packets|.pdf"
```

Make sure no private files are tracked in the output. If the last command prints nothing, that is the safest result.

## What Stage 1 Implements

- A Docker Compose stack for PostgreSQL, FastAPI, and Next.js.
- Environment configuration via `.env.example`.
- FastAPI routes for:
  - `/health`
  - `/api/profile`
  - `/api/jobs`
  - `/api/tracker`
  - `/api/packets`
  - `/api/market`
  - `/api/autofill`
- SQLAlchemy models for jobs, application events, and application packets.
- Startup table creation with `Base.metadata.create_all(...)`.
- Seeded sample jobs for validating the UI and data model.
- Read-only loading of `data/profile.yaml` with fallback to `data/profile.example.yaml`.
- A safe public base LaTeX resume template at `data/resume/base_resume.example.tex`, with `data/resume/base_resume.tex` reserved for the private local copy.
- Placeholder service modules for parsing, verification, scoring, packet generation, market analytics, and browser autofill.
- A basic Next.js UI with pages for Home, Profile, Jobs, Tracker, Packets, Market, and Autofill.

## Application Workflow

1. Maintain a truthful private local profile and base resume.
2. Import or discover jobs.
3. Parse jobs into structured data.
4. Verify that jobs appear open and estimate whether they may be stale or closed.
5. Score jobs by fit, freshness, availability, location, and application ease.
6. Generate a reviewable application packet for a chosen job.
7. Track actions, progress, and outcomes.
8. Optionally assist with safe browser autofill in a later stage.
9. Stop before final submission so the user can review and submit manually.

## Project Structure

```text
careeragent/
  README.md
  docker-compose.yml
  .env.example
  .gitignore
  backend/
    Dockerfile
    requirements.txt
    main.py
    app/
      api/routes/
      core/
      db/
      models/
      schemas/
      services/
      utils/
  frontend/
    Dockerfile
    package.json
    next.config.js
    tsconfig.json
    next-env.d.ts
    app/
    components/
    lib/
  data/
    profile.example.yaml
    profile.yaml              # local only, gitignored
    resume/
      base_resume.example.tex
      base_resume.tex         # local only, gitignored
  outputs/                    # local only, gitignored
    application_packets/
```

## Backend Endpoints In Stage 1

- `GET /health`
  Returns a simple backend health payload.
- `GET /api/profile`
  Loads profile data from `data/profile.yaml` first and falls back to `data/profile.example.yaml`.
- `GET /api/jobs`
  Returns seeded sample jobs from PostgreSQL.
- `GET /api/tracker`
  Returns a tracker placeholder payload.
- `GET /api/packets`
  Returns a packet-generation placeholder payload.
- `GET /api/market/summary`
  Returns placeholder market summary statistics.
- `GET /api/autofill/status`
  Returns the planned autofill status and explicitly states that final submission will never be automated.

## Stage Roadmap

### Stage 1: Project Skeleton, Database, Basic UI, README, and Future Roadmap

- Status: Current
- Goal: create full foundation with Next.js, FastAPI, PostgreSQL, Docker, safe example templates, private local profile and resume files, placeholder services, and basic pages.

### Stage 2: Profile + LaTeX Resume System

- Load and edit `profile.yaml` from UI.
- Add `base_resume.tex` management.
- Generate `tailored_resume.tex`.
- Compile `tailored_resume.pdf` using LaTeX.
- Preserve formatting.
- Never invent experience.

### Stage 3: Job Import + Job Parsing

- Paste job URL or description.
- Parse title, company, location, requirements, responsibilities, skills, experience level, and source.
- Save imported jobs to database.

### Stage 4: Job Verification + Likely Closed Scoring

- Check if job page loads.
- Detect apply button.
- Detect closed-job phrases.
- Track posted date, first seen, last seen, last checked, closed date.
- Estimate `likely_closed_score`.
- Include availability in priority scoring.

### Stage 5: Match Scoring + Priority Ranking

- Compare resume/profile to job description.
- Score skill match, role match, location match, freshness, verification, and application ease.
- Rank jobs by overall priority.
- Note in README that scoring should improve with real outcome data.

### Stage 6: Application Packet Generation

- Create per-job output folders.
- Generate tailored resume, cover letter, recruiter message, application questions, notes, and change summary.
- Write in user’s direct/simple style.
- Do not exaggerate or invent details.

### Stage 7: Tracker + Action Logging

- Track saved jobs, verified jobs, packet-ready jobs, application link opened, autofill started, autofill completed, manually applied, interview, rejected, offer, follow-up.
- Track clicks and timestamps.

### Stage 8: Browser Autofill with Playwright

- Launch headed Chromium.
- Detect common application fields.
- Fill high-confidence factual fields.
- Draft/fill common questions when safe.
- Prefer not to answer demographic questions by default.
- Never click submit/apply/final confirmation buttons.

### Stage 9: Market Analytics Dashboard

- Show jobs by week, role, company, location, source, skills, verification status, and response rate.
- Track which jobs close fastest.
- Prepare data for future prediction.

### Stage 10: AI Provider Integration

- Add provider pattern:
  - `MockProvider`
  - `OpenAIProvider`
  - `LocalLLMProvider`
- Use AI for job parsing, resume tailoring, cover letters, and application question drafts.
- Keep outputs reviewable.

### Stage 11: Prediction and Improvements

- Predict best times to apply.
- Predict likely-closed postings.
- Improve priority scoring from application outcomes.
- Improve source quality scoring.
- Add better market trend models.

## Planned Improvements

- Improve priority scoring with real outcome data.
- Add stronger job availability prediction.
- Add market trend models for best times to apply.
- Add more ATS integrations.
- Improve LaTeX resume editing while preserving formatting.
- Improve custom application question answering.
- Add browser autofill support for more job boards.
- Add email/recruiter outreach tracking.
- Add calendar reminders for follow-ups.
- Add dashboard for response rates by role, company, and source.

## Notes For Future Stages

- The Stage 1 backend uses placeholder services intentionally so the structure is stable before deeper logic is added.
- The frontend already consumes backend endpoints, which keeps future API work incremental instead of requiring a UI rewrite.
- Browser automation must remain bounded by safety checks and blocked final-action detection.
- Resume tailoring must preserve the base resume structure and stay faithful to verified user history.
