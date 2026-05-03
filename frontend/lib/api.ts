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

export type Profile = {
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

function getBaseUrl() {
  if (typeof window === "undefined") {
    return process.env.API_SERVER_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  }

  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
}

async function fetchJson<T>(path: string, fallback: T): Promise<T> {
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

export async function getJobs(): Promise<Job[]> {
  return fetchJson<Job[]>("/api/jobs", []);
}

export async function getProfile(): Promise<Profile> {
  return fetchJson<Profile>("/api/profile", {
    personal: { name: "", email: "", phone: "", location: "" },
    education: { school: "UC Berkeley", degree: "Data Science", graduation: "May 2026" },
    links: { linkedin: "", github: "", portfolio: "" },
    target_roles: [
      "Data Scientist",
      "Data Engineer",
      "ML Engineer",
      "Analytics Engineer",
      "Data Analyst"
    ],
    skills: [
      "Python",
      "SQL",
      "Pandas",
      "NumPy",
      "scikit-learn",
      "PyTorch",
      "TensorFlow",
      "Docker",
      "Git",
      "Linux"
    ],
    application_defaults: {
      work_authorized_us: true,
      need_sponsorship_now: false,
      need_sponsorship_future: false,
      willing_to_relocate: true,
      preferred_locations: ["Bay Area", "California", "Remote"]
    },
    question_policy: {
      answer_work_authorization: true,
      answer_sponsorship: true,
      answer_relocation: true,
      answer_salary_expectation: "draft_only",
      answer_demographic_questions: "prefer_not_to_answer",
      never_lie: true
    },
    writing_style: {
      tone: "direct, simple, specific, not overly corporate",
      avoid: ["fake-polished language", "exaggeration", "made-up experience"]
    }
  });
}

export async function getMarketSummary(): Promise<MarketSummary> {
  return fetchJson<MarketSummary>("/api/market/summary", {
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
  return fetchJson<AutofillStatus>("/api/autofill/status", {
    status: "planned",
    message:
      "Browser autofill is planned for a later stage. CareerAgent will never click final submit.",
    manual_review_required: "User review and manual submission will always be required."
  });
}

