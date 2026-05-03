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
  application_status: string;
  created_at: string;
  updated_at: string;
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
  application_status: string;
  input_type: "description" | "url";
  parse_mode: string;
};

export type JobFilters = {
  status?: string;
  role_category?: string;
  source?: string;
  search?: string;
};

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
  applications_opened: number;
  packets_ready: number;
  verified_open_jobs: number;
  verified_checked_jobs: number;
  open_jobs: number;
  probably_open_jobs: number;
  unknown_jobs: number;
  possibly_closed_jobs: number;
  likely_closed_jobs: number;
  closed_jobs: number;
  risky_jobs: number;
  verification_counts: Record<string, number>;
  average_verification_score: number;
  average_likely_closed_score: number;
  scored_jobs_count: number;
  average_resume_match_score: number;
  average_overall_priority_score: number;
  checked_recently_count: number;
  stale_jobs_count: number;
  recommendation_count: number;
  top_priority_job: TopJobSummary | null;
  top_recommended_jobs: TopJobSummary[];
  top_role_categories: Array<{
    role_category: string;
    average_overall_priority_score: number;
    count: number;
  }>;
  top_requested_skills: Array<{
    skill: string;
    count: number;
  }>;
  top_locations: string[];
  note: string;
};

export type AutofillStatus = {
  status: string;
  message: string;
  manual_review_required: string;
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
    return process.env.API_SERVER_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  }

  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
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
  const response = await fetch(`${getBaseUrl()}${path}`, {
    cache: "no-store",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {})
    }
  });

  const text = await response.text();
  let data: Record<string, unknown> | null = null;

  if (text) {
    try {
      data = JSON.parse(text) as Record<string, unknown>;
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const detail =
      data && typeof data.detail === "string"
        ? data.detail
        : `Request failed with status ${response.status}.`;
    throw new Error(detail);
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

  const query = params.toString();
  return requestJson<Job[]>(`/api/jobs${query ? `?${query}` : ""}`);
}

export async function getJob(id: number | string): Promise<Job> {
  return requestJson<Job>(`/api/jobs/${id}`);
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
    applications_opened: 0,
    packets_ready: 0,
    verified_open_jobs: 0,
    verified_checked_jobs: 0,
    open_jobs: 0,
    probably_open_jobs: 0,
    unknown_jobs: 0,
    possibly_closed_jobs: 0,
    likely_closed_jobs: 0,
    closed_jobs: 0,
    risky_jobs: 0,
    verification_counts: {
      open: 0,
      probably_open: 0,
      unknown: 0,
      possibly_closed: 0,
      likely_closed: 0,
      closed: 0
    },
    average_verification_score: 0,
    average_likely_closed_score: 0,
    scored_jobs_count: 0,
    average_resume_match_score: 0,
    average_overall_priority_score: 0,
    checked_recently_count: 0,
    stale_jobs_count: 0,
    recommendation_count: 0,
    top_priority_job: null,
    top_recommended_jobs: [],
    top_role_categories: [],
    top_requested_skills: [],
    top_locations: [],
    note: "Backend market summary is unavailable."
  });
}

export async function getAutofillStatus(): Promise<AutofillStatus> {
  return fetchJsonWithFallback<AutofillStatus>("/api/autofill/status", {
    status: "planned",
    message:
      "Browser autofill is planned for a later stage. CareerAgent will never click final submit.",
    manual_review_required: "User review and manual submission will always be required."
  });
}
