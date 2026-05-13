export type Job = {
  id: number;
  company: string;
  title: string;
  location: string;
  url: string;
  source: string;
  job_description: string;
  employment_type: string | null;
  remote_status: string | null;
  role_category: string | null;
  seniority_level: string | null;
  years_experience_min: number | null;
  years_experience_max: number | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  required_skills: string[];
  preferred_skills: string[];
  responsibilities: string[];
  requirements: string[];
  education_requirements: string[];
  application_questions: string[];
  raw_parsed_data: Record<string, unknown>;
  verification_evidence: string[];
  verification_raw_data: Record<string, unknown>;
  last_verification_error: string | null;
  posted_date: string | null;
  first_seen_date: string | null;
  last_seen_date: string | null;
  last_checked_date: string | null;
  closed_date: string | null;
  verification_status: string;
  verification_score: number;
  likely_closed_score: number;
  skill_match_score: number;
  role_match_score: number;
  experience_fit_score: number;
  profile_keyword_score: number;
  resume_match_score: number;
  freshness_score: number;
  location_score: number;
  application_ease_score: number;
  overall_priority_score: number;
  scoring_status: string;
  scoring_evidence: Record<string, unknown>;
  scoring_raw_data: Record<string, unknown>;
  scored_at: string | null;
  predicted_priority_score: number;
  predicted_close_risk_score: number;
  predicted_response_score: number;
  prediction_confidence: number;
  prediction_evidence: Record<string, unknown>;
  prediction_updated_at: string | null;
  application_status: string;
  application_link_opened_at: string | null;
  packet_generated_at: string | null;
  applied_at: string | null;
  follow_up_at: string | null;
  interview_at: string | null;
  rejected_at: string | null;
  offer_at: string | null;
  withdrawn_at: string | null;
  closed_before_apply_at: string | null;
  user_notes: string | null;
  next_action: string | null;
  next_action_due_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ApplicationEvent = {
  id: number;
  job_id: number;
  packet_id: number | null;
  event_type: string;
  event_time: string;
  old_status: string | null;
  new_status: string | null;
  notes: string | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  job: {
    id: number;
    company: string;
    title: string;
    application_status: string;
  } | null;
};

export type ApplicationPacket = {
  id: number;
  job_id: number;
  packet_path: string;
  tailored_resume_tex_path: string | null;
  tailored_resume_pdf_path: string | null;
  cover_letter_path: string | null;
  cover_letter_pdf_path: string | null;
  recruiter_message_path: string | null;
  application_questions_path: string | null;
  application_notes_path: string | null;
  change_summary_path: string | null;
  job_summary_path: string | null;
  packet_metadata_path: string | null;
  generation_status: string;
  generation_error: string | null;
  generated_at: string | null;
  created_at: string;
  updated_at: string;
  job: Job | null;
};

export type ApplicationPacketGenerateRequest = {
  job_id: number;
  include_cover_letter: boolean;
  include_recruiter_message: boolean;
  include_application_questions: boolean;
  compile_resume_pdf: boolean;
  use_ai?: boolean;
  ai_tasks?: string[];
  user_triggered?: boolean;
};

export type ApplicationPacketGenerateResponse = {
  packet: ApplicationPacket;
  job: Job;
  message: string;
  compile_resume_pdf_requested: boolean;
  compile_resume_pdf_success: boolean;
  files_created: string[];
  metadata: Record<string, unknown>;
};

export type StartAiAssistedApplyRequest = {
  user_triggered?: boolean;
  include_resume?: boolean;
  include_cover_letter?: boolean;
  include_application_answers?: boolean;
};

export type StartAiAssistedApplyResponse = {
  success: boolean;
  job_id: number;
  packet_id: number;
  packet_status: string;
  ai_used: boolean;
  provider: string | null;
  message: string;
  warnings: string[];
  visible_autofill_available: boolean;
  can_fill_application: boolean;
  browser_mode: "headless" | "headed";
  configured_browser_mode: string;
  setup_instructions?: string[] | null;
  setup_command?: string | null;
  autofill_environment?: AutofillStatus;
  next_actions: string[];
  packet: ApplicationPacket;
  job: Job;
};

export type StartBasicAutofillRequest = {
  user_triggered?: boolean;
  allow_base_resume_upload?: boolean;
  fill_sensitive_optional_fields?: boolean;
};

export type StartBasicAutofillResponse = {
  success: boolean;
  status: string;
  job_id: number;
  job: Job;
  open_url: string;
  packet_id?: number | null;
  packet_status?: string | null;
  upload_status?: string | null;
  visible_autofill_available: boolean;
  browser_mode: "headless" | "headed";
  configured_browser_mode: string;
  can_fill_application: boolean;
  can_open_in_browser: boolean;
  manual_review_required: boolean;
  message: string;
  setup_instructions: string[] | null;
  setup_command?: string | null;
  packet?: ApplicationPacket | null;
  manual_values?: AutofillManualValue[];
  files_available?: string[];
  warnings?: string[];
  next_actions: string[];
};

export type FillApplicationRequest = {
  user_triggered?: boolean;
  packet_id?: number | null;
  allow_base_resume_upload?: boolean;
  fill_sensitive_optional_fields?: boolean;
  keep_browser_open?: boolean;
  ai_assisted_apply?: boolean;
};

export type FillApplicationResponse = AutofillStartResponse & {
  blocked_final_actions?: string[];
  setup_command?: string | null;
  setup_instructions?: string[];
};

export type ApplicationPacketFilePreview = {
  packet_id: number;
  file_key: string;
  path: string;
  content: string;
  format: string;
};

export type JobImportRequest = {
  input_type: "description" | "url";
  content: string;
  source: string;
};

export type JobParseResult = {
  company: string;
  title: string;
  location: string;
  url: string;
  source: string;
  job_description: string;
  employment_type: string | null;
  remote_status: string | null;
  role_category: string | null;
  seniority_level: string | null;
  years_experience_min: number | null;
  years_experience_max: number | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  required_skills: string[];
  preferred_skills: string[];
  responsibilities: string[];
  requirements: string[];
  education_requirements: string[];
  application_questions: string[];
  raw_parsed_data: Record<string, unknown>;
  verification_evidence: string[];
  verification_raw_data: Record<string, unknown>;
  last_verification_error: string | null;
  posted_date: string | null;
  first_seen_date: string | null;
  last_seen_date: string | null;
  last_checked_date: string | null;
  closed_date: string | null;
  verification_status: string;
  verification_score: number;
  likely_closed_score: number;
  skill_match_score: number;
  role_match_score: number;
  experience_fit_score: number;
  profile_keyword_score: number;
  resume_match_score: number;
  freshness_score: number;
  location_score: number;
  application_ease_score: number;
  overall_priority_score: number;
  scoring_status: string;
  scoring_evidence: Record<string, unknown>;
  scoring_raw_data: Record<string, unknown>;
  scored_at: string | null;
  predicted_priority_score: number;
  predicted_close_risk_score: number;
  predicted_response_score: number;
  prediction_confidence: number;
  prediction_evidence: Record<string, unknown>;
  prediction_updated_at: string | null;
  application_status: string;
  input_type: "description" | "url";
  parse_mode: string;
  provider: string | null;
  parsing_status: "full" | "partial";
  parsing_warnings: string[];
};

export type JobFinderSourceStatus = {
  source_type: string;
  label: string;
  implemented: boolean;
  configured: boolean;
  manual_only: boolean;
  notes: string;
};

export type JobFinderStatus = {
  stage: string;
  message: string;
  sources: JobFinderSourceStatus[];
  safety_rules: string[];
};

export type JobFinderQueryResponse = {
  search_profile: Record<string, unknown>;
  queries: string[];
  default_queries: string[];
  warnings: string[];
  api_used?: boolean;
  provider?: string | null;
  api_action?: string | null;
  model?: string | null;
  blocked_reason?: string | null;
};

export type JobFinderRunRequest = {
  source_types: string[];
  queries: string[];
  location: string;
  source_urls: string[];
  manual_links?: string[];
  max_jobs: number;
  use_ai_queries?: boolean;
  auto_verify?: boolean;
  auto_score?: boolean;
  match_mode?: "strict" | "balanced" | "broad";
  target_experience_levels?: string[];
  excluded_experience_levels?: string[];
  degree_filter?: DegreeFilter;
  allow_unknown_location?: boolean;
  location_filter?: LocationFilter;
};

export type DegreeFilter = {
  allow_no_degree: boolean;
  allow_bachelors: boolean;
  allow_masters_preferred: boolean;
  allow_masters_required: boolean;
  allow_phd_preferred: boolean;
  allow_phd_required: boolean;
  allow_unknown: boolean;
};

export type LocationFilter = {
  allow_bay_area: boolean;
  allow_remote_us: boolean;
  allow_unknown: boolean;
  allow_non_bay_area_california: boolean;
  allow_other_us: boolean;
  allow_international: boolean;
};

export type JobCandidate = {
  id: number;
  discovery_run_id: number;
  source_type: string;
  source_name: string | null;
  company: string;
  title: string;
  location: string;
  url: string;
  description_snippet: string | null;
  job_description: string | null;
  role_category: string | null;
  experience_level: string | null;
  seniority_level: string | null;
  level_confidence: number | null;
  location_fit: string | null;
  remote_status: string | null;
  required_skills: string[];
  preferred_skills: string[];
  years_experience_min: number | null;
  years_experience_max: number | null;
  experience_requirement_text: string | null;
  experience_requirement_strength: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  education_requirement: string | null;
  degree_level: string | null;
  degree_requirement_strength: string | null;
  masters_required: boolean;
  phd_required: boolean;
  bachelors_required: boolean;
  degree_requirement_text: string | null;
  metadata_confidence: number | null;
  missing_fields: string[];
  posted_date: string | null;
  discovered_at: string;
  relevance_score: number;
  filter_status: string;
  filter_reasons: string[];
  duplicate_key: string;
  duplicate_of_job_id: number | null;
  imported_job_id: number | null;
  raw_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type JobDiscoveryRun = {
  id: number;
  source_type: string;
  query: string;
  location: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  total_found: number;
  total_candidates: number;
  total_imported: number;
  errors: string[];
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type JobDiscoveryRunDetail = JobDiscoveryRun & {
  candidates: JobCandidate[];
};

export type JobFinderSourceResult = {
  source_url: string;
  source_type: string;
  status: "success" | "warning" | "error" | string;
  found: number;
  jobs_fetched: number;
  saved_candidates: number;
  candidates_saved: number;
  good_match: number;
  weak_match: number;
  excluded: number;
  duplicate: number;
  duplicates: number;
  skipped_incomplete: number;
  warnings: string[];
  errors: string[];
};

export type JobFinderRunResponse = {
  run: JobDiscoveryRun;
  candidates: JobCandidate[];
  summary: Record<string, number>;
  source_results: JobFinderSourceResult[];
  message: string;
  errors: string[];
};

export type JobSource = {
  id: number;
  name: string;
  source_type: string;
  base_url: string;
  normalized_url: string;
  ats_type: string | null;
  enabled: boolean;
  status: string | null;
  jobs_found: number | null;
  last_error: string | null;
  discovery_method: string | null;
  warnings: string[];
  imported_at: string | null;
  last_checked_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type JobSourceSummary = {
  total_sources: number;
  enabled_sources: number;
  valid_sources: number;
  partial_sources: number;
  by_ats_type: Record<string, number>;
  last_imported_at: string | null;
  last_discovery_run_at: string | null;
};

export type JobSourceImportResponse = {
  success: boolean;
  summary: {
    total_read: number;
    created: number;
    updated: number;
    skipped: number;
    invalid: number;
    deleted: number;
    by_ats_type: Record<string, number>;
  };
};

export type SavedSourceSearchRequest = {
  ats_types?: string[];
  source_ids?: number[];
  use_enabled_sources?: boolean;
  limit?: number;
  offset?: number;
  location?: string;
  queries?: string[];
  exclude_duplicates?: boolean;
  exclude_imported?: boolean;
  max_sources?: number;
  match_mode?: "strict" | "balanced" | "broad";
  target_experience_levels?: string[];
  excluded_experience_levels?: string[];
  degree_filter?: DegreeFilter;
  allow_unknown_location?: boolean;
  location_filter?: LocationFilter;
};

export type SavedSourceSearchResult = {
  source_id: number | null;
  company: string | null;
  ats_type: string;
  base_url: string;
  status: string;
  jobs_fetched: number;
  matches: number;
  candidates_saved: number;
  good_match: number;
  weak_match: number;
  excluded: number;
  duplicate: number;
  duplicates: number;
  skipped_incomplete: number;
  warnings: string[];
  errors: string[];
};

export type RunCandidatePage = {
  success: boolean;
  run_id: number;
  limit: number;
  offset: number;
  next_offset: number | null;
  has_more: boolean;
  total_matches: number;
  candidates: JobCandidate[];
};

export type JobFinderSearchDiagnostics = {
  match_mode?: string;
  sources_checked?: number;
  jobs_fetched?: number;
  jobs_excluded?: number;
  excluded_by_experience?: number;
  excluded_by_degree?: number;
  excluded_by_location?: number;
  excluded_by_role?: number;
  excluded_by_low_confidence?: number;
  duplicates?: number;
  incomplete?: number;
  near_match_fallback_used?: boolean;
  bay_area_found?: number;
  remote_us_found?: number;
  unknown_location_found?: number;
  non_bay_area_california_found?: number;
  other_us_found?: number;
  international_found?: number;
  zero_result_diagnostics?: {
    sample_excluded?: Array<{
      company?: string | null;
      title?: string | null;
      location?: string | null;
      role_category?: string | null;
      experience_level?: string | null;
      degree_level?: string | null;
      primary_exclusion_category?: string | null;
      relevance_score?: number | null;
      reasons?: string[];
    }>;
  };
  top_exclusion_reasons?: Array<{ reason: string; count: number }>;
  top_incomplete_reasons?: Array<{ reason: string; count: number }>;
  top_duplicate_reasons?: Array<{ reason: string; count: number }>;
  source_order?: string[];
  suggestions?: string[];
};

export type SavedSourceSearchResponse = RunCandidatePage & {
  summary: Record<string, number>;
  source_results: SavedSourceSearchResult[];
  diagnostics: JobFinderSearchDiagnostics;
};

export type JobCandidateImportResponse = {
  candidate: JobCandidate;
  job: Job;
  verified: boolean;
  scored: boolean;
  warnings: string[];
};

export type JobCandidateImportSelectedResponse = {
  imported_count: number;
  skipped_count: number;
  jobs: Job[];
  errors: string[];
};

export type AIStatus = {
  configured_provider: string;
  active_provider: string;
  openai_available: boolean;
  gemini_available: boolean;
  api_key_present: boolean;
  gemini_key_present: boolean;
  api_key_preview: null;
  safety_mode: boolean;
  message: string;
  ai_allow_external_calls: boolean;
  active_ai_provider: string;
  openai_configured: boolean;
  gemini_configured: boolean;
  both_provider_keys_configured: boolean;
  openai_model: string;
  gemini_model: string;
  current_model: string;
  allowed_ai_actions: string[];
  recent_api_usage: Array<Record<string, unknown>>;
};

export type AIProviderInfo = {
  name: string;
  available: boolean;
  message: string | null;
};

export type AIProvidersResponse = {
  providers: AIProviderInfo[];
};

export type AITestRequest = {
  task: string;
  prompt: string;
  user_enabled?: boolean;
  user_triggered?: boolean;
  max_output_tokens?: number;
};

export type AIProviderResult = {
  provider: string;
  success: boolean;
  task: string;
  content: string;
  parsed_json: Record<string, unknown> | unknown[] | null;
  warnings: string[];
  safety_notes: string[];
  raw: Record<string, unknown> | null;
};

export type JobFilters = {
  status?: string;
  role_category?: string;
  source?: string;
  search?: string;
  saved_only?: boolean;
  applied_only?: boolean;
};

const SAVED_JOB_STATUSES = new Set([
  "saved",
  "ready_to_apply",
  "verified_open",
  "packet_ready",
  "application_opened",
  "applying",
  "autofill_started",
  "autofill_completed",
]);

const APPLIED_JOB_STATUSES = new Set([
  "applied",
  "applied_manual",
  "interview",
  "rejected",
  "offer",
  "withdrawn",
  "closed_after_apply",
]);

function isSavedJob(job: Job) {
  return SAVED_JOB_STATUSES.has(job.application_status) && job.applied_at === null;
}

function isAppliedJob(job: Job) {
  return APPLIED_JOB_STATUSES.has(job.application_status) || job.applied_at !== null;
}

export type RecommendationFilters = {
  limit?: number;
  include_closed?: boolean;
  role_category?: string;
  location?: string;
  status?: string;
};

export type JobVerificationResult = {
  verification_status: string;
  verification_score: number;
  likely_closed_score: number;
  evidence: string[];
  checked_at: string;
  http_status: number | null;
  final_url: string;
  redirected: boolean;
  page_title: string;
  days_since_posted: number | null;
  days_since_first_seen: number | null;
  last_checked_date: string | null;
  last_seen_date: string | null;
  closed_date: string | null;
  freshness_score: number;
  overall_priority_score: number;
  verification_raw_data: Record<string, unknown>;
  last_verification_error: string | null;
};

export type JobVerificationResponse = {
  job: Job;
  verification: JobVerificationResult;
};

export type JobScoreResult = {
  skill_match_score: number;
  role_match_score: number;
  experience_fit_score: number;
  profile_keyword_score: number;
  resume_match_score: number;
  freshness_score: number;
  location_score: number;
  application_ease_score: number;
  verification_score: number;
  overall_priority_score: number;
  scoring_status: string;
  scored_at: string | null;
  evidence: string[];
  scoring_evidence: Record<string, unknown>;
  scoring_raw_data: Record<string, unknown>;
};

export type JobScoringResponse = {
  job: Job;
  score: JobScoreResult;
};

export type TopJobSummary = {
  id: number;
  company: string;
  title: string;
  overall_priority_score: number;
  resume_match_score: number;
  verification_status: string;
};

export type ScoreAllSummary = {
  total_jobs: number;
  scored_count: number;
  skipped_count: number;
  average_resume_match_score: number;
  average_overall_priority_score: number;
  top_jobs: TopJobSummary[];
  errors: string[];
};

export type RecommendationResponse = {
  count: number;
  jobs: Job[];
};

export type VerifyAllSummary = {
  total_jobs: number;
  verified_count: number;
  skipped_count: number;
  open_count: number;
  probably_open_count: number;
  unknown_count: number;
  possibly_closed_count: number;
  likely_closed_count: number;
  closed_count: number;
  errors: string[];
};

export type TrackerSummary = {
  total_jobs: number;
  saved_count: number;
  packet_ready_count: number;
  application_opened_count: number;
  applied_count: number;
  follow_up_count: number;
  interview_count: number;
  rejected_count: number;
  offer_count: number;
  withdrawn_count: number;
  closed_before_apply_count: number;
  counts_by_status: Record<string, number>;
  upcoming_follow_ups: Job[];
  recent_events: ApplicationEvent[];
};

export type TrackerFilters = {
  status?: string;
  search?: string;
};

export type TrackerEventFilters = {
  limit?: number;
  job_id?: number;
  event_type?: string;
};

export type TrackerMutationResponse = {
  job: Job;
  event: ApplicationEvent;
};

export type OpenApplicationResponse = {
  success: boolean;
  job_id: number;
  job: Job;
  event: ApplicationEvent;
  url: string;
  message: string;
};

export type ApplyStartResponse = {
  job: Job;
  message: string;
  manual_review_required?: boolean;
};

export type MarkAppliedResponse = {
  job: Job;
  event: ApplicationEvent;
  message: string;
};

export type ProfileData = {
  personal: {
    name: string;
    email: string;
    phone: string;
    location: string;
  };
  education: {
    school: string;
    degree: string;
    graduation: string;
  };
  links: {
    linkedin: string;
    github: string;
    portfolio: string;
  };
  target_roles: string[];
  skills: string[];
  application_defaults: {
    work_authorized_us: boolean;
    need_sponsorship_now: boolean;
    need_sponsorship_future: boolean;
    willing_to_relocate: boolean;
    preferred_locations: string[];
  };
  question_policy: {
    answer_work_authorization: boolean;
    answer_sponsorship: boolean;
    answer_relocation: boolean;
    answer_salary_expectation: string;
    answer_demographic_questions: string;
    never_lie: boolean;
  };
  writing_style: {
    tone: string;
    avoid: string[];
  };
};

export type ProfileDocument = {
  source: "private" | "example";
  path: string;
  profile: ProfileData;
  message?: string | null;
};

export type ProfileStatus = {
  private_profile_exists: boolean;
  example_profile_exists: boolean;
  active_source: "private" | "example" | "missing";
  private_profile_path: string;
  example_profile_path: string;
  github_safety_note: string;
};

export type MarketSummary = {
  status: string;
  jobs_found: number;
  total_jobs: number;
  verified_jobs: number;
  scored_jobs: number;
  scored_jobs_count: number;
  packets_ready: number;
  packet_ready_jobs: number;
  applications_opened: number;
  application_opened_jobs: number;
  applied_jobs: number;
  interview_jobs: number;
  offer_jobs: number;
  response_rate: number | null;
  average_resume_match_score: number;
  average_overall_priority_score: number;
  average_verification_score: number;
  stale_jobs_count: number;
  top_requested_skills: Array<{
    skill: string;
    count: number;
    required_count?: number;
    preferred_count?: number;
  }>;
  note: string;
};

export type MarketGroupRow = {
  name: string;
  count: number;
  average_resume_match_score: number;
  average_priority_score: number;
  applied_count: number;
  interview_count: number;
};

export type MarketStatusRow = {
  name: string;
  count: number;
};

export type MarketSkillRow = {
  skill: string;
  count: number;
  required_count?: number;
  preferred_count?: number;
  missing_required_count?: number;
  missing_preferred_count?: number;
};

export type MarketJobScoreRow = {
  job_id: number;
  company: string;
  title: string;
  role_category: string;
  resume_match_score: number;
  overall_priority_score: number;
  verification_status: string;
};

export type MarketScoreBucket = {
  bucket: string;
  count: number;
};

export type MarketScoreSummary = {
  average_resume_match_score: number;
  median_resume_match_score: number;
  average_overall_priority_score: number;
  average_skill_match_score: number;
  average_role_match_score: number;
  average_location_score: number;
  top_scored_jobs: MarketJobScoreRow[];
  low_scored_jobs: MarketJobScoreRow[];
  score_distribution: MarketScoreBucket[];
  message: string | null;
};

export type MarketVerificationSummary = {
  average_verification_score: number;
  average_likely_closed_score: number;
  counts_by_verification_status: Record<string, number>;
  jobs_checked_recently: number;
  stale_jobs_count: number;
  likely_closed_jobs_count: number;
  closed_jobs_count: number;
};

export type MarketOutcomeSummary = {
  applied_count: number;
  interview_count: number;
  rejected_count: number;
  offer_count: number;
  follow_up_count: number;
  response_count: number;
  response_rate: number | null;
  interview_rate: number | null;
  offer_rate: number | null;
  message: string | null;
};

export type MarketResponseRateRow = {
  name: string;
  applied_count: number;
  response_count: number;
  response_rate: number | null;
  interview_count: number;
  interview_rate: number | null;
  offer_count: number;
  offer_rate: number | null;
  rejected_count: number;
  sample_size_warning: boolean;
};

export type MarketResponseRates = {
  by_role: MarketResponseRateRow[];
  by_source: MarketResponseRateRow[];
  by_company: MarketResponseRateRow[];
  by_location: MarketResponseRateRow[];
  sample_size_warning: boolean;
  message: string | null;
};

export type MarketActivityPoint = {
  date: string;
  jobs_imported: number;
  jobs_verified: number;
  jobs_scored: number;
  packets_generated: number;
  application_links_opened: number;
  applications_marked_applied: number;
  interviews: number;
  rejections: number;
  offers: number;
};

export type MarketActivity = {
  days: number;
  series: MarketActivityPoint[];
};

export type StaleJob = {
  job_id: number;
  company: string;
  title: string;
  verification_status: string;
  likely_closed_score: number;
  days_since_first_seen: number | null;
  recommendation: string;
};

export type MarketInsight = {
  title: string;
  detail: string;
  category: string;
};

export type PipelineSummary = {
  total_jobs: number;
  verified_jobs: number;
  scored_jobs: number;
  packet_ready_jobs: number;
  application_opened_jobs: number;
  applied_jobs: number;
  follow_up_jobs: number;
  interview_jobs: number;
  rejected_jobs: number;
  offer_jobs: number;
  withdrawn_jobs: number;
  closed_before_apply_jobs: number;
  application_rate: number | null;
  interview_rate: number | null;
  offer_rate: number | null;
  rejection_rate: number | null;
  application_rate_explanation: string | null;
  response_rate_explanation: string | null;
};

export type MarketDashboard = {
  status: string;
  generated_at: string;
  pipeline_summary: PipelineSummary;
  jobs_by_role: MarketGroupRow[];
  jobs_by_company: MarketGroupRow[];
  jobs_by_location: MarketGroupRow[];
  jobs_by_source: MarketGroupRow[];
  jobs_by_verification_status: MarketStatusRow[];
  jobs_by_application_status: MarketStatusRow[];
  skills: {
    requested_skills: MarketSkillRow[];
    missing_skills: MarketSkillRow[];
    message: string | null;
  };
  score_summary: MarketScoreSummary;
  verification_summary: MarketVerificationSummary;
  outcome_summary: MarketOutcomeSummary;
  response_rates: MarketResponseRates;
  activity_over_time: MarketActivity;
  stale_jobs: StaleJob[];
  insights: MarketInsight[];
  export_formats: string[];
  note: string;
};

export type PredictionInsight = {
  title: string;
  detail: string;
  category: string;
  confidence: string;
};

export type PredictionQualityRow = {
  name: string;
  source?: string;
  role_category?: string;
  total_jobs: number;
  applied_jobs: number;
  response_count: number;
  interview_count: number;
  offer_count: number;
  rejected_count: number;
  response_rate: number | null;
  interview_rate: number | null;
  offer_rate: number | null;
  average_priority_score: number;
  average_resume_match_score: number;
  source_quality_score?: number;
  role_quality_score?: number;
  sample_size_warning: boolean;
  evidence: string[];
};

export type PredictionQualityTable = {
  sources?: PredictionQualityRow[];
  roles?: PredictionQualityRow[];
  minimum_meaningful_applied_jobs: number;
  sample_size_warning: boolean;
  message: string | null;
};

export type ApplyWindowEstimate = {
  observed_best_import_days: Array<{ weekday: string; count: number }>;
  observed_best_application_days: Array<{ weekday: string; count: number }>;
  busiest_job_days: Array<{ weekday: string; count: number }>;
  recommended_focus_days: string[];
  confidence: string;
  confidence_score: number;
  based_on: string;
  warning: string | null;
  default_guidance: string[];
  sample_sizes: {
    jobs: number;
    applied_jobs: number;
    response_outcomes: number;
  };
};

export type PredictionJobRow = {
  job_id: number;
  id: number;
  company: string;
  title: string;
  location: string;
  url: string;
  source: string;
  role_category: string;
  application_status: string;
  verification_status: string;
  overall_priority_score: number;
  resume_match_score: number;
  packet_ready: boolean;
  predicted_priority_score: number;
  predicted_close_risk_score: number;
  predicted_response_score: number;
  prediction_confidence: number;
  prediction_confidence_label: string;
  prediction_updated_at: string | null;
  risk_label: string;
  suggested_action: string;
  priority_prediction: Record<string, unknown>;
  close_risk_prediction: Record<string, unknown>;
  response_likelihood_prediction: Record<string, unknown>;
};

export type PredictionDashboard = {
  status: string;
  generated_at: string;
  summary: {
    total_jobs: number;
    scored_jobs: number;
    applied_jobs: number;
    response_count: number;
    average_predicted_priority_score: number;
    high_priority_jobs: number;
    high_close_risk_jobs: number;
    low_confidence_predictions: number;
    best_observed_apply_day: string | null;
    warning: string | null;
  };
  top_priority_jobs: PredictionJobRow[];
  high_close_risk_jobs: PredictionJobRow[];
  response_likelihood_summary: {
    applied_jobs: number;
    response_count: number;
    average_predicted_response_score: number;
    warning: string | null;
  };
  source_quality: PredictionQualityTable;
  role_quality: PredictionQualityTable;
  apply_windows: ApplyWindowEstimate;
  insights: PredictionInsight[];
  export_formats: string[];
  note: string;
};

export type PredictionRecalculateSummary = {
  total_jobs: number;
  updated_jobs: number;
  average_predicted_priority_score: number;
  high_priority_count: number;
  high_close_risk_count: number;
  low_confidence_count: number;
  updated_at: string;
  message: string;
};

export type JobPredictionDetails = {
  job_id: number;
  company: string;
  title: string;
  role_category: string | null;
  source: string;
  application_status: string;
  verification_status: string;
  stored_prediction: {
    predicted_priority_score: number;
    predicted_close_risk_score: number;
    predicted_response_score: number;
    prediction_confidence: number;
    prediction_updated_at: string | null;
    prediction_evidence: Record<string, unknown>;
  };
  priority_prediction: Record<string, unknown>;
  close_risk_prediction: Record<string, unknown>;
  response_likelihood_prediction: Record<string, unknown>;
  note: string;
};

export type PredictionJobFilters = {
  include_closed?: boolean;
  min_confidence?: number;
  role_category?: string;
  source?: string;
};

export type AutofillStatus = {
  status: string;
  stage: string;
  message: string;
  manual_review_required: boolean;
  browser_mode: "headless" | "headed";
  visible_autofill_available: boolean;
  headless_diagnostic_available: boolean;
  can_continue_from_autofill: boolean;
  recommended_user_action: "open_in_browser" | "fill_application";
  active_sessions: AutofillSession[];
  playwright_installed: boolean;
  chromium_installed: boolean;
  headed_browser_supported: boolean;
  headed_display_available: boolean;
  configured_browser_mode: string;
  playwright_headless: boolean;
  playwright_use_xvfb: boolean;
  playwright_slow_mo_ms: number;
  env_file_loaded: boolean;
  env_path: string;
  install_command: string;
  playwright_install_hint: string;
  python_executable: string;
  backend_runtime: "local" | "docker" | "unknown";
  database_host_hint: string;
  environment_note: string;
  recent_sessions: Array<Record<string, unknown>>;
};

export type AutofillSession = {
  session_id: string;
  job_id: number;
  opened_url: string;
  mode: string;
  created_at: string;
};

export type AutofillSessionListResponse = {
  sessions: AutofillSession[];
};

export type AutofillSessionCloseResponse = {
  success: boolean;
  session: Record<string, unknown>;
};

export type AutofillSafety = {
  blocked_final_action_words: string[];
  safety_rules: string[];
};

export type AutofillRequest = {
  job_id: number;
  packet_id?: number | null;
  allow_base_resume_upload?: boolean;
  fill_sensitive_optional_fields?: boolean;
};

export type AutofillManualValue = {
  key: string;
  label: string;
  value: string;
};

export type AutofillFieldResult = {
  field_key: string;
  label: string | null;
  question?: string | null;
  category?: string | null;
  action?: string | null;
  selector: string | null;
  filled: boolean;
  confidence: number;
  value_preview?: string | null;
  value?: string | null;
  reason: string;
  provider?: string | null;
  review_required?: boolean;
};

export type AutofillPreviewResponse = {
  job_id: number;
  packet_id: number | null;
  proposed_values: Record<string, unknown>;
  manual_values: AutofillManualValue[];
  files_available: string[];
  warnings: string[];
  manual_review_required: boolean;
  message: string;
};

export type AutofillStartRequest = AutofillRequest & {
  dry_run?: boolean;
  mode?: "headless_test" | "visible_review";
  keep_browser_open?: boolean;
  keep_open_seconds?: number;
};

export type AutofillStartResponse = {
  success: boolean;
  autofill_effective: boolean;
  can_continue_in_browser: boolean;
  job_id: number;
  packet_id: number | null;
  status: string;
  mode?: string | null;
  session_mode: string;
  session_id?: string | null;
  browser_mode: string;
  opened_url: string;
  fields_detected: number;
  fields_filled: number;
  fields_skipped: number;
  files_uploaded: string[];
  blocked_actions: string[];
  warnings: string[];
  manual_review_required: boolean;
  message: string;
  suggested_fix?: string | null;
  fix_command?: string | null;
  details?: string | null;
  no_fields_reason?: string | null;
  recommended_next_action?: string | null;
  screenshot_path?: string | null;
  screenshot_url?: string | null;
  manual_values: AutofillManualValue[];
  field_results: AutofillFieldResult[];
};

export type ResumeDocument = {
  source: "private" | "example";
  path: string;
  content: string;
  message?: string | null;
};

export type ResumeStatus = {
  private_resume_exists: boolean;
  example_resume_exists: boolean;
  active_source: "private" | "example" | "missing";
  private_resume_path: string;
  example_resume_path: string;
  latex_compiler_available: boolean;
  compiler_name: string | null;
  last_compile_output_path: string | null;
  github_safety_note: string;
};

export type ResumeCompileResult = {
  success: boolean;
  source: "private" | "example" | "missing";
  compiler: string | null;
  input_path: string;
  output_path: string | null;
  message: string;
  logs: string;
};

function getBaseUrl() {
  if (typeof window === "undefined") {
    return (process.env.API_SERVER_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
  }

  const configuredUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  try {
    const parsed = new URL(configuredUrl);
    if (parsed.hostname === "backend" || parsed.hostname === "0.0.0.0") {
      parsed.hostname = "localhost";
      return parsed.toString().replace(/\/$/, "");
    }
  } catch {
    return configuredUrl.replace(/\/$/, "");
  }
  return configuredUrl.replace(/\/$/, "");
}

function formatApiDetail(detail: unknown): string | null {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((entry) => {
        if (entry && typeof entry === "object") {
          const record = entry as Record<string, unknown>;
          const location = Array.isArray(record.loc) ? record.loc.join(".") : "";
          const message = typeof record.msg === "string" ? record.msg : JSON.stringify(record);
          return location ? `${location}: ${message}` : message;
        }
        return String(entry);
      })
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return null;
}

function errorMessageForResponse(method: string, path: string, status: number, data: unknown) {
  const record = data && typeof data === "object" && !Array.isArray(data) ? (data as Record<string, unknown>) : null;
  const detail = formatApiDetail(record?.detail ?? record?.message ?? data);
  const prefix = `${method} ${path} returned ${status}`;
  if (detail) {
    return `${prefix}: ${detail}`;
  }
  if (status === 404) {
    return `${prefix}: Endpoint or resource not found.`;
  }
  if (status === 422) {
    return `${prefix}: Validation failed.`;
  }
  if (status >= 500) {
    return `${prefix}: Backend error.`;
  }
  return `${prefix}: Request failed.`;
}

async function fetchJsonWithFallback<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${getBaseUrl()}${path}`, {
      cache: "no-store"
    });

    if (!response.ok) {
      return fallback;
    }

    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const baseUrl = getBaseUrl();
  const method = (init?.method || "GET").toUpperCase();
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      cache: "no-store",
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {})
      }
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(`Could not reach backend at ${baseUrl} while calling ${method} ${path}. Make sure the backend is running and NEXT_PUBLIC_API_BASE_URL is browser-reachable.`);
    }
    throw error;
  }

  const text = await response.text();
  let data: unknown = null;

  if (text) {
    try {
      data = JSON.parse(text) as unknown;
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    throw new Error(errorMessageForResponse(method, path, response.status, data));
  }

  return data as T;
}

export async function getJobs(filters?: JobFilters): Promise<Job[]> {
  const params = new URLSearchParams();
  if (filters?.status) {
    params.set("status", filters.status);
  }
  if (filters?.role_category) {
    params.set("role_category", filters.role_category);
  }
  if (filters?.source) {
    params.set("source", filters.source);
  }
  if (filters?.search) {
    params.set("search", filters.search);
  }
  if (filters?.saved_only !== undefined) {
    params.set("saved_only", String(filters.saved_only));
  }
  if (filters?.applied_only !== undefined) {
    params.set("applied_only", String(filters.applied_only));
  }

  const query = params.toString();
  return requestJson<Job[]>(`/api/jobs${query ? `?${query}` : ""}`);
}

export async function getJob(id: number | string): Promise<Job> {
  return requestJson<Job>(`/api/jobs/${id}`);
}

export async function getSavedJobs(): Promise<Job[]> {
  const jobs = await getJobs({ saved_only: true });
  return jobs.filter(isSavedJob);
}

export async function getAppliedJobs(): Promise<Job[]> {
  const jobs = await getJobs({ applied_only: true });
  return jobs.filter(isAppliedJob);
}

export async function getJobFinderStatus(): Promise<JobFinderStatus> {
  return requestJson<JobFinderStatus>("/api/job-finder/status");
}

export async function generateJobFinderQueries(payload: { use_ai?: boolean; user_enabled?: boolean; user_triggered?: boolean }): Promise<JobFinderQueryResponse> {
  return requestJson<JobFinderQueryResponse>("/api/job-finder/generate-queries", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function runJobFinder(payload: JobFinderRunRequest): Promise<JobFinderRunResponse> {
  return requestJson<JobFinderRunResponse>("/api/job-finder/run", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function importJobSourceFile(payload: {
  format: "csv" | "json";
  path?: string;
  skip_existing?: boolean;
  replace_existing?: boolean;
}): Promise<JobSourceImportResponse> {
  return requestJson<JobSourceImportResponse>("/api/job-finder/sources/import-file", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getJobSourceSummary(): Promise<JobSourceSummary> {
  return requestJson<JobSourceSummary>("/api/job-finder/sources/summary");
}

export async function getJobSources(filters?: {
  ats_type?: string;
  enabled?: boolean;
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<JobSource[]> {
  const params = new URLSearchParams();
  if (filters?.ats_type) params.set("ats_type", filters.ats_type);
  if (filters?.enabled !== undefined) params.set("enabled", String(filters.enabled));
  if (filters?.status) params.set("status", filters.status);
  if (filters?.search) params.set("search", filters.search);
  if (filters?.limit !== undefined) params.set("limit", String(filters.limit));
  if (filters?.offset !== undefined) params.set("offset", String(filters.offset));
  const query = params.toString();
  return requestJson<JobSource[]>(`/api/job-finder/sources${query ? `?${query}` : ""}`);
}

export async function updateJobSource(sourceId: number | string, payload: {
  enabled?: boolean;
  name?: string;
  company?: string;
  notes?: string;
}): Promise<JobSource> {
  return requestJson<JobSource>(`/api/job-finder/sources/${sourceId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export async function searchSavedJobSources(payload: SavedSourceSearchRequest): Promise<SavedSourceSearchResponse> {
  return requestJson<SavedSourceSearchResponse>("/api/job-finder/sources/search-saved", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getJobFinderRuns(): Promise<JobDiscoveryRun[]> {
  return requestJson<JobDiscoveryRun[]>("/api/job-finder/runs");
}

export async function getJobFinderRun(runId: number | string): Promise<JobDiscoveryRunDetail> {
  return requestJson<JobDiscoveryRunDetail>(`/api/job-finder/runs/${runId}`);
}

export async function getJobFinderRunCandidates(
  runId: number | string,
  filters?: { limit?: number; offset?: number }
): Promise<RunCandidatePage> {
  const params = new URLSearchParams();
  if (filters?.limit !== undefined) params.set("limit", String(filters.limit));
  if (filters?.offset !== undefined) params.set("offset", String(filters.offset));
  const query = params.toString();
  return requestJson<RunCandidatePage>(`/api/job-finder/runs/${runId}/candidates${query ? `?${query}` : ""}`);
}

export async function getJobCandidates(filters?: {
  run_id?: number;
  filter_status?: string;
  source_type?: string;
  search?: string;
  min_relevance_score?: number;
}): Promise<JobCandidate[]> {
  const params = new URLSearchParams();
  if (filters?.run_id) params.set("run_id", String(filters.run_id));
  if (filters?.filter_status) params.set("filter_status", filters.filter_status);
  if (filters?.source_type) params.set("source_type", filters.source_type);
  if (filters?.search) params.set("search", filters.search);
  if (filters?.min_relevance_score !== undefined) params.set("min_relevance_score", String(filters.min_relevance_score));
  const query = params.toString();
  return requestJson<JobCandidate[]>(`/api/job-finder/candidates${query ? `?${query}` : ""}`);
}

export async function importJobCandidate(
  candidateId: number | string,
  options?: { auto_verify?: boolean; auto_score?: boolean }
): Promise<JobCandidateImportResponse> {
  const params = new URLSearchParams();
  if (options?.auto_verify) params.set("auto_verify", "true");
  if (options?.auto_score) params.set("auto_score", "true");
  const query = params.toString();
  return requestJson<JobCandidateImportResponse>(`/api/job-finder/candidates/${candidateId}/import${query ? `?${query}` : ""}`, {
    method: "POST"
  });
}

export async function saveCandidate(candidateId: number | string): Promise<JobCandidateImportResponse> {
  return requestJson<JobCandidateImportResponse>(`/api/job-finder/candidates/${candidateId}/save`, {
    method: "POST"
  });
}

export async function saveSelectedCandidates(candidateIds: number[]): Promise<JobCandidateImportSelectedResponse> {
  return requestJson<JobCandidateImportSelectedResponse>("/api/job-finder/candidates/import-selected", {
    method: "POST",
    body: JSON.stringify({ candidate_ids: candidateIds })
  });
}

export async function importSelectedJobCandidates(payload: {
  candidate_ids: number[];
  auto_verify?: boolean;
  auto_score?: boolean;
}): Promise<JobCandidateImportSelectedResponse> {
  return requestJson<JobCandidateImportSelectedResponse>("/api/job-finder/candidates/import-selected", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getPackets(): Promise<ApplicationPacket[]> {
  return requestJson<ApplicationPacket[]>("/api/packets");
}

export async function getPacket(id: number | string): Promise<ApplicationPacket> {
  return requestJson<ApplicationPacket>(`/api/packets/${id}`);
}

export async function getPacketsForJob(jobId: number | string): Promise<ApplicationPacket[]> {
  return requestJson<ApplicationPacket[]>(`/api/packets/job/${jobId}`);
}

export async function getJobPackets(jobId: number | string): Promise<ApplicationPacket[]> {
  return getPacketsForJob(jobId);
}

export async function generatePacket(payload: ApplicationPacketGenerateRequest): Promise<ApplicationPacketGenerateResponse> {
  return requestJson<ApplicationPacketGenerateResponse>("/api/packets/generate", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getPacketFile(
  packetId: number | string,
  fileKey: string
): Promise<ApplicationPacketFilePreview> {
  const params = new URLSearchParams({ file_key: fileKey });
  return requestJson<ApplicationPacketFilePreview>(`/api/packets/${packetId}/file?${params.toString()}`);
}

export async function getTrackerSummary(): Promise<TrackerSummary> {
  return requestJson<TrackerSummary>("/api/tracker/summary");
}

export async function getTrackerJobs(filters?: TrackerFilters): Promise<Job[]> {
  const params = new URLSearchParams();
  if (filters?.status) {
    params.set("status", filters.status);
  }
  if (filters?.search) {
    params.set("search", filters.search);
  }

  const query = params.toString();
  return requestJson<Job[]>(`/api/tracker/jobs${query ? `?${query}` : ""}`);
}

export async function getJobTimeline(jobId: number | string): Promise<ApplicationEvent[]> {
  return requestJson<ApplicationEvent[]>(`/api/tracker/jobs/${jobId}/timeline`);
}

export async function updateJobStatus(
  jobId: number | string,
  status: string,
  notes?: string
): Promise<TrackerMutationResponse> {
  return requestJson<TrackerMutationResponse>(`/api/tracker/jobs/${jobId}/status`, {
    method: "POST",
    body: JSON.stringify({ status, notes })
  });
}

export async function addJobNote(jobId: number | string, notes: string): Promise<TrackerMutationResponse> {
  return requestJson<TrackerMutationResponse>(`/api/tracker/jobs/${jobId}/note`, {
    method: "POST",
    body: JSON.stringify({ notes })
  });
}

export async function setFollowUp(
  jobId: number | string,
  followUpAt: string,
  notes?: string
): Promise<TrackerMutationResponse> {
  return requestJson<TrackerMutationResponse>(`/api/tracker/jobs/${jobId}/follow-up`, {
    method: "POST",
    body: JSON.stringify({ follow_up_at: followUpAt, notes })
  });
}

export async function completeFollowUp(jobId: number | string, notes?: string): Promise<TrackerMutationResponse> {
  return requestJson<TrackerMutationResponse>(`/api/tracker/jobs/${jobId}/follow-up/complete`, {
    method: "POST",
    body: JSON.stringify({ notes })
  });
}

export async function openApplicationLink(jobId: number | string): Promise<OpenApplicationResponse> {
  return requestJson<OpenApplicationResponse>(`/api/tracker/jobs/${jobId}/open-application`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function openApplication(jobId: number | string): Promise<OpenApplicationResponse> {
  return requestJson<OpenApplicationResponse>(`/api/jobs/${jobId}/open-application`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function getTrackerEvents(filters?: TrackerEventFilters): Promise<ApplicationEvent[]> {
  const params = new URLSearchParams();
  if (filters?.limit !== undefined) {
    params.set("limit", String(filters.limit));
  }
  if (filters?.job_id !== undefined) {
    params.set("job_id", String(filters.job_id));
  }
  if (filters?.event_type) {
    params.set("event_type", filters.event_type);
  }

  const query = params.toString();
  return requestJson<ApplicationEvent[]>(`/api/tracker/events${query ? `?${query}` : ""}`);
}

export async function parseJobImport(payload: JobImportRequest): Promise<JobParseResult> {
  return requestJson<JobParseResult>("/api/jobs/parse", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function importJob(payload: JobImportRequest): Promise<Job> {
  return requestJson<Job>("/api/jobs/import", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function startAiAssistedApply(
  jobId: number | string,
  payload: StartAiAssistedApplyRequest = {},
): Promise<StartAiAssistedApplyResponse> {
  return requestJson<StartAiAssistedApplyResponse>(`/api/jobs/${jobId}/apply/start-ai-assisted`, {
    method: "POST",
    body: JSON.stringify({
      user_triggered: true,
      include_resume: true,
      include_cover_letter: true,
      include_application_answers: true,
      ...payload,
    })
  });
}

export async function startBasicAutofill(
  jobId: number | string,
  payload: StartBasicAutofillRequest = {},
): Promise<StartBasicAutofillResponse> {
  return requestJson<StartBasicAutofillResponse>(`/api/jobs/${jobId}/apply/start-basic-autofill`, {
    method: "POST",
    body: JSON.stringify({
      user_triggered: true,
      allow_base_resume_upload: true,
      fill_sensitive_optional_fields: false,
      ...payload,
    })
  });
}

export async function fillApplication(
  jobId: number | string,
  payload: FillApplicationRequest = {},
): Promise<FillApplicationResponse> {
  return requestJson<FillApplicationResponse>(`/api/jobs/${jobId}/apply/fill-application`, {
    method: "POST",
    body: JSON.stringify({
      user_triggered: true,
      packet_id: null,
      allow_base_resume_upload: true,
      fill_sensitive_optional_fields: false,
      keep_browser_open: true,
      ai_assisted_apply: false,
      ...payload,
    })
  });
}

export async function markJobApplied(jobId: number | string): Promise<MarkAppliedResponse> {
  return requestJson<MarkAppliedResponse>(`/api/jobs/${jobId}/mark-applied`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function getInsightsTrackerSummary(): Promise<TrackerSummary> {
  return getTrackerSummary();
}

export async function updateJob(id: number | string, payload: Partial<Job>): Promise<Job> {
  return requestJson<Job>(`/api/jobs/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export async function deleteJob(id: number | string): Promise<{ status: string; job_id: number }> {
  return requestJson<{ status: string; job_id: number }>(`/api/jobs/${id}`, {
    method: "DELETE"
  });
}

export async function verifyJob(id: number | string): Promise<JobVerificationResponse> {
  return requestJson<JobVerificationResponse>(`/api/jobs/${id}/verify`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function getJobVerification(id: number | string): Promise<JobVerificationResult> {
  return requestJson<JobVerificationResult>(`/api/jobs/${id}/verification`);
}

export async function verifyAllJobs(): Promise<VerifyAllSummary> {
  return requestJson<VerifyAllSummary>("/api/jobs/verify-all", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function verifyRawUrl(url: string): Promise<JobVerificationResult> {
  return requestJson<JobVerificationResult>("/api/jobs/verify-url", {
    method: "POST",
    body: JSON.stringify({ url })
  });
}

export async function scoreJob(id: number | string): Promise<JobScoringResponse> {
  return requestJson<JobScoringResponse>(`/api/jobs/${id}/score`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function getJobScore(id: number | string): Promise<JobScoreResult> {
  return requestJson<JobScoreResult>(`/api/jobs/${id}/score`);
}

export async function scoreAllJobs(): Promise<ScoreAllSummary> {
  return requestJson<ScoreAllSummary>("/api/jobs/score-all", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function getRecommendations(filters?: RecommendationFilters): Promise<RecommendationResponse> {
  const params = new URLSearchParams();
  if (filters?.limit !== undefined) {
    params.set("limit", String(filters.limit));
  }
  if (filters?.include_closed !== undefined) {
    params.set("include_closed", String(filters.include_closed));
  }
  if (filters?.role_category) {
    params.set("role_category", filters.role_category);
  }
  if (filters?.location) {
    params.set("location", filters.location);
  }
  if (filters?.status) {
    params.set("status", filters.status);
  }

  const query = params.toString();
  return requestJson<RecommendationResponse>(`/api/jobs/recommendations${query ? `?${query}` : ""}`);
}

export async function getProfile(): Promise<ProfileDocument> {
  return requestJson<ProfileDocument>("/api/profile");
}

export async function getAIStatus(): Promise<AIStatus> {
  return fetchJsonWithFallback<AIStatus>("/api/ai/status", {
    configured_provider: "mock",
    active_provider: "mock",
    openai_available: false,
    gemini_available: false,
    api_key_present: false,
    gemini_key_present: false,
    api_key_preview: null,
    safety_mode: true,
    message: "External AI calls are disabled unless AI_ALLOW_EXTERNAL_CALLS=true and you explicitly trigger an allowed action.",
    ai_allow_external_calls: false,
    active_ai_provider: "mock",
    openai_configured: false,
    gemini_configured: false,
    both_provider_keys_configured: false,
    openai_model: "gpt-4o-mini",
    gemini_model: "gemini-2.5-flash",
    current_model: "mock",
    allowed_ai_actions: [],
    recent_api_usage: [],
  });
}

export async function getAIProviders(): Promise<AIProvidersResponse> {
  return fetchJsonWithFallback<AIProvidersResponse>("/api/ai/providers", {
    providers: [
      { name: "mock", available: true, message: null },
      { name: "openai", available: false, message: "Unavailable." },
      { name: "gemini", available: false, message: "Unavailable." },
    ],
  });
}

export async function testAIProvider(payload: AITestRequest): Promise<AIProviderResult> {
  return requestJson<AIProviderResult>("/api/ai/test", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getProfileStatus(): Promise<ProfileStatus> {
  return requestJson<ProfileStatus>("/api/profile/status");
}

export async function saveProfile(profile: ProfileData): Promise<ProfileDocument> {
  return requestJson<ProfileDocument>("/api/profile", {
    method: "PUT",
    body: JSON.stringify(profile)
  });
}

export async function createPrivateProfile(): Promise<ProfileDocument> {
  return requestJson<ProfileDocument>("/api/profile/create-private", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function getResume(): Promise<ResumeDocument> {
  return requestJson<ResumeDocument>("/api/resume");
}

export async function getResumeStatus(): Promise<ResumeStatus> {
  return requestJson<ResumeStatus>("/api/resume/status");
}

export async function saveResume(content: string): Promise<ResumeDocument> {
  return requestJson<ResumeDocument>("/api/resume", {
    method: "PUT",
    body: JSON.stringify({ content })
  });
}

export async function createPrivateResume(): Promise<ResumeDocument> {
  return requestJson<ResumeDocument>("/api/resume/create-private", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function compileResume(): Promise<ResumeCompileResult> {
  return requestJson<ResumeCompileResult>("/api/resume/compile", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function getMarketSummary(): Promise<MarketSummary> {
  return fetchJsonWithFallback<MarketSummary>("/api/market/summary", {
    status: "placeholder",
    jobs_found: 0,
    total_jobs: 0,
    verified_jobs: 0,
    scored_jobs: 0,
    scored_jobs_count: 0,
    packets_ready: 0,
    packet_ready_jobs: 0,
    applications_opened: 0,
    application_opened_jobs: 0,
    applied_jobs: 0,
    interview_jobs: 0,
    offer_jobs: 0,
    response_rate: null,
    average_resume_match_score: 0,
    average_overall_priority_score: 0,
    average_verification_score: 0,
    stale_jobs_count: 0,
    top_requested_skills: [],
    note: "Backend market summary is unavailable."
  });
}

export async function getMarketDashboard(): Promise<MarketDashboard> {
  return fetchJsonWithFallback<MarketDashboard>("/api/market/dashboard", {
    status: "placeholder",
    generated_at: "",
    pipeline_summary: {
      total_jobs: 0,
      verified_jobs: 0,
      scored_jobs: 0,
      packet_ready_jobs: 0,
      application_opened_jobs: 0,
      applied_jobs: 0,
      follow_up_jobs: 0,
      interview_jobs: 0,
      rejected_jobs: 0,
      offer_jobs: 0,
      withdrawn_jobs: 0,
      closed_before_apply_jobs: 0,
      application_rate: null,
      interview_rate: null,
      offer_rate: null,
      rejection_rate: null,
      application_rate_explanation: "Import jobs to see pipeline conversion rates.",
      response_rate_explanation: "Mark applications applied to calculate interview, offer, and rejection rates."
    },
    jobs_by_role: [],
    jobs_by_company: [],
    jobs_by_location: [],
    jobs_by_source: [],
    jobs_by_verification_status: [],
    jobs_by_application_status: [],
    skills: {
      requested_skills: [],
      missing_skills: [],
      message: "Import and score more jobs to see skill analytics."
    },
    score_summary: {
      average_resume_match_score: 0,
      median_resume_match_score: 0,
      average_overall_priority_score: 0,
      average_skill_match_score: 0,
      average_role_match_score: 0,
      average_location_score: 0,
      top_scored_jobs: [],
      low_scored_jobs: [],
      score_distribution: [],
      message: "Score jobs to see match analytics."
    },
    verification_summary: {
      average_verification_score: 0,
      average_likely_closed_score: 0,
      counts_by_verification_status: {},
      jobs_checked_recently: 0,
      stale_jobs_count: 0,
      likely_closed_jobs_count: 0,
      closed_jobs_count: 0
    },
    outcome_summary: {
      applied_count: 0,
      interview_count: 0,
      rejected_count: 0,
      offer_count: 0,
      follow_up_count: 0,
      response_count: 0,
      response_rate: null,
      interview_rate: null,
      offer_rate: null,
      message: "Apply to more jobs to calculate meaningful response rates."
    },
    response_rates: {
      by_role: [],
      by_source: [],
      by_company: [],
      by_location: [],
      sample_size_warning: false,
      message: "Response rate needs applied jobs and outcomes."
    },
    activity_over_time: {
      days: 30,
      series: []
    },
    stale_jobs: [],
    insights: [],
    export_formats: ["json", "csv"],
    note: "Import jobs to see market analytics. Prediction estimates are available on the Predictions page."
  });
}

export async function getMarketSkills(): Promise<{
  requested_skills: MarketSkillRow[];
  missing_skills: MarketSkillRow[];
  message: string | null;
}> {
  return requestJson<{
    requested_skills: MarketSkillRow[];
    missing_skills: MarketSkillRow[];
    message: string | null;
  }>("/api/market/skills");
}

export async function getMarketScores(): Promise<MarketScoreSummary> {
  return requestJson<MarketScoreSummary>("/api/market/scores");
}

export async function getMarketOutcomes(): Promise<{
  outcome_summary: MarketOutcomeSummary;
  response_rates: MarketResponseRates;
}> {
  return requestJson<{
    outcome_summary: MarketOutcomeSummary;
    response_rates: MarketResponseRates;
  }>("/api/market/outcomes");
}

export async function getMarketActivity(days = 30): Promise<MarketActivity> {
  const params = new URLSearchParams({ days: String(days) });
  return requestJson<MarketActivity>(`/api/market/activity?${params.toString()}`);
}

export async function getStaleJobs(): Promise<StaleJob[]> {
  return requestJson<StaleJob[]>("/api/market/stale-jobs");
}

export async function getMarketInsights(): Promise<MarketInsight[]> {
  return requestJson<MarketInsight[]>("/api/market/insights");
}

export function getMarketExport(format: "json" | "csv" = "json"): string {
  const params = new URLSearchParams({ format });
  const publicBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  return `${publicBaseUrl}/api/market/export?${params.toString()}`;
}

function predictionDashboardFallback(): PredictionDashboard {
  return {
    status: "placeholder",
    generated_at: "",
    summary: {
      total_jobs: 0,
      scored_jobs: 0,
      applied_jobs: 0,
      response_count: 0,
      average_predicted_priority_score: 0,
      high_priority_jobs: 0,
      high_close_risk_jobs: 0,
      low_confidence_predictions: 0,
      best_observed_apply_day: null,
      warning: "Import and score jobs before predictions become useful.",
    },
    top_priority_jobs: [],
    high_close_risk_jobs: [],
    response_likelihood_summary: {
      applied_jobs: 0,
      response_count: 0,
      average_predicted_response_score: 0,
      warning: "Not enough applied-job history for reliable response estimates.",
    },
    source_quality: {
      sources: [],
      minimum_meaningful_applied_jobs: 3,
      sample_size_warning: false,
      message: "Import jobs before quality estimates become useful.",
    },
    role_quality: {
      roles: [],
      minimum_meaningful_applied_jobs: 3,
      sample_size_warning: false,
      message: "Import jobs before quality estimates become useful.",
    },
    apply_windows: {
      observed_best_import_days: [],
      observed_best_application_days: [],
      busiest_job_days: [],
      recommended_focus_days: ["Monday", "Tuesday", "Wednesday", "Thursday"],
      confidence: "low",
      confidence_score: 0.2,
      based_on: "general_heuristic",
      warning: "Not enough data yet for reliable apply-window estimates.",
      default_guidance: [
        "Apply soon after strong jobs are found.",
        "Prioritize recent, verified-open, high-match jobs.",
        "Review jobs several times per week instead of waiting for one perfect day.",
      ],
      sample_sizes: {
        jobs: 0,
        applied_jobs: 0,
        response_outcomes: 0,
      },
    },
    insights: [],
    export_formats: ["json", "csv"],
    note: "Backend prediction dashboard is unavailable.",
  };
}

export async function getPredictionDashboard(): Promise<PredictionDashboard> {
  return fetchJsonWithFallback<PredictionDashboard>("/api/prediction/dashboard", predictionDashboardFallback());
}

export async function recalculatePredictions(): Promise<PredictionRecalculateSummary> {
  return requestJson<PredictionRecalculateSummary>("/api/prediction/recalculate", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function getPredictionJobs(filters?: PredictionJobFilters): Promise<PredictionJobRow[]> {
  const params = new URLSearchParams();
  if (filters?.include_closed !== undefined) {
    params.set("include_closed", String(filters.include_closed));
  }
  if (filters?.min_confidence !== undefined) {
    params.set("min_confidence", String(filters.min_confidence));
  }
  if (filters?.role_category) {
    params.set("role_category", filters.role_category);
  }
  if (filters?.source) {
    params.set("source", filters.source);
  }

  const query = params.toString();
  return requestJson<PredictionJobRow[]>(`/api/prediction/jobs${query ? `?${query}` : ""}`);
}

export async function getJobPrediction(jobId: number | string): Promise<JobPredictionDetails> {
  return requestJson<JobPredictionDetails>(`/api/prediction/jobs/${jobId}`);
}

export async function getSourceQuality(): Promise<PredictionQualityTable> {
  return requestJson<PredictionQualityTable>("/api/prediction/source-quality");
}

export async function getRoleQuality(): Promise<PredictionQualityTable> {
  return requestJson<PredictionQualityTable>("/api/prediction/role-quality");
}

export async function getApplyWindows(): Promise<ApplyWindowEstimate> {
  return requestJson<ApplyWindowEstimate>("/api/prediction/apply-windows");
}

export async function getPredictionInsights(): Promise<PredictionInsight[]> {
  return requestJson<PredictionInsight[]>("/api/prediction/insights");
}

export function exportPredictionData(format: "json" | "csv" = "json"): string {
  const params = new URLSearchParams({ format });
  const publicBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  return `${publicBaseUrl}/api/prediction/export?${params.toString()}`;
}

export function autofillScreenshotUrl(pathOrUrl: string): string {
  if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
    return pathOrUrl;
  }
  const publicBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  return `${publicBaseUrl}${pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`}`;
}

export async function getAutofillStatus(): Promise<AutofillStatus> {
  return fetchJsonWithFallback<AutofillStatus>("/api/autofill/status", {
    status: "environment_warning",
    stage: "Stage 8 - Browser Autofill with Playwright",
    message:
      "CareerAgent fills safe, high-confidence fields and always stops before final submit.",
    manual_review_required: true,
    browser_mode: "headless",
    visible_autofill_available: false,
    headless_diagnostic_available: false,
    can_continue_from_autofill: false,
    recommended_user_action: "open_in_browser",
    active_sessions: [],
    playwright_installed: false,
    chromium_installed: false,
    headed_browser_supported: false,
    headed_display_available: false,
    configured_browser_mode: "headless",
    playwright_headless: true,
    playwright_use_xvfb: false,
    playwright_slow_mo_ms: 0,
    env_file_loaded: false,
    env_path: "",
    install_command: "python -m playwright install chromium",
    playwright_install_hint: "python -m playwright install chromium",
    python_executable: "unknown",
    backend_runtime: "unknown",
    database_host_hint: "unknown",
    environment_note:
      "Docker defaults to headless Playwright. Run the backend locally outside Docker for visible browser autofill.",
    recent_sessions: []
  });
}

export async function getAutofillSafety(): Promise<AutofillSafety> {
  return fetchJsonWithFallback<AutofillSafety>("/api/autofill/safety", {
    blocked_final_action_words: [],
    safety_rules: []
  });
}

export async function previewAutofill(payload: AutofillRequest): Promise<AutofillPreviewResponse> {
  return requestJson<AutofillPreviewResponse>("/api/autofill/dry-run", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function startAutofill(payload: AutofillStartRequest): Promise<AutofillStartResponse> {
  return requestJson<AutofillStartResponse>("/api/autofill/start", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getAutofillSessions(): Promise<AutofillSession[]> {
  const response = await requestJson<AutofillSessionListResponse>("/api/autofill/sessions");
  return response.sessions;
}

export async function closeAutofillSession(sessionId: string): Promise<AutofillSessionCloseResponse> {
  return requestJson<AutofillSessionCloseResponse>(`/api/autofill/sessions/${sessionId}/close`, {
    method: "POST",
    body: JSON.stringify({})
  });
}
