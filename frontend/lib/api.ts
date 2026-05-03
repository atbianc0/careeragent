export type Job = {
  id: number;
  company: string;
  title: string;
  location: string;
  url: string;
  source: string;
  job_description: string;
  posted_date: string | null;
  first_seen_date: string | null;
  last_seen_date: string | null;
  last_checked_date: string | null;
  closed_date: string | null;
  verification_status: string;
  verification_score: number;
  likely_closed_score: number;
  resume_match_score: number;
  freshness_score: number;
  location_score: number;
  application_ease_score: number;
  overall_priority_score: number;
  application_status: string;
  created_at: string;
  updated_at: string;
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
  applications_opened: number;
  packets_ready: number;
  verified_open_jobs: number;
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

export async function getJobs(): Promise<Job[]> {
  return fetchJsonWithFallback<Job[]>("/api/jobs", []);
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
    applications_opened: 0,
    packets_ready: 0,
    verified_open_jobs: 0,
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
