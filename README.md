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

## Quick Run
```bash
 ./scripts/docker-up-open.sh
```

## Project Map

For a full file-by-file overview of the app structure, routes, backend services, models, and workflows, see:

[PROJECT_MAP.md](./PROJECT_MAP.md)

## Product Workflow

1. Fill Profile.
2. Discover Jobs.
3. Save good jobs.
4. CareerAgent auto-verifies and scores saved jobs.
5. Go to Apply.
6. Choose AI-assisted apply or Basic Autofill.
7. Review everything and manually submit on the employer site.
8. Mark Applied.
9. Track outcomes in Insights.

AI assistance is optional and only runs after an explicit AI-assisted apply click. CareerAgent never submits applications. Follow-ups are hidden from the main workflow for now, Tracker lives in Insights, and the job detail page is secondary/advanced only.

## Current Stage

**Stage 12 — Job Finder + Source Discovery**

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
- Stage 12: Initial implementation

Stage 12 adds a safe, source-based Job Finder that imports a saved ATS/company source database, discovers reviewable candidates from known boards and company career pages, deduplicates/filters them, and lets the user save selected candidates into the Jobs -> Apply workflow. Saving a job automatically runs verification and scoring.

## Features Through Stage 12

- Generate a private per-job packet folder under `outputs/application_packets/`.
- Generate `tailored_resume.tex` by minimally editing the source LaTeX resume while preserving structure and style; AI-assisted apply can use the selected provider to return a complete validated LaTeX resume source.
- Attempt `tailored_resume.pdf` compilation with `xelatex` and `pdflatex`, falling back from the local backend to the Docker backend image when the host has no TeX install.
- Generate `cover_letter.md`.
- Generate `recruiter_message.md`.
- Generate `application_questions.md`.
- Generate `application_notes.md`.
- Generate `change_summary.md`.
- Generate `job_summary.json`.
- Generate `packet_metadata.json`.
- Save packet records in PostgreSQL with generation status, timestamps, file paths, and graceful error details.
- Show packets from Apply and the advanced packet library on `/packets` and `/packets/{id}`.
- Track application statuses such as saved, ready to apply, applying, applied, interview, rejected, offer, withdrawn, and closed before apply. Internal legacy statuses are mapped to these simpler user-facing labels.
- Log application events with timestamps, notes, and optional status transitions.
- Track when a packet is generated or viewed.
- Track when an application link is opened through CareerAgent.
- Let the user manually mark jobs as applied, interview, rejected, offer, withdrawn, or closed before applying.
- Let the user add notes and maintain existing follow-up data through legacy/internal paths, while follow-ups are hidden from the primary workflow for now.
- Show tracker/status summaries, outcome counts, and recent activity in `/insights`.
- Keep the job detail page secondary and simple, with raw evidence collapsed under Advanced details.
- Update dashboard stats from tracker data.
- Open applications in the user's normal browser with tracker logging and no autofill.
- Launch Chromium with Playwright in headless Docker mode or headed local mode when a display is available.
- Detect common application fields using explainable rule-based matching.
- Fill only safe, high-confidence factual fields.
- Upload generated packet files such as `tailored_resume.pdf` when available.
- Skip low-confidence, unknown, or sensitive fields unless the policy explicitly allows a conservative “Prefer not to answer” response.
- Detect final submit/apply/confirm actions and never click them.
- Log visible autofill start/completion events and headless diagnostic metadata separately.
- Update job status to `autofill_started` and `autofill_completed` only for visible sessions the user can continue from.
- Show two user-facing autofill actions plus collapsed headless diagnostics in the frontend.
- Show pipeline summary cards for total, verified, scored, packet-ready, opened, applied, interview, rejected, and offer-stage jobs.
- Break down jobs by role, company, location, source, verification status, and application status.
- Surface top requested skills and top missing skills from stored parsing and scoring data.
- Show score analytics, including averages, distribution buckets, and top and low scored jobs.
- Show verification analytics, outcome analytics, and observed response rates with small-sample warnings.
- Show observed activity over time for imports, verification, scoring, packets, application opens, applies, interviews, rejections, and offers.
- Flag stale and likely closed jobs with conservative recommendations such as reverify, deprioritize, or mark closed before apply.
- Generate rule-based insights without pretending to predict future performance.
- Export safe job and application metadata to JSON or CSV without including private profile, resume, or packet contents.
- Add an AI provider abstraction with MockProvider by default and optional OpenAIProvider or GeminiProvider.
- Keep MockProvider available with no API key so the app remains fully testable and usable offline from external AI services.
- Add an AI status endpoint and provider test endpoint without exposing secrets.
- Keep job parsing, matching, scoring, verification, insights, predictions, saved-source search, autofill, and applying local/rule-based with no external AI/API dependency.
- Allow optional selected-provider AI writing assistance for validated tailored resume source, cover letters, recruiter messages, application question drafts, and one-time Job Finder search keyword generation only after explicit user action and policy checks.
- Run review-required safety checks on AI-generated packet content before it is used.
- Keep all external API usage optional, disabled by default, and never required for the app to start or function.
- Estimate predicted application priority from existing priority scores, source quality, role quality, response likelihood, close risk, packet readiness, stale signals, and application status.
- Estimate close risk with conservative labels such as low, medium, high, closed, or unknown.
- Estimate response likelihood from stored applied-job outcomes when enough history exists, and warn when history is too small.
- Score source quality and role quality from historical outcomes with small-sample warnings.
- Estimate apply windows from imported, posted, applied, and response-history weekdays when enough data exists.
- Store prediction scores, confidence, evidence, and update timestamps on job records.
- Recalculate prediction scores for all jobs.
- Show a Predictions dashboard with top priority jobs, close-risk jobs, response likelihood, source quality, role quality, apply windows, insights, and exports.
- Export prediction-safe JSON or CSV without private profile, resume, notes, packet contents, generated files, API keys, or secrets.
- Generate deterministic job-search queries from profile/resume/defaults, with optional AI-assisted query generation.
- Import the generated job source database from `job-database-script/outputs/source_discovery/job_sources.csv` or `.json`.
- Summarize saved source boards by ATS type and enabled/valid status.
- Search saved Lever, Greenhouse, Ashby, Workday, or all enabled source boards without manually pasting URLs every run.
- Discover jobs from Greenhouse, Lever, Ashby, conservative Workday URL fallback, company career pages, and generic remote-board/source URLs.
- Accept LinkedIn and Indeed pasted links manually without scraping those sites automatically.
- Store discovery runs and job candidates separately from saved jobs.
- Deduplicate discovered candidates against existing candidates and saved jobs.
- Filter candidates for Bay Area/new-grad/entry-level relevance and exclude obvious senior, staff, principal, manager, PhD-required, Master's-required, and 5+ year roles.
- Review candidates in `/job-finder` and import only selected candidates into the main Jobs table.
- Optionally verify and score imported candidates using the existing verifier/scoring flow.
- Keep Stage 1 through Stage 5 features intact, including profile editing, resume editing, import, verification, scoring, and ranked recommendations.
- Keep generated outputs private and gitignored.

## Stage 12 Implemented

- Query generation from profile, resume, and default test queries
- Safe source-based discovery, not aggressive crawling
- Greenhouse discovery
- Lever discovery
- Ashby discovery
- Conservative Workday direct-link fallback
- Company career page link discovery with a small link budget
- Manual LinkedIn/Indeed pasted-link support
- Candidate review table
- Deduplication
- Relevance filtering
- Import selected candidates into main Jobs
- Optional verify/score after import
- Source database import from generated CSV/JSON
- Saved source summary and source management
- Saved-source search with first-5/next-5 paging from the same discovery run

## Stage 12 Limitations

- This is not an aggressive crawler.
- CareerAgent searches saved company boards, not every company globally.
- The source database can be expanded over time by rerunning the discovery script.
- LinkedIn and Indeed are manual pasted links only.
- Workday pages are often JavaScript-heavy and may return partial URL-inferred candidates.
- Some company pages block requests or require browser rendering.
- Users should review candidates before importing.

## Using the Job Source Database

1. Run the source discovery script in `job-database-script`.
2. It creates `job-database-script/outputs/source_discovery/job_sources.csv` and `job-database-script/outputs/source_discovery/job_sources.json`.
3. Open CareerAgent -> Jobs -> Discover.
4. Click Import Source CSV.
5. Search Lever, Greenhouse, Ashby, Workday, or all enabled sources.
6. Review the first 5 matches.
7. Click Next 5 to page through candidates already saved for that discovery run.
8. Import selected jobs into Saved Jobs.

CareerAgent searches the saved company boards in the source database, not every company globally. The source database can be expanded over time. Workday support may be partial because many Workday boards are JavaScript-heavy. LinkedIn and Indeed remain manual-only sources. CareerAgent does not auto-apply and never clicks final submit/apply/confirm buttons.

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
13. CareerAgent uses optional, explicit AI assists only for writing drafts, validated resume tailoring, and one-time Job Finder keyword generation.
14. CareerAgent uses collected history to improve recommendations and make cautious predictions.

At the end of this Stage 11 pass, setup, import, parsing, saved-job persistence, rule-based verification, rule-based scoring, packet generation, tracker logging, manual application status updates, follow-up tracking, autofill previews, safe browser autofill, market analytics dashboards, optional AI provider integration, and cautious prediction estimates are implemented. Final submission is still always manual.

## Tech Stack

- Frontend: Next.js
- Backend: FastAPI
- Database: PostgreSQL
- Local development: Docker Compose
- Browser automation: Playwright
- Resume generation: LaTeX
- AI integration: one selected provider at a time with `mock` by default, optional OpenAI, or optional Gemini

## How To Run Locally

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Optional: configure AI assists in your private `.env` only if you want explicit OpenAI or Gemini writing/query help:

```bash
AI_PROVIDER=mock
AI_ALLOW_EXTERNAL_CALLS=false
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
```

If you skip this, CareerAgent uses `AI_PROVIDER=mock` and still works normally with no API key.

## AI Provider Policy

Core CareerAgent works without external AI calls. `AI_PROVIDER` controls the single active provider: `mock`, `openai`, or `gemini`. External AI calls are disabled by default with `AI_ALLOW_EXTERNAL_CALLS=false`.

OpenAI and Gemini are alternatives, not simultaneous providers. Only the selected provider is used, even if both keys exist. `mock` never makes paid external calls.

AI is allowed only for validated tailored resume source, cover letters, recruiter messages, long application answer drafts, and one-time Job Finder keyword generation after an explicit user click. CareerAgent does not use AI for job URL parsing, core matching, scoring, verification, insights, source discovery, saved-source search, autofill, or applying. It does not scrape search engine HTML, LinkedIn, or Indeed automatically.

To allow paid OpenAI calls, set `AI_PROVIDER=openai`, `AI_ALLOW_EXTERNAL_CALLS=true`, configure `OPENAI_API_KEY`, and explicitly trigger an allowed writing/query action in the UI. To allow Gemini calls, set `AI_PROVIDER=gemini`, `AI_ALLOW_EXTERNAL_CALLS=true`, configure `GEMINI_API_KEY`, and explicitly trigger an allowed writing/query action in the UI.

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

Docker Compose starts the CareerAgent frontend, backend, database, Playwright dependencies, and LaTeX tooling. A Docker container on macOS cannot open a normal host Chromium window that you can continue from; visible autofill requires the backend to run locally on your Mac with `PLAYWRIGHT_HEADLESS=false`. CareerAgent still requires manual review and never submits applications.

For normal local use with native Chromium autofill, use the wrapper script:

```bash
./scripts/docker-up-open.sh
```

That command starts Postgres and the frontend in Docker, stops the Docker backend if it is running, starts the backend locally on port `8000`, then opens `/apply` in Chromium/Chrome. Keep that terminal open while using the app.

### LaTeX PDF Compilation

The backend Docker image includes TeX packages for `xelatex` and `pdflatex`, including common resume packages such as `geometry`, `enumitem`, `hyperref`, `titlesec`, and `parskip`, plus recommended TeX fonts used by hyperlink/font packages. The first Docker build may take longer and the backend image will be larger because TeX Live is substantial.

After rebuilding with `docker compose up --build`, `Compile PDF` on `/resume` should work inside Docker when the LaTeX source is valid. If you use the visible local backend helper for native Chromium and your Mac does not have TeX installed, CareerAgent delegates PDF compilation to the Docker backend image. Generated PDFs are written under `outputs/resume/` or packet output folders, which are gitignored.

If you want a lighter backend image, remove the TeX Live packages from `backend/Dockerfile` and use the generated `.tex` output only. CareerAgent keeps the graceful no-compiler fallback and returns a clear JSON message instead of crashing.

### Troubleshooting

Browser extension hydration warning: some extensions, especially Grammarly, inject attributes like `data-gr-ext-installed` into the page before React hydrates. CareerAgent sets `suppressHydrationWarning` on the `<body>` element to avoid this harmless warning. Hydration errors inside app components should still be treated as real bugs and fixed.

### Autofill

There are two user-facing Autofill actions:

1. `Open in Browser`
   - Manual apply.
   - Opens the job URL in your normal browser.
   - Logs `application_link_opened`.
   - No autofill runs.

2. `Fill Application`
   - Requires Playwright headed mode from a backend running on the host machine.
   - Docker on macOS cannot open a normal host Chromium window you can continue from.
   - In Apply, this is the `Fill Application in Chromium` action.
   - Used by both AI-assisted apply and Basic Autofill.
   - Basic Autofill fills factual profile/resume fields only: name, email, phone, location, links, configured work authorization/defaults, and safe resume upload.
   - AI-assisted apply can also draft and fill long application questions when AI is enabled, policy allows `draft_application_answer`, and the user explicitly clicked AI-assisted apply.
   - Live long-answer fields are drafted from the exact detected on-page prompt, including Lever-style numbered technical question blocks, instead of reusing generic packet-level application text.
   - AI-drafted answers are marked as drafts and require review before submission.
   - EEO, demographic, pronoun, veteran, disability, and other sensitive/optional fields are skipped by default. CareerAgent only selects "Prefer not to answer" / "Decline to self-identify" for sensitive optional dropdowns when the user explicitly enables that behavior and the option exists.
   - Fills safe fields and uploads available packet/base resume PDFs.
   - Opens a headed Chromium session and leaves it open for manual review.
   - Returns a session id that can be closed from the Autofill page.
   - The user manually submits.

CareerAgent never clicks final submit, apply, confirm, finish, send, or equivalent completion actions.

Docker can run hidden Playwright diagnostics, but native visible autofill needs the backend on your Mac:

```bash
cd backend
PLAYWRIGHT_HEADLESS=false python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On `/apply`, `Start Basic Autofill` opens a normal Chromium window only when the active backend is local and visible Playwright is ready. AI-assisted apply uses the same `Fill Application in Chromium` action after packet generation and can fill review-required AI drafts for detected long-answer questions. If AI is disabled, detected long-answer questions are reported with manual-draft guidance and a Settings link.

Headless Diagnostic:

- For testing only.
- Runs in a hidden browser to test field detection and safe filling.
- Returns a summary, screenshot, and copyable values.
- Cannot be continued.
- Is not a real application flow.

If CareerAgent opens a page but detects zero form fields, the result is `no_fields_detected` rather than `autofill_completed`. This often means the URL is a job-detail page, a JavaScript-heavy ATS page, a login/CAPTCHA page, or not the direct application form. Workday pages commonly behave this way; CareerAgent may detect an Apply button or link, but it does not click Workday Apply automatically.

Use `/autofill` -> `Use Local Test Form` to create a fake local application form job at `http://localhost:3000/test-application-form`. For Lever-style long-answer testing, use `http://localhost:3000/test-forms/lever-rd`; it mimics a Baseball Operations R&D Intern form with resume upload, contact fields, technical/statistics textareas, optional EEO fields, future-opportunities consent, and a submit button CareerAgent must never click.

### Fill Application Setup

From the project root:

```bash
docker compose up --build
```

This starts every service in Docker. It is useful for general app development, but the Docker backend cannot open a native macOS Chromium window.

For full local app startup with native Chromium autofill, use:

```bash
./scripts/docker-up-open.sh
```

The script starts only `db` and `frontend` in Docker, runs the backend locally, and opens the app. Plain `docker compose up --build` cannot open a host browser by itself because Compose runs containers, not macOS UI commands.

Manual equivalent:

```bash
docker compose stop backend
docker compose up --build -d db frontend
cd backend
PLAYWRIGHT_HEADLESS=false python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then open `/apply`, click `Start Basic Autofill` or `Start AI-assisted apply`, and review the Chromium window plus field results. CareerAgent keeps final submit blocked; you submit manually.

Verify the Docker backend is ready:

```bash
curl http://localhost:8000/api/autofill/status
```

Expected local visible-autofill fields include `browser_mode: headed`, `visible_autofill_available: true`, `chromium_installed: true`, and `backend_runtime: local`.

If headed mode fails with a “Missing X server” or similar display error, confirm you are running the backend locally on macOS instead of inside Docker.

If Chromium is missing, install it inside the same virtualenv used to start the backend:

```bash
cd backend
source .venv/bin/activate
which python
python -c "import sys; print(sys.executable)"
python -m playwright install chromium
DATABASE_URL="postgresql://careeragent:careeragent@localhost:5432/careeragent" PLAYWRIGHT_HEADLESS=false python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

`playwright_chromium_missing` only means the Playwright browser binaries are missing from the active backend virtualenv. It should not appear for navigation failures, closed browser sessions, HTTP failures, or Workday blocking.

If `/api/autofill/status` still reports `browser_mode: headless`, Docker backend may still be serving port 8000. Check `docker compose ps`; the backend should be stopped, while `db` and `frontend` remain running. If switching jobs fails, refresh the page and confirm the selected job has a direct application URL.

Workday/NVIDIA troubleshooting:

- Workday pages may block Playwright, redirect unexpectedly, or fail with navigation errors such as `net::ERR_HTTP_RESPONSE_CODE_FAILURE`.
- Use `Open in Browser` for Workday if visible autofill returns `workday_manual_required`.
- If a saved Workday URL contains literal `...` or an ellipsis character, re-save or re-import the full job URL before using autofill.
- CareerAgent will not bypass Workday protections, login walls, CAPTCHAs, or anti-bot restrictions.

Switching jobs:

- Closing one visible Chromium session is okay.
- CareerAgent cleans closed sessions before listing sessions and before starting another visible autofill run.
- A new `Fill Application` click starts a clean session for the currently selected job id.

If you are upgrading from an older local database, CareerAgent adds the Stage 3 through Stage 11 job, packet, tracker, autofill, market, AI-supporting, and prediction fields automatically on startup. If you want a clean local reset instead, run:

```bash
docker compose down -v
docker compose up --build
```

### Local Non-Docker Development

Docker Compose is the preferred local setup because it provides PostgreSQL, the backend, the frontend, Playwright dependencies, and the LaTeX packages together. If Docker is unavailable and you run the backend/frontend directly on the host, install backend dependencies in a virtual environment and point both server-side and browser-side frontend requests at the same backend URL:

```bash
cd backend
DATABASE_URL=sqlite:////tmp/careeragent-dev.sqlite ENABLE_SAMPLE_JOBS=true python -m uvicorn main:app --reload

cd ../frontend
API_SERVER_URL=http://127.0.0.1:8000 NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Using `127.0.0.1` avoids local environments where `localhost` resolves differently for server-side fetches. Host-mode SQLite is useful for smoke tests, but PostgreSQL in Docker is the normal app database.

### End-To-End Smoke Test

After the stack is running, a practical trial run is:

1. Open `/profile` and `/resume`; create private files from examples if needed, save, and refresh.
2. Open `/jobs`, discover jobs, review candidates, and save one candidate.
3. Confirm the saved job is automatically verified and scored.
4. Open `/apply?jobId=<id>`.
5. Try AI-assisted apply with AI disabled and confirm the Settings message appears without starting generation.
6. Try AI-assisted apply with MockProvider or a configured provider and confirm a reviewable packet/draft is created.
7. Try Basic Autofill; use `Open in Browser` or `Fill Application` when a visible local backend is available.
8. Manually submit outside CareerAgent, then click `Mark applied`.
9. Confirm the job moves from Saved Jobs to Applied Jobs and appears in `/insights`.

## Optional API Provider Setup

CareerAgent works without any API key using MockProvider.

To enable OpenAI safely for explicit writing/query assists:

1. Copy `.env.example` to `.env`.
2. Set:

```bash
AI_PROVIDER=openai
AI_ALLOW_EXTERNAL_CALLS=true
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

Or select Gemini instead:

```bash
AI_PROVIDER=gemini
AI_ALLOW_EXTERNAL_CALLS=true
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

3. Restart the app.

Important:

- `.env` is gitignored.
- Only the selected `AI_PROVIDER` is used.
- OpenAI and Gemini are not used for parsing, matching, scoring, verification, insights, source discovery, saved-source search, autofill, or applying.
- OpenAI/Gemini calls still require an explicit allowed action in the UI.
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

CareerAgent should preserve the user’s original LaTeX resume structure, section order, commands, formatting, spacing, fonts, margins, and visual style. Tailoring should be content-only unless the user explicitly asks for design changes. AI-assisted tailoring must return a complete LaTeX source, pass structure and unsupported-claim validation, compile successfully, and fall back to deterministic tailoring if validation or compilation fails.

## Primary Usage

1. Open `/profile` and complete your profile, defaults, and resume.
2. Open `/jobs`.
3. Use Discover and Candidates to find reviewable jobs.
4. Save the candidates you want to apply to. CareerAgent automatically verifies and scores saved jobs.
5. Review Saved Jobs. The main action is `Apply`, which opens `/apply?jobId=<id>`.
6. In Apply, choose `Start AI-assisted apply` for AI resume/question help, or `Start Basic Autofill` for profile-based safe autofill without AI writing.
7. Review all drafts and filled fields yourself. CareerAgent never submits.
8. After you manually submit on the employer site, click `Mark applied`.
9. Review Applied Jobs from `/jobs?tab=applied` and outcomes from `/insights`.

AI is optional. If AI is disabled, Apply shows a Settings link and Basic Autofill remains available. Packets are internal application materials, Tracker lives in Insights, Follow-ups are hidden from the primary workflow, and the full job detail page is an advanced secondary view.

## Legacy Stage Usage Notes

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
5. Use `Open in Browser` when you want the safest manual path with tracker logging and no autofill.
6. Use `Fill Application` only when a visible local Playwright browser is available.
7. Use `Use Local Test Form` when you want a safe local form that should detect and fill fields.
8. In Docker/headless mode, `Fill Application` returns `visible_browser_required` instead of running hidden autofill.
9. Run `Advanced diagnostics` -> `Run Headless Field Detection Test` only as a diagnostic. You cannot continue from that hidden session.
10. Treat `no_fields_detected` as an honest warning that CareerAgent opened the page but did not find an application form.
11. Manually click submit only after reviewing the form yourself.
12. Return to CareerAgent and manually mark the job applied from the tracker after you really submit it.

### Stage 9 market analytics workflow

1. Import jobs.
2. Verify and score them so CareerAgent has enough structured data to analyze.
3. Generate packets and track applications when you start applying.
4. Open `/market`.
5. Review the pipeline summary, skill trends, score analytics, outcomes, activity, stale jobs, and insights.
6. Export JSON or CSV if you want to do your own personal analysis outside the app.

### Stage 10 AI workflow

1. Open `/settings`.
2. Confirm the active provider, external AI allow flag, OpenAI status, and Gemini status are shown.
3. Run the provider test form with `mock`; it does not make paid external calls.
4. To use OpenAI, set `AI_PROVIDER=openai`, `AI_ALLOW_EXTERNAL_CALLS=true`, `OPENAI_API_KEY`, and optionally `OPENAI_MODEL` in private `.env`, then restart the app.
5. To use Gemini instead, set `AI_PROVIDER=gemini`, `AI_ALLOW_EXTERNAL_CALLS=true`, `GEMINI_API_KEY`, and optionally `GEMINI_MODEL` in private `.env`, then restart the app.
6. Use optional AI packet drafts or Job Finder keyword help only when you explicitly choose them.
7. Job parsing, matching, scoring, saved-source search, and market insights remain local/rule-based.

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

### Stage 12 job finder workflow

1. Open `/jobs?tab=discover`.
2. Generate rule-based queries or use the default test queries.
3. Select source types such as Greenhouse, Lever, Ashby, Workday, and company career pages.
4. Paste company career URLs, ATS board URLs, or manual job links.
5. Click `Find Jobs` or search saved sources.
6. Review candidates, filter reasons, duplicate markers, and source warnings.
7. Save one candidate or select multiple candidates and click `Save Selected`.
8. CareerAgent automatically verifies and scores saved jobs.
9. Continue from `/apply` with AI-assisted apply or Basic Autofill, then track outcomes in `/insights`.

Stage 12 safety: CareerAgent uses small, source-based fetches with timeouts and a normal user agent, respects `robots.txt` where practical for page fetches, does not use credentials, does not bypass CAPTCHAs/login walls, does not scrape LinkedIn/Indeed automatically, and never submits applications.

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
- Docker cannot open native macOS Chromium windows; local backend execution is the visible-browser path on macOS.
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
- `POST /api/jobs/import`
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
- `POST /api/packets/generate` with optional guarded `use_ai`, `ai_tasks`, and `user_triggered`
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
- Launch headless Chromium only for diagnostics, and headed Chromium for user-continuable visible autofill.
- Keep visible autofill browser sessions open through an in-memory session store.
- List and close active visible sessions from the Autofill UI.
- Detect common application fields.
- Fill high-confidence factual fields.
- Draft/fill common questions when safe.
- Prefer not to answer demographic questions by default.
- Never click submit/apply/final confirmation buttons.
- Log visible autofill start and completion events into the tracker only when the user can continue in the visible browser.
- Show headless field detection only as an advanced diagnostic.

### Stage 9: Market Analytics Dashboard

- Status: Complete
- Show a real analytics dashboard for pipeline, skills, score, verification, outcomes, response rates, activity, stale jobs, and insights.
- Export safe analytics data to JSON and CSV for personal analysis.
- Feed Stage 11 prediction estimates with stored analytics and outcomes.

### Stage 10: AI Provider Integration

- Status: Complete
- Add provider pattern with `MockProvider`, `OpenAIProvider`, and `GeminiProvider`.
- Keep MockProvider available without API keys.
- Use optional AI only for resume tailoring advice, cover letters, recruiter messages, application question drafts, and Job Finder keyword suggestions.
- Keep parsing, matching, scoring, verification, saved-source search, deterministic packet generation, and insights local/rule-based.
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

### Stage 12: Job Finder + Source Discovery

- Status: Source database integration
- Generate rule-based and optional AI-assisted search queries from profile/resume/defaults.
- Import generated source CSV/JSON files from `job-database-script/outputs/source_discovery/`.
- Show saved source counts by ATS type and enabled/valid status.
- Search saved Lever, Greenhouse, Ashby, Workday, company career, or all enabled sources.
- Page first 5 / next 5 candidates from a saved discovery run without refetching sources.
- Discover candidates from Greenhouse, Lever, Ashby, conservative Workday URLs, company career pages, and remote/source URLs.
- Treat LinkedIn and Indeed as pasted/manual links only.
- Store reviewable candidates separately from saved jobs.
- Deduplicate against candidates and saved jobs.
- Filter out or deprioritize senior, staff, principal, manager, PhD-required, Master's-required, 5+ year, and non-Bay-Area roles.
- Import selected candidates into the existing Jobs pipeline for verify, score, packet, tracker, and manual application work.

## Beyond Stage 12

Future stages can refine prediction feedback loops, follow-up planning, ATS coverage, reminder integrations, richer company-source management, and browser-rendered source discovery while keeping CareerAgent human-in-the-loop and safe.

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
