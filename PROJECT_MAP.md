# CareerAgent Project Map

## 1. Project Overview

CareerAgent is a customizable, human-in-the-loop job search assistant. It helps a user manage their profile and resume, discover jobs from a saved source database, review and import candidate jobs, verify and score saved jobs, generate application packets, track application status, and safely assist with browser autofill while always stopping before final submission.

Core product areas:

- Profile and resume management from private local files under `data/`.
- Job discovery from saved ATS/company sources and manually supplied links.
- Saved jobs pipeline with parsing, verification, scoring, recommendations, and predictions.
- Application packet generation with tailored resume source, cover letter, recruiter message, application answers, notes, summaries, and metadata.
- Tracker for application events, statuses, follow-ups, interviews, rejections, offers, and notes.
- Autofill/manual application flow using Playwright when available, with final submit/apply actions blocked.
- Insights, market analytics, cautious predictions, source quality, role quality, and settings.

## 2. High-Level Architecture

```text
CareerAgent
+-- Frontend: Next.js
|   +-- frontend/app routes
|   |   +-- dashboard, profile, jobs, applications, insights, settings
|   |   +-- legacy/direct pages for resume, tracker, packets, autofill, market, predictions, ai
|   +-- frontend/components
|   |   +-- managers for jobs, job finder, profile, resume, autofill, tracker, AI
|   |   +-- shared tables, cards, nav, tracking actions
|   +-- frontend/lib/api.ts
|       +-- typed API client for FastAPI endpoints
+-- Backend: FastAPI
|   +-- backend/main.py
|   |   +-- app setup, CORS, DB init, route registration
|   +-- backend/app/api/routes
|   |   +-- HTTP routes grouped by feature
|   +-- backend/app/services
|   |   +-- business logic for jobs, discovery, packets, tracker, autofill, AI, analytics
|   +-- backend/app/models
|   |   +-- SQLAlchemy tables
|   +-- backend/app/schemas
|   |   +-- Pydantic request/response models
|   +-- backend/app/db
|       +-- SQLAlchemy engine/session, table creation, lightweight column sync
+-- Database: PostgreSQL
|   +-- jobs
|   +-- job_candidates
|   +-- job_sources
|   +-- job_discovery_runs
|   +-- application_events
|   +-- application_packets
+-- Generated/local files
|   +-- data/
|   |   +-- profile.yaml
|   |   +-- resume/base_resume.tex
|   +-- outputs/
|   |   +-- application_packets/
|   |   +-- autofill_screenshots/
|   |   +-- resume/
|   +-- job-database-script/
|       +-- generated ATS sources
|       +-- CSV/JSON source discovery outputs
```

## 3. Current App Route Map

- `/`
  - Main command center dashboard.
  - Shows saved jobs, waiting candidates, scored jobs, packet readiness, applications opened, and recommended next actions.

- `/profile`
  - Profile workspace with tabs for profile, resume, application defaults, and writing style.
  - Uses `ProfileEditor` and `ResumeEditor`.

- `/jobs`
  - Saved jobs pipeline.
  - Tabs: Discover, Candidates, Saved Jobs, Recommended, Manual Import.
  - Uses `JobFinderManager` for discovery/candidates and `JobsManager` for saved/recommended/manual import.
  - Discover supports Strict, Balanced, and Broad saved-source match modes, first-5/next-5 run paging, source result diagnostics, higher-quality ATS ordering before Workday, and pre-search fit filters for experience level and degree requirement.
  - Candidate results show detected experience level, years/strength when available, detected degree requirement, match reasons, and import actions.

- `/jobs/[id]`
  - Job detail page.
  - Shows parsed job data, verification/scoring/prediction details, packet actions, tracker timeline, and autofill controls.

- `/applications`
  - Unified applications workspace.
  - Tabs: Tracker, Packets, Autofill, Follow-ups.
  - Uses `TrackerBoard` and `AutofillManager`; links to packet library.

- `/insights`
  - Consolidated insight workspace.
  - Tabs: Market, Predictions, Skills, Sources.
  - Provides summaries and links to full market and predictions pages.

- `/settings`
  - Settings workspace.
  - Tabs: AI Provider, Environment, Safety, Data/GitHub Safety.
  - Shows AI provider state, autofill health, source database health, resume compiler status, and private-data guardrails.

- `/resume`
  - Legacy/direct route that redirects to `/profile?tab=resume`.

- `/job-finder`
  - Legacy/direct route that redirects to `/jobs?tab=discover`.

- `/tracker`
  - Direct tracker page with tracker board and links to market, predictions, AI settings, and autofill.
  - The newer unified entry point is `/applications`.

- `/packets`
  - Packet library page.
  - Lists generated application packets and links to packet details/autofill.

- `/packets/[id]`
  - Packet detail page.
  - Previews generated files, packet metadata, safety notes, and autofill controls for the associated job.

- `/autofill`
  - Direct autofill page.
  - Shows available autofill modes and safe fill actions for a selected job.

- `/market`
  - Full market analytics page.
  - Breaks down pipeline, scores, outcomes, skills, response rates, activity, stale jobs, insights, and exports.

- `/predictions`
  - Full prediction dashboard.
  - Recalculates and displays priority, close risk, response likelihood, source quality, role quality, and apply-window estimates.

- `/ai`
  - Legacy/direct route that redirects to `/settings`.

- `/test-application-form`
  - Local fake application form for autofill testing.
  - Includes safe fields, sensitive optional EEO fields, dangerous fields, file uploads, and a submit button that should never be clicked by CareerAgent.

## 4. Backend API Route Map

- `backend/app/api/routes/health.py`
  - `GET /health`
  - Basic health check.

- `backend/app/api/routes/ai.py`
  - Mounted at `/api/ai`.
  - Provider status, provider list, and provider test endpoint.

- `backend/app/api/routes/profile.py`
  - Mounted at `/api/profile`.
  - Load/save profile YAML, create private profile from example, and profile status.

- `backend/app/api/routes/resume.py`
  - Mounted at `/api/resume`.
  - Load/save resume LaTeX, create private resume from example, compile resume, and resume status.

- `backend/app/api/routes/jobs.py`
  - Mounted at `/api/jobs`.
  - Job list/detail/update/delete, parse/import, raw URL verification, verify all/single, score all/single, and recommendations.

- `backend/app/api/routes/job_finder.py`
  - Mounted at `/api/job-finder`.
  - Job Finder status, query generation, source CSV/JSON import, source summary/list/update, saved-source search, discovery runs, candidates, candidate exclusion, and candidate import.
  - Saved-source and manual discovery requests accept `target_experience_levels`, `excluded_experience_levels`, `degree_filter`, and `match_mode`.

- `backend/app/api/routes/tracker.py`
  - Mounted at `/api/tracker`.
  - Tracker summary, tracked jobs, job timeline, status changes, notes, follow-ups, open-application logging, and recent events.

- `backend/app/api/routes/packets.py`
  - Mounted at `/api/packets`.
  - Generate packets, list packets, list packets for a job, read packet details, and preview individual generated files.

- `backend/app/api/routes/market.py`
  - Mounted at `/api/market`.
  - Market dashboard, summary, skills, scores, outcomes, activity, stale jobs, insights, and JSON/CSV exports.

- `backend/app/api/routes/prediction.py`
  - Mounted at `/api/prediction`.
  - Prediction dashboard, recalculate, job predictions, source quality, role quality, apply windows, insights, and JSON/CSV exports.

- `backend/app/api/routes/autofill.py`
  - Mounted at `/api/autofill`.
  - Autofill status, safety rules, sessions, screenshots, dry-run preview, visible/headless autofill start, session close, and cleanup.

## 5. Services Map

### Jobs

- `backend/app/services/jobs/parser.py`
  - Parses pasted job descriptions or fetched job URLs, including Workday URL inference, embedded metadata extraction, skills, salary, experience, responsibilities, requirements, and optional AI parsing.

- `backend/app/services/jobs/job_store.py`
  - Creates, lists, updates, deletes, and recommends saved `Job` records; provides placeholder freshness/priority helpers.

### Job Finder

- `backend/app/services/job_finder/discovery.py`
  - Orchestrates source discovery, saved-source search, run/candidate persistence, filtering, dedupe, and importing candidates into saved jobs.
  - Saved-source search prioritizes Lever, Greenhouse, Ashby, company career pages, then Workday; records per-source counts plus no-result diagnostics for exclusions, duplicates, incomplete postings, and primary experience/degree/location/role/low-confidence exclusion buckets.
  - If a saved-source run fetches jobs but no normal candidates survive, it promotes the best non-hard-excluded soft matches as weak near matches with an explicit fallback reason and includes sample excluded jobs when true zero-result runs remain.
  - Candidate import preserves Job Finder fit metadata, match reasons, role category, experience details, degree details, and full description in saved job metadata when no first-class job column exists.

- `backend/app/services/job_finder/source_database_importer.py`
  - Imports generated source CSV/JSON files into the `job_sources` table, normalizes URLs, infers ATS type, blocks disallowed hosts, and summarizes import results.

- `backend/app/services/job_finder/job_normalizer.py`
  - Converts raw source results into normalized candidate fields with company/title/location/role/location fit metadata plus experience and degree requirement metadata.

- `backend/app/services/job_finder/dedupe.py`
  - Normalizes URLs and checks candidates against existing candidates and saved jobs.

- `backend/app/services/job_finder/filters.py`
  - Filters/classifies candidates for target roles, selected experience levels, Bay Area/remote fit, selected degree requirements, and Strict/Balanced/Broad Job Finder match modes.
  - Strict honors fit filters tightly; Balanced hard-excludes only clear disqualifiers while keeping unknowns, adjacent technical roles, outside-target US locations, and 3-5 year stretch roles as weak matches; Broad honors hard disqualifiers while allowing more reviewable stretch roles.
  - Filter results carry hard/soft exclusion metadata, primary exclusion category, broad-match eligibility, and all reasons for diagnostics/fallback.

- `backend/app/services/job_finder/query_builder.py`
  - Builds a search profile from profile/resume data and generates rule-based or optional AI-assisted queries.

- `backend/app/services/job_finder/role_classifier.py`
  - Classifies role category from title/description, including strong data/ML/analytics targets and adjacent technical roles such as software, backend, platform, infrastructure, AI/data solutions, technical analyst, and quantitative analyst.

- `backend/app/services/job_finder/level_classifier.py`
  - Classifies experience level and year requirements from title and description, including internship, new-grad/entry, early-career, mid-level, senior, unknown, years min/max, strength, signals, and reasons.
  - Also classifies degree requirements into none mentioned, bachelor's, master's, PhD, unknown, with required/preferred/equivalent-experience strength and strict master's/PhD required flags; degree exclusions are limited to clear Master’s-required or PhD-required conflicts.

- `backend/app/services/job_finder/location_classifier.py`
  - Classifies Bay Area, remote US, hybrid, outside target, or unknown location fit.

### Job Finder Source Connectors

- `backend/app/services/job_finder/sources/common.py`
  - Shared HTTP, robots, text cleanup, URL, company inference, and candidate-building helpers.

- `backend/app/services/job_finder/sources/lever.py`
  - Fetches Lever board postings.

- `backend/app/services/job_finder/sources/greenhouse.py`
  - Fetches Greenhouse board postings with HTML fallback.

- `backend/app/services/job_finder/sources/ashby.py`
  - Fetches Ashby postings with HTML extraction.

- `backend/app/services/job_finder/sources/workday.py`
  - Uses conservative Workday metadata/API fallback and URL inference.

- `backend/app/services/job_finder/sources/company_careers.py`
  - Scans company career pages for ATS/job links with a small link budget.

- `backend/app/services/job_finder/sources/remote_boards.py`
  - Delegates generic remote/source board URLs through company career discovery.

- `backend/app/services/job_finder/sources/manual_links.py`
  - Handles manually pasted links, especially LinkedIn/Indeed-style sources, without automated scraping.

- `backend/app/services/job_finder/sources/web_search.py`
  - Placeholder for future configured web-search provider.

- `backend/app/services/job_finder/sources/github_lists.py`
  - Placeholder for future GitHub company-list source integration.

### Verification, Scoring, Predictions, Analytics

- `backend/app/services/verifier/verifier.py`
  - Fetches job pages and infers open/closed/blocked/possibly closed status from apply signals, closed signals, redirects, and evidence.

- `backend/app/services/scoring/scoring.py`
  - Scores jobs against profile/resume for skill, role, location, experience, freshness, application ease, resume match, and overall priority.

- `backend/app/services/prediction/prediction.py`
  - Estimates priority, close risk, response likelihood, source quality, role quality, apply windows, confidence, and prediction exports.

- `backend/app/services/market/analytics.py`
  - Builds pipeline summaries, breakdowns, skills, score analytics, outcome metrics, activity timelines, stale-job recommendations, insights, and safe exports.

### Packet Generation

- `backend/app/services/generator/packet_generator.py`
  - Generates a packet folder and database record for a job, writes all packet files, compiles resume PDF when requested, logs tracker events, and promotes job status.

- `backend/app/services/generator/cover_letter.py`
  - Deterministic cover letter draft.

- `backend/app/services/generator/recruiter_message.py`
  - Deterministic recruiter outreach draft.

- `backend/app/services/generator/application_questions.py`
  - Conservative draft answers for common application questions.

- `backend/app/services/generator/application_notes.py`
  - Internal notes and recommended review points.

- `backend/app/services/generator/change_summary.py`
  - Summarizes resume tailoring changes.

- `backend/app/services/generator/common.py`
  - Shared profile, skill, label, and writing-style helpers.

- `backend/app/services/generator/mock_generator.py`
  - Older placeholder generator helpers.

### Resume and Profile

- `backend/app/services/profile/profile_store.py`
  - Loads/saves `data/profile.yaml`, creates it from `data/profile.example.yaml`, and reports GitHub safety status.

- `backend/app/services/resume/latex_resume.py`
  - Loads/saves `data/resume/base_resume.tex`, creates it from example, finds LaTeX compilers, compiles PDFs, and reports resume safety/status.

- `backend/app/services/resume/tailor_resume.py`
  - Produces minimal tailored LaTeX resume source changes while preserving structure.

### Autofill / Browser Agent

- `backend/app/services/browser_agent/autofill.py`
  - Builds safe autofill values from profile/job/packet, detects environment support, opens Playwright sessions, fills safe fields, uploads files when possible, blocks final actions, captures diagnostics, and logs tracker events.

- `backend/app/services/browser_agent/field_detector.py`
  - Detects and classifies application form fields with confidence and sensitivity flags.

- `backend/app/services/browser_agent/safe_actions.py`
  - Detects blocked final submit/apply/confirm action text.

- `backend/app/services/browser_agent/session_store.py`
  - Tracks visible/headless autofill session summaries and active sessions in memory.

### AI

- `backend/app/services/ai/base.py`
  - Abstract AI provider interface.

- `backend/app/services/ai/mock_provider.py`
  - Offline deterministic/mock provider for testable drafts.

- `backend/app/services/ai/openai_provider.py`
  - Optional OpenAI-backed provider.

- `backend/app/services/ai/local_provider.py`
  - Placeholder local LLM provider.

- `backend/app/services/ai/provider_factory.py`
  - Normalizes provider names and returns active/provider availability.

- `backend/app/services/ai/prompts.py`
  - Prompt builders for job parsing, resume tailoring, packet drafts, and market insights.

- `backend/app/services/ai/safety.py`
  - Sanitizes AI output, detects risky claims, and adds review-required notices.

## 6. Database / Model Map

- `Job` in `backend/app/models/job.py`
  - Table: `jobs`.
  - Main saved job/application pipeline record.
  - Stores source info, parsed job fields, verification, scoring, predictions, application status timestamps, notes, and next actions.
  - Relationships: `Job.events` and `Job.packets`.

- `JobSource` in `backend/app/models/job_finder.py`
  - Table: `job_sources`.
  - Saved ATS/company board source imported from generated CSV/JSON or managed in app.
  - Used by saved-source searches and discovery runs.

- `JobDiscoveryRun` in `backend/app/models/job_finder.py`
  - Table: `job_discovery_runs`.
  - One discovery/search run with source type, query, location, totals, errors, and metadata.
  - Relationship: `JobDiscoveryRun.candidates`.

- `JobCandidate` in `backend/app/models/job_finder.py`
  - Table: `job_candidates`.
  - Reviewable discovered job before import.
  - Links to a discovery run, may mark duplicates against saved jobs, and may link to an imported `Job`.

- `ApplicationPacket` in `backend/app/models/application_packet.py`
  - Table: `application_packets`.
  - Generated packet record for a saved job.
  - Stores file paths, generation status/error, timestamps, and links back to the job and packet-related events.

- `ApplicationEvent` in `backend/app/models/application_event.py`
  - Table: `application_events`.
  - Tracker timeline event for a job, optionally tied to a packet.
  - Stores event type, time, old/new status, notes, and metadata.

Model relationships:

```text
JobSource
  -> used by saved-source searches and discovery runs to fetch postings

JobDiscoveryRun
  -> owns many JobCandidate records

JobCandidate
  -> reviewable discovered job
  -> can point to duplicate_of_job_id or imported_job_id in jobs

Job
  -> saved job in application pipeline
  -> owns ApplicationPacket records
  -> owns ApplicationEvent tracker timeline

ApplicationPacket
  -> generated materials for one Job
  -> can be referenced by ApplicationEvent

ApplicationEvent
  -> status/action/note/follow-up/autofill/packet timeline entry for one Job
```

Profile and resume data are not SQLAlchemy models in this codebase. They are local files managed by services:

- `data/profile.yaml`
- `data/resume/base_resume.tex`

## 7. Data Flow Diagrams

### A. Job Discovery Flow

```text
Source CSV/JSON or saved sources
  -> JobSource table
  -> Search saved sources
  -> Fetch ATS/company jobs
  -> Normalize raw postings
  -> Filter/classify/dedupe
  -> JobCandidate
  -> User reviews candidates
  -> Import selected
  -> Job
```

### B. Application Flow

```text
Job
  -> Verify availability
  -> Score fit/priority
  -> Generate application packet
  -> Open in browser or Fill Application
  -> User manually reviews
  -> User manually submits
  -> Mark applied
  -> Tracker timeline
```

### C. Autofill Flow

```text
Selected Job + Packet
  -> Open in Browser or Fill Application
  -> Playwright visible browser if available
  -> Detect fields
  -> Fill only safe, high-confidence fields
  -> Upload generated files when safe/available
  -> Final submit/apply/confirm blocked
  -> User manually completes/submits
```

### D. Source Discovery Script Flow

```text
job-database-script
  -> seed files / pasted results / company career pages / helper scrapers
  -> normalize ATS board URLs
  -> test sources
  -> store in local SQLite job_sources.db when requested
  -> export CSV/JSON
  -> import into CareerAgent via /api/job-finder/sources/import-file
```

## 8. File / Folder Inventory

### Root

- `README.md`
  - Main project description, stage notes, features, setup, safety boundaries, and workflow.

- `.env.example`
  - Public environment variable template.

- `.gitignore`
  - Ignores private profile/resume files, environment files, generated outputs, local DB files, caches, virtualenvs, Node build artifacts, and PDFs.

- `docker-compose.yml`
  - Runs PostgreSQL, FastAPI backend, and Next.js frontend for local development.

- `PROJECT_MAP.md`
  - This handoff map.

### Backend

- `backend/main.py`
  - FastAPI app entrypoint, lifespan DB init, CORS, and router registration.

- `backend/Dockerfile`
  - Backend container image.

- `backend/requirements.txt`
  - FastAPI, SQLAlchemy, PostgreSQL driver, PyYAML, requests, BeautifulSoup, Playwright, and OpenAI dependencies.

- `backend/app/core/config.py`
  - Environment-backed settings, project/data/output path resolution, database URL, AI settings, and Playwright settings.

- `backend/app/db/database.py`
  - SQLAlchemy engine/session/base, `init_db`, table creation, lightweight schema sync/backfills, and sample-job normalization.

- `backend/app/api/routes/`
  - FastAPI route modules for `health`, `ai`, `profile`, `resume`, `jobs`, `job_finder`, `tracker`, `packets`, `market`, `prediction`, and `autofill`.

- `backend/app/models/`
  - SQLAlchemy models for jobs, discovery sources/runs/candidates, packets, and application events.

- `backend/app/schemas/`
  - Pydantic schemas used by API routes and frontend API typing.

- `backend/app/services/jobs/`
  - Job parsing and saved job persistence/recommendation logic.

- `backend/app/services/job_finder/`
  - Source-based discovery, source import, normalizers, filters, classifiers, dedupe, and connectors.

- `backend/app/services/generator/`
  - Packet generation and deterministic draft material creation.

- `backend/app/services/tracker/`
  - Application status transitions, event logging, follow-ups, and tracker summaries.

- `backend/app/services/browser_agent/`
  - Playwright/browser autofill, field detection, safe-action blocking, and session summaries.

- `backend/app/services/scoring/`
  - Profile/resume/job fit and priority scoring.

- `backend/app/services/verifier/`
  - Job page availability verification.

- `backend/app/services/market/`
  - Market analytics, insights, and safe exports.

- `backend/app/services/prediction/`
  - Prediction estimates, quality summaries, apply windows, and exports.

- `backend/app/services/ai/`
  - AI provider abstraction, OpenAI/mock/local providers, prompts, and safety checks.

- `backend/app/services/profile/`
  - Profile YAML load/save/status helpers.

- `backend/app/services/resume/`
  - Resume LaTeX load/save/compile/tailor helpers.

- `backend/app/utils/text.py`
  - Shared text normalization utility.

- `backend/scripts/job_finder_quality_checks.py`
  - Internal quality-check script for Job Finder behavior.

### Frontend

- `frontend/package.json`
  - Next.js app scripts and dependencies.

- `frontend/next.config.js`
  - Next.js config.

- `frontend/tsconfig.json`
  - TypeScript config.

- `frontend/Dockerfile`
  - Frontend container image.

- `frontend/app/layout.tsx`
  - Root layout and navigation shell.

- `frontend/app/globals.css`
  - Global app styling.

- `frontend/app/page.tsx`
  - Home dashboard.

- `frontend/app/profile/page.tsx`
  - Profile/resume/settings tabs for user context.

- `frontend/app/jobs/page.tsx`
  - Job discovery, candidates, saved jobs, recommendations, and manual import tabs.

- `frontend/app/jobs/[id]/page.tsx`
  - Saved job detail page.

- `frontend/app/applications/page.tsx`
  - Unified tracker, packet, autofill, and follow-up workspace.

- `frontend/app/insights/page.tsx`
  - Unified market/prediction/skills/source insight workspace.

- `frontend/app/settings/page.tsx`
  - AI, environment, safety, and data/privacy settings workspace.

- `frontend/app/resume/page.tsx`
  - Redirects to `/profile?tab=resume`.

- `frontend/app/job-finder/page.tsx`
  - Redirects to `/jobs?tab=discover`.

- `frontend/app/tracker/page.tsx`
  - Direct tracker page.

- `frontend/app/packets/page.tsx`
  - Packet library page.

- `frontend/app/packets/[id]/page.tsx`
  - Packet detail and file-preview page.

- `frontend/app/autofill/page.tsx`
  - Direct autofill page.

- `frontend/app/market/page.tsx`
  - Full market analytics page.

- `frontend/app/predictions/page.tsx`
  - Full client-side predictions page.

- `frontend/app/ai/page.tsx`
  - Redirects to `/settings`.

- `frontend/app/test-application-form/page.tsx`
  - Local fake application form for autofill testing.

- `frontend/components/NavBar.tsx`
  - Main navigation and route-group active state.

- `frontend/components/StatCard.tsx`
  - Shared summary card.

- `frontend/components/ProfileEditor.tsx`
  - Profile YAML-backed editor.

- `frontend/components/ResumeEditor.tsx`
  - Resume LaTeX editor/compile UI.

- `frontend/components/JobsManager.tsx`
  - Saved/recommended/manual job UI with parse/import/verify/score actions.

- `frontend/components/JobFinderManager.tsx`
  - Job Finder UI for source import, saved-source search, discovery, candidate review, and candidate import.

- `frontend/components/JobTable.tsx`
  - Shared job table.

- `frontend/components/JobDetailView.tsx`
  - Job detail UI with scoring, verification, prediction, packets, timeline, and autofill.

- `frontend/components/TrackerBoard.tsx`
  - Tracker dashboard grouped by application status.

- `frontend/components/TrackingActions.tsx`
  - Status, note, follow-up, and open-application actions.

- `frontend/components/AutofillManager.tsx`
  - Autofill page orchestration and local test form handling.

- `frontend/components/AutofillControls.tsx`
  - Per-job autofill/open-in-browser controls, dry-run/manual values, visible setup hints, and session closing.

- `frontend/components/AIManager.tsx`
  - AI provider status and test UI.

- `frontend/lib/api.ts`
  - Typed frontend API client for all backend feature areas.

### Job Database Script

- `job-database-script/README.md`
  - Source discovery script documentation and command examples.

- `job-database-script/requirements.txt`
  - Script dependencies.

- `job-database-script/Dockerfile`
  - Script container image.

- `job-database-script/docker-compose.yml`
  - Script-local compose setup.

- `job-database-script/run_all.sh`
  - End-to-end source discovery pipeline runner.

- `job-database-script/scripts/discover_job_sources.py`
  - Main source discovery CLI: reads seed/pasted/career inputs, normalizes URLs, tests sources, stores to DB, and exports CSV/JSON.

- `job-database-script/scripts/generate_google_queries.py`
  - Generates manual Google search queries.

- `job-database-script/scripts/scrape_ddg_startups.py`
  - Uses DuckDuckGo search to find startup ATS boards.

- `job-database-script/scripts/scrape_google_for_ats.py`
  - Direct Google scraper helper; README warns it may be rate-limited.

- `job-database-script/scripts/mine_github_repos.py`
  - Mines public GitHub repositories for ATS links.

- `job-database-script/scripts/mine_hacker_news.py`
  - Mines Hacker News "Who is hiring" threads for source links.

- `job-database-script/scripts/mine_vc_portfolios.py`
  - Mines VC/startup portfolio sources.

- `job-database-script/scripts/fetch_wikipedia_companies.py`
  - Builds large company-name inputs.

- `job-database-script/scripts/generate_from_company_names.py`
  - Generates ATS URL guesses/permutations from company names.

- `job-database-script/scripts/find_big_tech_boards.py`
  - Uses DuckDuckGo to find exact career pages for larger companies.

- `job-database-script/scripts/reverify_db.py`
  - Retests existing local source DB records.

- `job-database-script/backend/app/services/job_finder/source_normalizer.py`
  - Detects ATS type and normalizes raw board URLs.

- `job-database-script/backend/app/services/job_finder/source_tester.py`
  - Tests whether a normalized source appears valid and has jobs.

- `job-database-script/backend/app/models/job_source.py`
  - Script-local SQLAlchemy `JobSource` model.

- `job-database-script/backend/app/database.py`
  - Script-local SQLite database setup.

- `job-database-script/data/source_seeds/`
  - Input seed files for ATS sources, company career pages, and pasted search results.

- `job-database-script/data/company_names.txt`
  - Company-name input list.

- `job-database-script/data/startup_names.txt`
  - Startup-name input list.

- `job-database-script/outputs/source_discovery/`
  - Generated source CSV/JSON output location when present.

### Data and Outputs

- `data/profile.example.yaml`
  - Safe public profile template.

- `data/profile.yaml`
  - Private local profile file. Do not commit.

- `data/resume/base_resume.example.tex`
  - Safe public resume template.

- `data/resume/base_resume.tex`
  - Private local resume source. Do not commit.

- `outputs/application_packets/`
  - Generated per-job packet folders. Do not commit.

- `outputs/autofill_screenshots/`
  - Autofill diagnostics/screenshots. Do not commit.

- `outputs/resume/`
  - Generated resume PDFs/build artifacts. Do not commit.

## 9. Git / Privacy Notes

Do not commit:

- `.env` or `.env.*` private environment files.
- API keys, tokens, credentials, secrets, `.pem`, `.key`, or similar files.
- `data/profile.yaml`.
- `data/resume/base_resume.tex`.
- `outputs/`.
- Generated PDFs.
- Application packets.
- Autofill screenshots.
- Private resumes, profile data, notes, generated application answers, cover letters, or packet metadata.
- Local database files such as `*.db`, `*.sqlite`, and `job_sources.db`.
- Source-discovery outputs if they are private/generated and gitignored.
- `node_modules/`, `.next/`, `__pycache__/`, `.venv/`, and other build/cache folders.

Safe examples/templates:

- `.env.example`
- `data/profile.example.yaml`
- `data/resume/base_resume.example.tex`

## 10. Known Limitations / TODOs

- Workday support can be partial because many Workday pages are JavaScript-heavy and may only yield URL-inferred metadata.
- LinkedIn and Indeed are manual pasted-link sources only; CareerAgent should not automatically scrape them.
- Google search should not be scraped automatically in the main app. The source script includes manual query helpers and experimental/direct helpers with rate-limit caveats.
- Visible autofill requires a local backend/browser environment with `PLAYWRIGHT_HEADLESS=false` and an available display; Docker defaults are typically headless diagnostics.
- CareerAgent never clicks final submit/apply/confirm/send buttons. The user must manually review and submit.
- Source database quality depends on generated/imported CSV/JSON quality and source testing results.
- Job title, description, company, location, salary, skills, and application questions depend on ATS extraction quality.
- Some company pages block simple HTTP requests, require browser rendering, or expose limited metadata.
- Prediction estimates are cautious and low-confidence when there is little application/outcome history.
- AI usage is optional; mock provider keeps the app usable without API keys.

## 11. How To Use This File

Use `PROJECT_MAP.md` as a compact handoff before asking ChatGPT, Codex, or a human developer to work on CareerAgent. It gives them the main architecture, current route names, backend route ownership, service responsibilities, data models, critical workflows, and private-data boundaries without exposing secrets or private resume/profile contents.

This file is intended as a quick project context handoff for ChatGPT, Codex, or human developers.
