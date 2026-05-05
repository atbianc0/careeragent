# CareerAgent

CareerAgent is a customizable, human-in-the-loop job-search and application assistant.

It is designed to help users:

- find relevant jobs
- verify whether jobs are still open
- score jobs by fit and availability
- generate tailored application packets
- track applications and outcomes
- assist with safe browser autofill in Chromium while stopping before submit

CareerAgent must never auto-submit job applications.

CareerAgent must never click final submit, apply, confirm, or equivalent end-state buttons.

CareerAgent must never invent experience, skills, credentials, companies, dates, results, education, or work authorization details.

## Current Stage

**Stage 11 — Prediction and Improvements**

- Stage 1: Complete
- Stage 2: Complete
- Stage 3: Complete
- Stage 4: Complete
- Stage 5: Complete
- Stage 6: Complete
- Stage 7: Complete
- Stage 8: Complete
- Stage 9: Complete
- Stage 10: Complete
- Stage 11: Complete

Stage 11 adds cautious, explainable prediction estimates on top of the completed parsing, packet, tracker, autofill, market, and AI-provider workflow. CareerAgent now uses stored local history to estimate priority, close risk, source quality, role quality, response likelihood, and apply windows while clearly labeling confidence and small-sample limits.

## Features Through Stage 11

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
- Track application statuses such as `saved`, `packet_ready`, `application_opened`, `applied_manual`, `follow_up`, `interview`, `rejected`, `offer`, `withdrawn`, and `closed_before_apply`.
- Log application events with timestamps, notes, and optional status transitions.
- Track when a packet is generated or viewed.
- Track when an application link is opened through CareerAgent.
- Let the user manually mark jobs as applied, interview, rejected, offer, withdrawn, or closed before applying.
- Let the user add notes and follow-up reminders to job records.
- Show a real Tracker page with grouped statuses, summary cards, upcoming follow-ups, and recent activity.
- Show per-job timeline history on the job detail page.
- Update dashboard stats from tracker data.
- Preview a rule-based autofill plan before opening the browser.
- Launch Chromium with Playwright in headless Docker mode or headed local mode when a display is available.
- Detect common application fields using explainable rule-based matching.
- Fill only safe, high-confidence factual fields.
- Upload generated packet files such as `tailored_resume.pdf` when available.
- Skip low-confidence, unknown, or sensitive fields unless the policy explicitly allows a conservative “Prefer not to answer” response.
- Detect final submit/apply/confirm actions and never click them.
- Log `autofill_started` and `autofill_completed` tracker events.
- Update job status to `autofill_started` and `autofill_completed` without ever marking the job applied automatically.
- Show autofill summaries and warnings in the frontend.
- Show pipeline summary cards for total, verified, scored, packet-ready, opened, applied, interview, rejected, and offer-stage jobs.
- Break down jobs by role, company, location, source, verification status, and application status.
- Surface top requested skills and top missing skills from stored parsing and scoring data.
- Show score analytics, including averages, distribution buckets, and top and low scored jobs.
- Show verification analytics, outcome analytics, and observed response rates with small-sample warnings.
- Show observed activity over time for imports, verification, scoring, packets, application opens, applies, interviews, rejections, and offers.
- Flag stale and likely closed jobs with conservative recommendations such as reverify, deprioritize, or mark closed before apply.
- Generate rule-based insights without pretending to predict future performance.
- Export safe job and application metadata to JSON or CSV without including private profile, resume, or packet contents.
- Add an AI provider abstraction with MockProvider, OpenAIProvider, and a LocalLLMProvider placeholder.
- Keep MockProvider available with no API key so the app remains fully testable and usable offline from external AI services.
- Add an AI status endpoint and provider test endpoint without exposing secrets.
- Allow optional AI job parsing while keeping rule-based parsing as the default fallback.
- Allow optional AI packet drafting for cover letters, recruiter messages, application questions, and conservative resume-tailoring advisory notes.
- Allow optional AI market insight summaries while preserving the Stage 9 rule-based insight path.
- Run review-required safety checks on AI-generated content before it is used in packets or insight summaries.
- Keep all AI usage optional and never require an API key for the app to start or function.
- Estimate predicted application priority from existing priority scores, source quality, role quality, response likelihood, close risk, packet readiness, stale signals, and application status.
- Estimate close risk with conservative labels such as low, medium, high, closed, or unknown.
- Estimate response likelihood from stored applied-job outcomes when enough history exists, and warn when history is too small.
- Score source quality and role quality from historical outcomes with small-sample warnings.
- Estimate apply windows from imported, posted, applied, and response-history weekdays when enough data exists.
- Store prediction scores, confidence, evidence, and update timestamps on job records.
- Recalculate prediction scores for all jobs.
- Show a Predictions dashboard with top priority jobs, close-risk jobs, response likelihood, source quality, role quality, apply windows, insights, and exports.
- Export prediction-safe JSON or CSV without private profile, resume, notes, packet contents, generated files, API keys, or secrets.
- Keep Stage 1 through Stage 5 features intact, including profile editing, resume editing, import, verification, scoring, and ranked recommendations.
- Keep generated outputs private and gitignored.

## Stage 11 Implemented

- Predicted application priority
- Close-risk estimates
- Response-likelihood estimates
- Source quality scoring
- Role quality scoring
- Apply-window estimates from collected history
- Prediction confidence and evidence
- Recalculate predictions
- Prediction dashboard
- Prediction export

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
12. CareerAgent summarizes job-market and personal application trends so the user can decide where and when to apply next.
13. CareerAgent uses optional AI providers to improve parsing, tailoring, application drafts, and insights while keeping everything reviewable and safe.
14. CareerAgent uses collected history to improve recommendations and make cautious predictions.

At the end of this Stage 11 pass, setup, import, parsing, saved-job persistence, rule-based verification, rule-based scoring, packet generation, tracker logging, manual application status updates, follow-up tracking, autofill previews, safe browser autofill, market analytics dashboards, optional AI provider integration, and cautious prediction estimates are implemented. Final submission is still always manual.

## Tech Stack

- Frontend: Next.js
- Backend: FastAPI
- Database: PostgreSQL
- Local development: Docker Compose
- Browser automation: Playwright
- Resume generation: LaTeX
- AI integration: MockProvider by default, optional OpenAIProvider, and a LocalLLMProvider placeholder

## How To Run Locally

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Optional: configure AI in your private `.env` if you want OpenAI instead of MockProvider:

```bash
AI_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=your_model_here
```

If you skip this, CareerAgent uses `AI_PROVIDER=mock` and still works normally with no API key.

3. Optional: if you want demo/sample jobs in an empty local database, set this in `.env`:

```bash
ENABLE_SAMPLE_JOBS=true
```

4. Copy the safe public profile template to your private local profile file:

```bash
cp data/profile.example.yaml data/profile.yaml
```

The committed example profile is intentionally neutral. It does not include real education details and does not auto-answer work authorization, sponsorship, or relocation questions. Put only your own truthful answers in `data/profile.yaml`.

5. Copy the safe public resume template to your private local resume file:

```bash
cp data/resume/base_resume.example.tex data/resume/base_resume.tex
```

6. Start the stack:

```bash
docker compose up --build
```

7. Open:

- Frontend: [http://localhost:3000](http://localhost:3000)
- Profile page: [http://localhost:3000/profile](http://localhost:3000/profile)
- Resume page: [http://localhost:3000/resume](http://localhost:3000/resume)
- AI page: [http://localhost:3000/ai](http://localhost:3000/ai)
- Predictions page: [http://localhost:3000/predictions](http://localhost:3000/predictions)
- Backend: [http://localhost:8000](http://localhost:8000)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

If `data/profile.yaml` or `data/resume/base_resume.tex` do not exist yet, the app still starts and falls back to the committed example files.

The backend Docker image includes LaTeX packages for PDF compilation. If LaTeX is unavailable in a custom or lighter image, the resume compile endpoint stays available and returns a clear message instead of crashing the backend.

If Playwright Chromium is not installed yet, install it with:

```bash
python -m playwright install chromium
```

Docker defaults autofill to headless Playwright with `PLAYWRIGHT_HEADLESS=true`, because Docker on macOS usually has no X server/display for headed Chromium. CareerAgent still requires manual review and never submits applications.

### LaTeX PDF Compilation

The backend Docker image includes TeX packages for `xelatex` and `pdflatex`, including common resume packages such as `geometry`, `enumitem`, `hyperref`, `titlesec`, and `parskip`, plus recommended TeX fonts used by hyperlink/font packages. The first Docker build may take longer and the backend image will be larger because TeX Live is substantial.

After rebuilding with `docker compose up --build`, `Compile PDF` on `/resume` should work inside Docker when the LaTeX source is valid. Generated PDFs are written under `outputs/resume/` or packet output folders, which are gitignored.

If you want a lighter backend image, remove the TeX Live packages from `backend/Dockerfile` and use the generated `.tex` output only. CareerAgent keeps the graceful no-compiler fallback and returns a clear JSON message instead of crashing.

### Troubleshooting

Browser extension hydration warning: some extensions, especially Grammarly, inject attributes like `data-gr-ext-installed` into the page before React hydrates. CareerAgent sets `suppressHydrationWarning` on the `<body>` element to avoid this harmless warning. Hydration errors inside app components should still be treated as real bugs and fixed.

### Playwright Autofill in Docker

Docker on macOS usually cannot show headed Chromium because the container has no X server/display. CareerAgent defaults to headless Playwright in Docker:

```bash
PLAYWRIGHT_HEADLESS=true
```

Headless mode can attempt safe autofill and return a summary, but it cannot show you a live browser window. CareerAgent never clicks final submit, apply, confirm, finish, or send buttons. You must open the application manually, review every field, and submit yourself.

For visible local autofill, run the backend outside Docker with a display:

```bash
PLAYWRIGHT_HEADLESS=false
python -m playwright install chromium
uvicorn main:app --reload
```

If headed mode fails with a “Missing X server” or similar display error, switch back to `PLAYWRIGHT_HEADLESS=true`, run the backend locally outside Docker, or configure a display/Xvfb. `PLAYWRIGHT_USE_XVFB=false` is the default; set it to `true` only when Xvfb is installed and you intentionally want a virtual display for headed Chromium.

If you are upgrading from an older local database, CareerAgent adds the Stage 3 through Stage 11 job, packet, tracker, autofill, market, AI-supporting, and prediction fields automatically on startup. If you want a clean local reset instead, run:

```bash
docker compose down -v
docker compose up --build
```

## Stage 10 AI Provider Setup

CareerAgent works without any API key using MockProvider.

To enable OpenAI safely:

1. Copy `.env.example` to `.env`.
2. Set:

```bash
AI_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=your_model_here
```

3. Restart the app.

Important:

- `.env` is gitignored.
- Never commit API keys.
- Do not put API keys in `profile.yaml`.
- Do not put API keys in source code.
- The frontend never receives the key.
- The app works without a key using MockProvider.

## Stage 11 Prediction Limitations

- AI outputs are drafts and must be reviewed manually.
- Safety checks are conservative but not perfect.
- AI should not be trusted for legal, visa, sponsorship, or demographic answers.
- Work authorization and sponsorship answers must come from profile settings.
- Resume structure and style must still be preserved.
- Predictions are estimates only.
- Small datasets are unreliable.
- Response likelihood requires applied jobs and outcomes.
- Apply-window estimates are based only on collected CareerAgent history.
- CareerAgent does not guarantee interviews, offers, responses, or ideal timing.
- The user should manually review all recommendations.

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
- The app should never expose API keys through the frontend or API responses.

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

## Stage 3 Through Stage 11 Usage

### Job import workflow

1. Open `/jobs`.
2. Choose `Paste Job Description` or `Paste Job URL`.
3. Paste the content and keep the source as `manual` or change it if needed.
4. Click `Preview Parse`.
5. Review the parsed fields.
6. Click `Import and Save`.
7. Open the saved job detail page.
8. Restart the app later and your saved jobs will still be in PostgreSQL.

Workday and JavaScript-heavy job pages:

- Some job boards, especially Workday, render job descriptions with JavaScript.
- CareerAgent first tries normal requests and BeautifulSoup parsing.
- If the text is not readable, CareerAgent may infer partial details from the URL, page title, meta tags, or embedded public JSON.
- For best results, manually paste the full job description text.
- CareerAgent does not bypass login walls, CAPTCHAs, anti-bot protections, or authentication.

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

### Stage 7 tracker workflow

1. Import jobs.
2. Verify and score them.
3. Generate a packet for a job when you want application materials ready.
4. Open the job detail page or `/tracker`.
5. Use `Open Application` through CareerAgent so the app logs the application-link-opened event first.
6. Manually apply on the company site.
7. Return to CareerAgent and click `Mark Applied`.
8. Add notes or set follow-up reminders as needed.
9. Update the status again when an interview, rejection, offer, withdrawal, or closed-before-apply outcome happens.

### Stage 8 autofill workflow

1. Make sure profile data exist locally, or let CareerAgent fall back to the committed example profile.
2. Import, verify, and score a job with a saved application URL.
3. Generate an application packet for that job when you want uploadable materials ready.
4. Open the job detail page, the packet detail page, or `/autofill`.
5. Click `Preview Autofill Plan`.
6. Review the proposed values, uploadable files, and warnings.
7. Click `Start Autofill in Browser`.
8. If Docker is in headless mode, review the returned summary and open the application manually in your browser. If running headed locally, review the visible Chromium window manually.
9. Manually click submit only after reviewing the form yourself.
10. Return to CareerAgent and manually mark the job applied from the tracker after you really submit it.

### Stage 9 market analytics workflow

1. Import jobs.
2. Verify and score them so CareerAgent has enough structured data to analyze.
3. Generate packets and track applications when you start applying.
4. Open `/market`.
5. Review the pipeline summary, skill trends, score analytics, outcomes, activity, stale jobs, and insights.
6. Export JSON or CSV if you want to do your own personal analysis outside the app.

### Stage 10 AI workflow

1. Open `/ai`.
2. Confirm MockProvider is active when no API key is configured.
3. Run the provider test form with `mock`.
4. To use OpenAI, set `AI_PROVIDER=openai`, `OPENAI_API_KEY`, and optionally `OPENAI_MODEL` in private `.env`, then restart the app.
5. Use optional AI parsing on `/jobs` only when you want a reviewable enhanced parse.
6. Use optional AI drafts from a job detail page when generating packet materials.
7. Use optional AI insights from `/market` when you want a short draft summary of stored analytics.

### Stage 11 prediction workflow

1. Import jobs.
2. Verify and score jobs.
3. Generate packets for jobs you are seriously considering.
4. Track application outcomes such as applied, interview, rejected, and offer.
5. Open `/predictions`.
6. Click `Recalculate Predictions`.
7. Review high-priority jobs and high close-risk jobs.
8. Review source quality, role quality, response likelihood, and apply-window estimates.
9. Export JSON or CSV if you want a safe local prediction dataset.
10. Use predictions as guidance, not guarantees.

### Stage 11 limitations

- URL parsing can infer partial details from some JavaScript-heavy job pages, but full descriptions may still require manual paste.
- Verification is rule-based and approximate.
- Scoring is also rule-based and approximate.
- Stage 6 deterministic generation remains the fallback; Stage 10 AI drafts are optional and off by default.
- Tailored resume edits are intentionally conservative to preserve structure and avoid invented claims.
- Cover letter and recruiter message drafts may still need meaningful editing.
- Packet generation does not submit applications; autofill is a separate Stage 8 step and still stops before submit.
- PDF compilation depends on local or container LaTeX availability.
- If LaTeX is unavailable, packet generation still succeeds and stores the `.tex` source with a graceful warning.
- User review is required before trusting or using any generated content.
- Scoring remains deterministic in Stage 10 and does not use AI yet.
- Scoring may miss skills or context that are not obvious in the parsed text or base resume text.
- Scores do not guarantee interview chances or application outcomes.
- Some job boards block requests or expose too little text for a confident check.
- Browser-based extraction and browser-based verification may be added later.
- A job can look open while still being closed behind a login wall or deeper ATS flow.
- User review is still required before trusting any recommendation or generated packet asset.
- CareerAgent does not submit applications.
- The user must manually mark a job as applied.
- Follow-up reminders are tracked in the app but are not scheduled notifications yet.
- Calendar and email integrations are still future improvements.
- Autofill is rule-based and may miss fields or misclassify unusual layouts.
- Some job sites require login or block automation before the real application form appears.
- CareerAgent never bypasses CAPTCHAs, anti-bot protections, or login walls.
- Docker defaults autofill to headless mode because headed Chromium needs a display/XServer. Local backend execution is the simplest visible-browser path on macOS.
- CareerAgent still stops before final submission every time.
- AI-assisted parsing is Stage 10.
- Some parsed, verified, and scored fields will be imperfect because CareerAgent currently uses deterministic rule-based parsing, verification, and scoring instead of AI or browser automation.
- Analytics are based only on data you have collected in CareerAgent.
- Small sample sizes can be misleading, especially for response-rate groupings.
- Response rates require jobs to be marked applied and to have later outcomes recorded.
- Predictions are based only on data you have collected in CareerAgent.
- Predicted priority, close risk, response likelihood, source quality, role quality, and apply windows are estimates only.
- Small datasets are low confidence and may be misleading.
- Response likelihood requires applied jobs and recorded outcomes.
- Apply-window estimates are local observations, not universal best-day advice.
- CareerAgent does not guarantee interviews, responses, offers, or application outcomes.
- User review is required before acting on every recommendation.

## What Works In Stage 11

- `GET /health`
- `GET /api/ai/status`
- `GET /api/ai/providers`
- `POST /api/ai/test`
- `GET /api/market/dashboard`
- `GET /api/market/summary`
- `GET /api/market/skills`
- `GET /api/market/scores`
- `GET /api/market/outcomes`
- `GET /api/market/activity`
- `GET /api/market/stale-jobs`
- `GET /api/market/insights`
- `GET /api/market/insights?use_ai=true&provider=mock`
- `GET /api/market/export?format=json`
- `GET /api/market/export?format=csv`
- `GET /api/prediction/dashboard`
- `POST /api/prediction/recalculate`
- `GET /api/prediction/jobs`
- `GET /api/prediction/jobs/{job_id}`
- `GET /api/prediction/source-quality`
- `GET /api/prediction/role-quality`
- `GET /api/prediction/apply-windows`
- `GET /api/prediction/insights`
- `GET /api/prediction/export?format=json`
- `GET /api/prediction/export?format=csv`
- `GET /api/autofill/status`
- `GET /api/autofill/safety`
- `POST /api/autofill/dry-run`
- `POST /api/autofill/start`
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
- `POST /api/jobs/parse` with `use_ai=false`
- `POST /api/jobs/parse` with `use_ai=true` and `provider=mock`
- `POST /api/jobs/import`
- `POST /api/jobs/import` with optional `use_ai` and `provider`
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
- `POST /api/packets/generate` with optional `use_ai` and `provider`
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
- `GET /api/tracker/summary`
- `GET /api/tracker/jobs`
- `GET /api/tracker/jobs/{job_id}/timeline`
- `POST /api/tracker/jobs/{job_id}/status`
- `POST /api/tracker/jobs/{job_id}/note`
- `POST /api/tracker/jobs/{job_id}/follow-up`
- `POST /api/tracker/jobs/{job_id}/follow-up/complete`
- `POST /api/tracker/jobs/{job_id}/open-application`
- `GET /api/tracker/events`
- Real Stage 11 pages for jobs, tracker, packets, packet detail, job timelines, browser autofill, market analytics, predictions, and AI provider status/testing

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
- Use safe partial parsing for Workday and other JavaScript-heavy URLs when only URL/title metadata is available.
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

- Status: Complete
- Track saved jobs, verified jobs, packet-ready jobs, application link opened, autofill started, autofill completed, manually applied, interview, rejected, offer, follow-up.
- Track clicks, notes, and timestamps.
- Show a real Tracker page and per-job timelines.

### Stage 8: Browser Autofill with Playwright

- Status: Complete
- Launch Chromium in configurable headless or headed mode.
- Detect common application fields.
- Fill high-confidence factual fields.
- Draft/fill common questions when safe.
- Prefer not to answer demographic questions by default.
- Never click submit/apply/final confirmation buttons.
- Log autofill start and completion events into the tracker.
- Show autofill previews and browser-session summaries in the UI.

### Stage 9: Market Analytics Dashboard

- Status: Complete
- Show a real analytics dashboard for pipeline, skills, score, verification, outcomes, response rates, activity, stale jobs, and insights.
- Export safe analytics data to JSON and CSV for personal analysis.
- Feed Stage 11 prediction estimates with stored analytics and outcomes.

### Stage 10: AI Provider Integration

- Status: Complete
- Add provider pattern with `MockProvider`, `OpenAIProvider`, and a `LocalLLMProvider` placeholder.
- Keep MockProvider available without API keys.
- Use optional AI for job parsing, resume tailoring advice, cover letters, recruiter messages, application question drafts, and market insight summaries.
- Keep rule-based parsing, deterministic packet generation, and rule-based insights as safe defaults and fallbacks.
- Keep outputs reviewable and safety-checked.

### Stage 11: Prediction and Improvements

- Status: Complete
- Predict which jobs are most worth applying to first with cautious priority estimates.
- Estimate close risk and likely stale postings.
- Estimate response likelihood from stored applied-job outcomes when enough history exists.
- Improve priority scoring with source quality, role quality, company history, packet readiness, stale signals, and application status.
- Estimate source quality and role quality from historical outcomes with small-sample warnings.
- Estimate apply windows from collected import, applied, and response history.
- Keep all recommendations descriptive, reviewable, grounded in stored data, and labeled with confidence.

## Beyond Stage 11

Future stages can refine prediction feedback loops, follow-up planning, ATS coverage, local-model support, and reminder integrations while keeping CareerAgent human-in-the-loop and safe.

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
