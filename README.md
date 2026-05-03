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

**Stage 2 — Profile + LaTeX Resume System**

- Stage 1: Complete
- Stage 2: Complete after this audit

Stage 2 adds editable YAML profile management, editable LaTeX resume management, safe private-file creation from committed examples, and optional PDF compilation when a LaTeX compiler is installed.

## Stage 2 Features

- Profile loading from YAML with private-first fallback behavior.
- Private profile creation from the public-safe example template.
- Profile editing and saving from the frontend to `data/profile.yaml`.
- Resume loading from LaTeX with private-first fallback behavior.
- Private resume creation from the public-safe example template.
- Resume editing and saving from the frontend to `data/resume/base_resume.tex`.
- Optional LaTeX PDF compilation with `xelatex` preferred and `pdflatex` as fallback.
- GitHub-safe private file workflow with ignored local files and committed example templates only.

## Core Safety Principles

- CareerAgent is human-in-the-loop by design.
- CareerAgent may assist with research, drafting, verification, and safe autofill preparation.
- CareerAgent must never auto-submit an application.
- CareerAgent must never click final submit, apply, confirm, finalize, or equivalent completion actions.
- The user always manually reviews and manually submits.
- CareerAgent should never invent experience, achievements, credentials, or answers.
- The app should never log secrets or print full personal profile information unnecessarily.

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

5. Open:

- Frontend: [http://localhost:3000](http://localhost:3000)
- Profile page: [http://localhost:3000/profile](http://localhost:3000/profile)
- Resume page: [http://localhost:3000/resume](http://localhost:3000/resume)
- Backend: [http://localhost:8000](http://localhost:8000)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

If `data/profile.yaml` or `data/resume/base_resume.tex` do not exist yet, the app still starts and falls back to the committed example files.

If LaTeX is not installed, the resume compile endpoint stays available and returns a clear message instead of crashing the backend.

## Public GitHub Safety

- Real profile info should go in `data/profile.yaml`, which is gitignored.
- Real resume content should go in `data/resume/base_resume.tex`, which is gitignored.
- API keys, tokens, and secrets should go in `.env`, which is gitignored.
- Generated application packets and generated PDFs are private and ignored under `outputs/`.
- Only `.env.example`, `data/profile.example.yaml`, and `data/resume/base_resume.example.tex` should be committed.
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

## What Works In Stage 2

- `GET /health`
- `GET /api/profile`
- `PUT /api/profile`
- `POST /api/profile/create-private`
- `GET /api/profile/status`
- `GET /api/resume`
- `PUT /api/resume`
- `POST /api/resume/create-private`
- `POST /api/resume/compile`
- `GET /api/resume/status`
- Existing Stage 1 routes for jobs, tracker, packets, market, and autofill

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

- Status: Complete after this audit
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
- Improve scoring over time with real outcome data.

### Stage 6: Application Packet Generation

- Create per-job output folders.
- Generate tailored resume, cover letter, recruiter message, application questions, notes, and change summary.
- Write in the user’s direct/simple style.
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

## Next Stage

**Next Stage: Stage 3 — Job Import + Job Parsing**

Stage 3 will:

- add a job import form
- allow pasted job descriptions
- allow pasted job URLs
- parse title, company, location, skills, requirements, responsibilities, experience level, and source
- save imported jobs to PostgreSQL
- prepare jobs for verification and scoring

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
