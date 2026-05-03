# CareerAgent

CareerAgent is a customizable, human-in-the-loop job-search and application assistant.

It is designed to help users:

- find relevant jobs
- verify whether jobs are still open
- score jobs by fit and availability
- generate tailored application packets
- track applications and outcomes
- eventually assist with browser autofill in Chromium

CareerAgent must never auto-submit job applications.

CareerAgent must never click final submit, apply, confirm, or equivalent end-state buttons.

CareerAgent must never invent experience, skills, credentials, companies, dates, results, education, or work authorization details.

## Current Stage

**Stage 6 — Application Packet Generation**

- Stage 1: Complete
- Stage 2: Complete
- Stage 3: Complete
- Stage 4: Complete
- Stage 5: Complete
- Stage 6: Complete

Next Stage: **Stage 7 — Tracker + Action Logging**

Stage 6 adds real per-job packet generation, packet records in PostgreSQL, packet detail pages in the frontend, conservative LaTeX resume tailoring, and graceful optional PDF compilation when a LaTeX compiler is available.

## Stage 6 Features

- Generate a private per-job packet folder under `outputs/application_packets/`.
- Generate `tailored_resume.tex` by minimally editing the source LaTeX resume while preserving structure and style.
- Attempt `tailored_resume.pdf` compilation when `xelatex` or `pdflatex` is available.
- Generate `cover_letter.md`.
- Generate `recruiter_message.md`.
- Generate `application_questions.md`.
- Generate `application_notes.md`.
- Generate `change_summary.md`.
- Generate `job_summary.json`.
- Generate `packet_metadata.json`.
- Save packet records in PostgreSQL with generation status, timestamps, file paths, and graceful error details.
- Show packets in the frontend on `/packets`, `/packets/{id}`, and the job detail page.
- Keep Stage 1 through Stage 5 features intact, including profile editing, resume editing, import, verification, scoring, and ranked recommendations.
- Keep generated outputs private and gitignored.

## Core Safety Principles

- CareerAgent is human-in-the-loop by design.
- CareerAgent may assist with research, drafting, verification, and safe autofill preparation.
- CareerAgent must never auto-submit an application.
- CareerAgent must never click final submit, apply, confirm, finalize, or equivalent completion actions.
- The user always manually reviews and manually submits.
- CareerAgent should never invent experience, achievements, credentials, or answers.
- The app should never log secrets or print full personal profile information unnecessarily.

## Target Agent Workflow

CareerAgent is being built toward a custom AI agent workflow, not just a set of separate tools. The intended end-to-end flow is:

1. The user uploads or creates their profile, resume, preferences, links, and application defaults once.
2. CareerAgent finds or imports relevant jobs.
3. CareerAgent verifies whether jobs are still hiring.
4. CareerAgent scores jobs by fit, freshness, availability, and application priority.
5. CareerAgent recommends the best jobs to apply to first.
6. The user reviews a recommended job.
7. CareerAgent generates a tailored application packet while preserving the user’s original resume structure and style.
8. The user clicks an autofill or apply-assist action.
9. CareerAgent opens the application page in Chromium, fills safe fields, uploads the correct files, drafts answers in the user’s writing style, and stops before final submission.
10. The user manually reviews and submits.
11. CareerAgent tracks the application and follow-up status.

At the end of this Stage 6 pass, setup, import, parsing, saved-job persistence, rule-based verification, rule-based scoring, and packet generation are implemented. Browser autofill and full tracker logging are still future stages.

## Tech Stack

- Frontend: Next.js
- Backend: FastAPI
- Database: PostgreSQL
- Local development: Docker Compose
- Browser automation later: Playwright
- Resume generation: LaTeX
- AI integration later: placeholder/mock provider first, OpenAI later

## How To Run Locally

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Optional: if you want demo/sample jobs in an empty local database, set this in `.env`:

```bash
ENABLE_SAMPLE_JOBS=true
```

3. Copy the safe public profile template to your private local profile file:

```bash
cp data/profile.example.yaml data/profile.yaml
```

4. Copy the safe public resume template to your private local resume file:

```bash
cp data/resume/base_resume.example.tex data/resume/base_resume.tex
```

5. Start the stack:

```bash
docker compose up --build
```

6. Open:

- Frontend: [http://localhost:3000](http://localhost:3000)
- Profile page: [http://localhost:3000/profile](http://localhost:3000/profile)
- Resume page: [http://localhost:3000/resume](http://localhost:3000/resume)
- Backend: [http://localhost:8000](http://localhost:8000)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

If `data/profile.yaml` or `data/resume/base_resume.tex` do not exist yet, the app still starts and falls back to the committed example files.

If LaTeX is not installed, the resume compile endpoint stays available and returns a clear message instead of crashing the backend.

If you are upgrading from an older local database, CareerAgent adds the Stage 3 through Stage 6 job and packet columns automatically on startup. If you want a clean local reset instead, run:

```bash
docker compose down -v
docker compose up --build
```

## Public GitHub Safety

- Real profile info should go in `data/profile.yaml`, which is gitignored.
- Real resume content should go in `data/resume/base_resume.tex`, which is gitignored.
- API keys, tokens, and secrets should go in `.env`, which is gitignored.
- Generated application packets and generated PDFs are private and ignored under `outputs/`.
- Allowed committed template files:
  - `.env.example`
  - `data/profile.example.yaml`
  - `data/resume/base_resume.example.tex`
- Never commit:
  - `.env`
  - `data/profile.yaml`
  - `data/resume/base_resume.tex`
  - `outputs/`
  - generated PDFs
  - generated application packets
  - API keys or tokens
  - real personal resume/profile data
- The app should never require private local files to be committed in order to run.

Helpful setup commands:

```bash
cp data/profile.example.yaml data/profile.yaml
cp data/resume/base_resume.example.tex data/resume/base_resume.tex
cp .env.example .env
```

If private files were already tracked before these ignore rules were added, remove them from Git tracking first:

```bash
git rm --cached .env
git rm --cached data/profile.yaml
git rm --cached data/resume/base_resume.tex
git rm --cached -r outputs/
```

Then commit the `.gitignore` update before pushing.

Before pushing to GitHub, run:

```bash
git status
git diff --cached --name-only
git ls-files | grep -E "profile.yaml|base_resume.tex|.env|outputs|application_packets|.pdf"
```

Only the example/template files should appear as tracked private-data matches. If this command also shows `frontend/next-env.d.ts`, that is the standard Next.js type shim and not a secret file. Private local files and generated outputs should not be tracked.

## Pre-Commit Safety Ideas

- Use `git-secrets` to block common secret patterns before commits.
- Use `detect-secrets` to scan for keys, tokens, and other sensitive values.
- Use lightweight `pre-commit` hooks to automate secret scans and path checks.
- This repo does not add heavy safety tooling yet, but those tools are good next steps before regular public pushes.

## Stage 2 Usage

### Profile workflow

1. Open `/profile`.
2. The page shows whether the active file is the private profile or the example fallback.
3. Use `Create Private Profile From Example` if `data/profile.yaml` does not exist yet.
4. Edit fields and save them.
5. The backend writes changes to `data/profile.yaml` only.

### Resume workflow

1. Open `/resume`.
2. The page shows whether the active file is the private resume or the example fallback.
3. Use `Create Private Resume From Example` if `data/resume/base_resume.tex` does not exist yet.
4. Edit the LaTeX source and save it.
5. Use `Compile PDF` to generate a PDF when `xelatex` or `pdflatex` is available.
6. Compiled PDFs are written under `outputs/resume/`, which is gitignored.

## Resume Safety

CareerAgent should preserve the user’s original LaTeX resume structure, section order, commands, formatting, spacing, fonts, margins, and visual style. Tailoring should be content-only unless the user explicitly asks for design changes. Tailored resumes should be made by minimally editing `base_resume.tex`, not by replacing it with a new template.

## Stage 3, Stage 4, Stage 5, and Stage 6 Usage

### Job import workflow

1. Open `/jobs`.
2. Choose `Paste Job Description` or `Paste Job URL`.
3. Paste the content and keep the source as `manual` or change it if needed.
4. Click `Preview Parse`.
5. Review the parsed fields.
6. Click `Import and Save`.
7. Open the saved job detail page.
8. Restart the app later and your saved jobs will still be in PostgreSQL.

### Verification workflow

1. Open `/jobs`.
2. Import a job first or use an existing saved job with a real URL.
3. Click `Verify` on a single row or `Verify All Jobs`.
4. Review the saved `verification_status`, `verification_score`, `likely_closed_score`, and evidence.
5. Treat `open` and `probably_open` as stronger candidates, and treat `unknown`, `possibly_closed`, `likely_closed`, and `closed` as needing manual review.
6. Open the job detail page to inspect verification evidence and raw verification details.

### Scoring workflow

1. Make sure profile and resume data exist locally, or let CareerAgent fall back to the committed example files.
2. Import jobs and verify them first when URLs are available.
3. Click `Score` on a single row or `Score All Jobs`.
4. Review `resume_match_score`, `overall_priority_score`, and the scoring evidence on the Jobs page.
5. Open the job detail page to inspect matched skills, missing skills, role fit evidence, location evidence, and freshness evidence.
6. Use the `Recommended Jobs` section on `/jobs` to decide which verified jobs should move into packet generation next.

### Stage 6 packet workflow

1. Make sure profile and resume data exist locally, or let CareerAgent fall back to the committed example files.
2. Import at least one job.
3. Verify the job when a URL is available.
4. Score the job.
5. Open the job detail page.
6. Click `Generate Application Packet`.
7. Review the generated packet summary on the job detail page.
8. Open `/packets` to view the full packet list.
9. Open `/packets/{id}` to preview the generated files.
10. Manually review and use the packet when applying.

### Stage 6 limitations

- URL parsing is basic and may not work on JavaScript-heavy job pages.
- Verification is rule-based and approximate.
- Scoring is also rule-based and approximate.
- Stage 6 generation is deterministic/mock unless an optional AI provider is added later.
- Tailored resume edits are intentionally conservative to preserve structure and avoid invented claims.
- Cover letter and recruiter message drafts may still need meaningful editing.
- Packet generation does not submit applications and does not autofill browser forms.
- PDF compilation depends on local or container LaTeX availability.
- If LaTeX is unavailable, packet generation still succeeds and stores the `.tex` source with a graceful warning.
- User review is required before trusting or using any generated content.
- Scoring does not use AI yet.
- Scoring may miss skills or context that are not obvious in the parsed text or base resume text.
- Scores do not guarantee interview chances or application outcomes.
- Some job boards block requests or expose too little text for a confident check.
- Browser-based extraction and browser-based verification may be added later.
- A job can look open while still being closed behind a login wall or deeper ATS flow.
- User review is still required before trusting any recommendation or generated packet asset.
- AI-assisted parsing is Stage 10.
- Some parsed, verified, and scored fields will be imperfect because CareerAgent currently uses deterministic rule-based parsing, verification, and scoring instead of AI or browser automation.

## What Works In Stage 6

- `GET /health`
- `GET /api/market/summary`
- `GET /api/autofill/status`
- `GET /api/profile`
- `PUT /api/profile`
- `POST /api/profile/create-private`
- `GET /api/profile/status`
- `GET /api/resume`
- `PUT /api/resume`
- `POST /api/resume/create-private`
- `POST /api/resume/compile`
- `GET /api/resume/status`
- `GET /api/jobs`
- `POST /api/jobs/parse`
- `POST /api/jobs/import`
- `POST /api/jobs/verify-url`
- `POST /api/jobs/verify-all`
- `POST /api/jobs/score-all`
- `GET /api/jobs/recommendations`
- `GET /api/jobs/{id}`
- `GET /api/jobs/{id}/score`
- `GET /api/jobs/{id}/verification`
- `POST /api/jobs/{id}/score`
- `POST /api/jobs/{id}/verify`
- `PUT /api/jobs/{id}`
- `DELETE /api/jobs/{id}`
- `GET /api/packets`
- `POST /api/packets/generate`
- `GET /api/packets/{id}`
- `GET /api/packets/job/{job_id}`
- `GET /api/packets/{id}/file?file_key=cover_letter`
- `GET /api/packets/{id}/file?file_key=recruiter_message`
- `GET /api/packets/{id}/file?file_key=application_questions`
- `GET /api/packets/{id}/file?file_key=application_notes`
- `GET /api/packets/{id}/file?file_key=change_summary`
- `GET /api/packets/{id}/file?file_key=tailored_resume_tex`
- `GET /api/packets/{id}/file?file_key=job_summary`
- `GET /api/packets/{id}/file?file_key=packet_metadata`
- Real Stage 6 pages for jobs, packets, and packet detail

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
    resume/
```

## Stage Roadmap

### Stage 1: Project Skeleton, Database, Basic UI, README, and Future Roadmap

- Status: Complete
- Goal: create the full foundation with Next.js, FastAPI, PostgreSQL, Docker, public-safe templates, private local file paths, placeholder services, and basic pages.

### Stage 2: Profile + LaTeX Resume System

- Status: Complete
- Load profile data from YAML.
- Edit profile data from the UI.
- Save profile changes to `data/profile.yaml`.
- Load private resume data from `data/resume/base_resume.tex`.
- Edit resume LaTeX source from the UI.
- Save resume changes to `data/resume/base_resume.tex`.
- Optionally compile the base resume into a PDF when a LaTeX compiler is installed.
- Keep private files local and GitHub-safe.
- Never invent experience.

### Stage 3: Job Import + Job Parsing

- Status: Complete
- Paste job URL or description.
- Parse title, company, location, requirements, responsibilities, skills, experience level, and source.
- Save imported jobs to database.
- Import jobs from pasted descriptions.
- Import jobs from pasted URLs.
- Use rule-based parsing for title, company, location, skills, salary, seniority, remote status, responsibilities, requirements, and application questions.
- View saved jobs in the Jobs page.
- View detailed job records.
- Prepare parsed job records for Stage 4 verification and Stage 5 scoring.

### Stage 4: Job Verification + Likely Closed Scoring

- Status: Complete
- Check if job page loads.
- Detect apply button.
- Detect closed-job phrases.
- Track posted date, first seen, last seen, last checked, closed date.
- Estimate `likely_closed_score`.
- Include availability in priority scoring.

### Stage 5: Match Scoring + Priority Ranking

- Status: Complete
- Compare resume/profile to job description.
- Score skill match, role match, location match, freshness, verification, and application ease.
- Score one job or all saved jobs against the current profile and base resume.
- Store scoring evidence and scoring raw data.
- Rank jobs by overall priority.
- Show recommended jobs ranked by rule-based priority.
- Improve scoring over time with real outcome data.

### Stage 6: Application Packet Generation

- Status: Complete
- Create per-job output folders.
- Generate `tailored_resume.tex`, `job_summary.json`, `packet_metadata.json`, `cover_letter.md`, `recruiter_message.md`, `application_questions.md`, `application_notes.md`, and `change_summary.md`.
- Attempt tailored resume PDF compilation when LaTeX is available.
- Save packet records in PostgreSQL.
- Show packet details in the frontend.
- Preserve the user’s original resume structure and style.
- Keep outputs private and gitignored.

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

## Next Stage

**Next Stage: Stage 7 — Tracker + Action Logging**

Stage 7 should:

- record manual application actions and timestamps
- track packet-ready, applied, interview, follow-up, rejection, and offer states
- make it easy to mark a job as manually applied after the user submits it themselves
- add basic follow-up reminders and action history
- preserve the no-auto-submit safety boundary

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
