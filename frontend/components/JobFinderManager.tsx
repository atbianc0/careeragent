"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  type JobCandidate,
  type JobDiscoveryRun,
  type JobSource,
  type JobSourceSummary,
  type JobFinderSourceResult,
  type JobFinderSearchDiagnostics,
  type SavedSourceSearchResult,
  type JobFinderStatus,
  type DegreeFilter,
  type LocationFilter,
  generateJobFinderQueries,
  getJobCandidates,
  getJobFinderRuns,
  getJobFinderRunCandidates,
  getJobFinderStatus,
  getJobSources,
  getJobSourceSummary,
  importJobSourceFile,
  saveCandidate,
  saveSelectedCandidates,
  runJobFinder,
  searchSavedJobSources,
  updateJobSource,
} from "@/lib/api";

const DEFAULT_SOURCES = ["greenhouse", "lever", "ashby", "workday", "company_careers"];
const MATCH_MODES = [
  { key: "strict", label: "Strict Match", detail: "Clear role and target location." },
  { key: "balanced", label: "Balanced Match", detail: "Default: role or strong skill/title signal." },
  { key: "broad", label: "Broad Match", detail: "Looser review queue when sources return little." },
] as const;
const EXPERIENCE_OPTIONS = [
  { key: "internship", label: "Internship" },
  { key: "new_grad_entry", label: "New Grad / Entry Level" },
  { key: "early_career", label: "Early Career / 0-2 years" },
  { key: "mid_level", label: "Mid-Level / 2-5 years" },
  { key: "senior", label: "Senior / 5+ years" },
  { key: "unknown", label: "Unknown level" },
] as const;
const DEFAULT_EXPERIENCE_LEVELS = ["new_grad_entry", "early_career", "unknown"];
const DEFAULT_DEGREE_FILTER: DegreeFilter = {
  allow_no_degree: true,
  allow_bachelors: true,
  allow_masters_preferred: true,
  allow_masters_required: false,
  allow_phd_preferred: true,
  allow_phd_required: false,
  allow_unknown: true,
};
const DEFAULT_LOCATION_FILTER: LocationFilter = {
  allow_bay_area: true,
  allow_remote_us: true,
  allow_unknown: true,
  allow_non_bay_area_california: false,
  allow_other_us: false,
  allow_international: false,
};
const LOCATION_OPTIONS: Array<{ key: keyof LocationFilter; label: string; fit: string }> = [
  { key: "allow_bay_area", label: "Bay Area", fit: "bay_area" },
  { key: "allow_remote_us", label: "Remote US", fit: "remote_us" },
  { key: "allow_unknown", label: "Unknown location", fit: "unknown" },
  { key: "allow_non_bay_area_california", label: "Non-Bay Area California", fit: "non_bay_area_california" },
  { key: "allow_other_us", label: "Other US", fit: "other_us" },
  { key: "allow_international", label: "International", fit: "international" },
];
const DEGREE_OPTIONS: Array<{ key: keyof DegreeFilter; label: string }> = [
  { key: "allow_no_degree", label: "No degree mentioned" },
  { key: "allow_bachelors", label: "Bachelor's required/accepted" },
  { key: "allow_masters_preferred", label: "Master's preferred" },
  { key: "allow_masters_required", label: "Master's required" },
  { key: "allow_phd_preferred", label: "PhD preferred" },
  { key: "allow_phd_required", label: "PhD required" },
  { key: "allow_unknown", label: "Unknown degree requirement" },
];
const DEFAULT_QUERIES = [
  "data scientist",
  "data engineer",
  "machine learning engineer",
  "ml engineer",
  "ai engineer",
  "analytics engineer",
  "data analyst",
  "product analyst",
  "business intelligence analyst",
  "software engineer data",
  "software engineer machine learning",
  "software engineer ai",
  "research engineer",
  "applied scientist",
  "applied ai engineer",
  "new grad",
  "entry level",
  "early career",
  "bay area",
  "remote us",
];
const EXAMPLE_SOURCES = {
  lever: "https://jobs.lever.co/zoox",
  greenhouse: "https://boards.greenhouse.io/databricks",
  workday: "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
};

function lines(value: string) {
  return value.split("\n").map((line) => line.trim()).filter(Boolean);
}

function looksLikePlaceholder(url: string) {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    const path = parsed.pathname.toLowerCase().replace(/\/+$/, "");
    return (
      host === "company.com" ||
      host === "www.company.com" ||
      (host === "jobs.lever.co" && path === "/company") ||
      (host === "boards.greenhouse.io" && path === "/company") ||
      path.includes("[company]")
    );
  } catch {
    return false;
  }
}

function validateUrls(values: string[]) {
  const invalid: string[] = [];
  const placeholders: string[] = [];
  const valid: string[] = [];

  for (const value of values) {
    try {
      const parsed = new URL(value);
      if (!["http:", "https:"].includes(parsed.protocol)) {
        invalid.push(value);
      } else if (looksLikePlaceholder(value)) {
        placeholders.push(value);
      } else {
        valid.push(value);
      }
    } catch {
      invalid.push(value);
    }
  }

  return { valid, invalid, placeholders };
}

function sourceStatusClass(status: string) {
  if (status === "error") {
    return "status-tag status-possibly-closed";
  }
  if (status === "warning") {
    return "status-tag status-medium";
  }
  return "status-tag status-open";
}

function candidateStatusClass(status: string) {
  if (status === "good_match") {
    return "status-tag status-open";
  }
  if (status === "weak_match") {
    return "status-tag status-medium";
  }
  if (status === "duplicate" || status === "excluded" || status === "incomplete") {
    return "status-tag status-unknown";
  }
  return "status-tag";
}

function levelLabel(level?: string | null) {
  if (level === "intern" || level === "internship") return "Intern";
  if (level === "new_grad_entry") return "New Grad / Entry";
  if (level === "early_career") return "Early Career";
  if (level === "mid_level") return "Mid-Level";
  if (level === "advanced_senior" || level === "senior") return "Senior / Advanced";
  return "Unknown";
}

function strengthLabel(value?: string | null) {
  if (value === "nice_to_have") return "Nice to have";
  if (value === "minimum") return "Minimum";
  if (value === "preferred") return "Preferred";
  if (value === "required") return "Required";
  if (value === "equivalent_experience") return "Equivalent experience";
  if (value === "accepted") return "Accepted";
  return "Unclear";
}

function experienceDisplay(candidate: JobCandidate) {
  const min = candidate.years_experience_min;
  const max = candidate.years_experience_max;
  const strength = strengthLabel(candidate.experience_requirement_strength).toLowerCase();
  if (min !== null && max !== null) return `${min}-${max} yrs ${strength}`;
  if (min !== null) return `${min}+ yrs ${strength}`;
  return levelLabel(candidate.experience_level);
}

function degreeDisplay(candidate: JobCandidate) {
  if (candidate.phd_required) return "PhD required";
  if (candidate.masters_required) return "Master's required";
  if (candidate.degree_level === "phd" && candidate.degree_requirement_strength === "preferred") return "PhD preferred";
  if (candidate.degree_level === "masters" && candidate.degree_requirement_strength === "preferred") return "Master's preferred";
  if (candidate.degree_level === "bachelors" && candidate.degree_requirement_strength === "equivalent_experience") return "Bachelor's / equivalent";
  if (candidate.degree_level === "bachelors") return "Bachelor's accepted";
  if (candidate.degree_level === "none_mentioned") return "Not mentioned";
  return "Unknown";
}

function candidateDescription(candidate: JobCandidate) {
  return (candidate.job_description || candidate.description_snippet || "").trim();
}

function sameSet(left: string[], right: string[]) {
  return [...left].sort().join("|") === [...right].sort().join("|");
}

function degreeFilterEquals(left: DegreeFilter, right: DegreeFilter) {
  return DEGREE_OPTIONS.every((option) => left[option.key] === right[option.key]);
}

function locationFilterEquals(left: LocationFilter, right: LocationFilter) {
  return LOCATION_OPTIONS.every((option) => left[option.key] === right[option.key]);
}

function experienceSummary(levels: string[]) {
  const labels = EXPERIENCE_OPTIONS.filter((option) => levels.includes(option.key)).map((option) => option.label.replace(" / Entry Level", " / Entry"));
  return labels.length > 0 ? labels.join(", ") : "Default target restored before search";
}

function degreeSummary(filter: DegreeFilter) {
  if (degreeFilterEquals(filter, DEFAULT_DEGREE_FILTER)) {
    return "Bachelor's-friendly, excludes Master's required and PhD required";
  }
  const labels = DEGREE_OPTIONS.filter((option) => filter[option.key]).map((option) => option.label);
  return labels.length > 0 ? labels.join(", ") : "Default Bachelor's-friendly restored before search";
}

function locationSummary(filter: LocationFilter) {
  const labels = LOCATION_OPTIONS.filter((option) => filter[option.key]).map((option) => option.label);
  return labels.length > 0 ? labels.join(", ") : "Default Bay Area target restored before search";
}

function locationFitLabel(fit?: string | null) {
  if (fit === "bay_area") return "Bay Area";
  if (fit === "remote_us") return "Remote US";
  if (fit === "non_bay_area_california") return "California";
  if (fit === "other_us") return "Other US";
  if (fit === "international") return "International";
  return "Unknown";
}

function runFitSummary(run: JobDiscoveryRun) {
  const metadata = run.metadata_json || {};
  const matchMode = typeof metadata.match_mode === "string" ? metadata.match_mode : "balanced";
  const maxSources = typeof metadata.max_sources === "number" ? metadata.max_sources : null;
  const experienceLevels = Array.isArray(metadata.target_experience_levels)
    ? metadata.target_experience_levels.filter((item): item is string => typeof item === "string")
    : [];
  const degreeFilter = metadata.degree_filter && typeof metadata.degree_filter === "object"
    ? { ...DEFAULT_DEGREE_FILTER, ...(metadata.degree_filter as Partial<DegreeFilter>) }
    : DEFAULT_DEGREE_FILTER;
  const savedLocationFilter = metadata.location_filter && typeof metadata.location_filter === "object"
    ? { ...DEFAULT_LOCATION_FILTER, ...(metadata.location_filter as Partial<LocationFilter>) }
    : DEFAULT_LOCATION_FILTER;
  return `${matchMode} - ${experienceSummary(experienceLevels)} - ${degreeSummary(degreeFilter)} - ${locationSummary(savedLocationFilter)}${maxSources ? ` - max sources ${maxSources}` : ""}`;
}

function savedSourceDetailsSummary(results: SavedSourceSearchResult[]) {
  const sources = results.length;
  const fetched = results.reduce((total, result) => total + result.jobs_fetched, 0);
  const matches = results.reduce((total, result) => total + result.matches, 0);
  const warnings = results.reduce((total, result) => total + result.warnings.length + result.errors.length, 0);
  return `${sources} sources checked, ${fetched.toLocaleString()} jobs fetched, ${matches} matches, ${warnings} warnings/errors`;
}

export function JobFinderManager() {
  const [status, setStatus] = useState<JobFinderStatus | null>(null);
  const [runs, setRuns] = useState<JobDiscoveryRun[]>([]);
  const [queries, setQueries] = useState("");
  const [sourceTypes, setSourceTypes] = useState<string[]>(DEFAULT_SOURCES);
  const [sourceUrls, setSourceUrls] = useState("");
  const [manualLinks, setManualLinks] = useState("");
  const [location, setLocation] = useState("Bay Area");
  const [maxJobs, setMaxJobs] = useState(50);
  const [maxSources, setMaxSources] = useState(25);
  const [matchMode, setMatchMode] = useState<"strict" | "balanced" | "broad">("balanced");
  const [targetExperienceLevels, setTargetExperienceLevels] = useState<string[]>(DEFAULT_EXPERIENCE_LEVELS);
  const [degreeFilter, setDegreeFilter] = useState<DegreeFilter>(DEFAULT_DEGREE_FILTER);
  const [locationFilter, setLocationFilter] = useState<LocationFilter>(DEFAULT_LOCATION_FILTER);
  const [sourceSummary, setSourceSummary] = useState<JobSourceSummary | null>(null);
  const [savedSources, setSavedSources] = useState<JobSource[]>([]);
  const [candidates, setCandidates] = useState<JobCandidate[]>([]);
  const [summary, setSummary] = useState<Record<string, number>>({});
  const [sourceResults, setSourceResults] = useState<JobFinderSourceResult[]>([]);
  const [savedSourceResults, setSavedSourceResults] = useState<SavedSourceSearchResult[]>([]);
  const [diagnostics, setDiagnostics] = useState<JobFinderSearchDiagnostics | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [currentRunId, setCurrentRunId] = useState<number | null>(null);
  const [resultOffset, setResultOffset] = useState(0);
  const [resultLimit, setResultLimit] = useState(5);
  const [totalMatches, setTotalMatches] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [showAllCandidates, setShowAllCandidates] = useState(false);
  const [showSourceDetails, setShowSourceDetails] = useState(false);
  const [aiQueryAssistEnabled, setAiQueryAssistEnabled] = useState(false);
  const [sourceRequired, setSourceRequired] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const sourceLabels = useMemo(() => {
    const labels = new Map<string, string>();
    for (const source of status?.sources || []) {
      labels.set(source.source_type, source.label);
    }
    return labels;
  }, [status]);

  async function loadInitial() {
    try {
      const [statusResponse, runsResponse, sourceSummaryResponse, savedSourcesResponse] = await Promise.all([
        getJobFinderStatus(),
        getJobFinderRuns(),
        getJobSourceSummary(),
        getJobSources({ limit: 20 }),
      ]);
      setStatus(statusResponse);
      setRuns(runsResponse);
      setSourceSummary(sourceSummaryResponse);
      setSavedSources(savedSourcesResponse);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load Job Finder.");
    }
  }

  useEffect(() => {
    void loadInitial();
  }, []);

  async function refreshRuns() {
    const runsResponse = await getJobFinderRuns();
    setRuns(runsResponse);
  }

  async function refreshSourceDatabase() {
    const [sourceSummaryResponse, savedSourcesResponse] = await Promise.all([
      getJobSourceSummary(),
      getJobSources({ limit: 20 }),
    ]);
    setSourceSummary(sourceSummaryResponse);
    setSavedSources(savedSourcesResponse);
  }

  async function loadCandidateView(runId: number | null, showAll: boolean) {
    if (showAll) {
      const allCandidates = await getJobCandidates();
      setCandidates(allCandidates);
      setTotalMatches(allCandidates.length);
      setResultOffset(0);
      setHasMore(false);
      return;
    }
    if (runId !== null) {
      const page = await getJobFinderRunCandidates(runId, { limit: 5, offset: 0 });
      setCandidates(page.candidates);
      setTotalMatches(page.total_matches);
      setResultOffset(page.offset);
      setResultLimit(page.limit);
      setHasMore(page.has_more);
      return;
    }
    setCandidates([]);
    setTotalMatches(0);
    setResultOffset(0);
    setHasMore(false);
  }

  function toggleSource(sourceType: string) {
    setSourceTypes((current) =>
      current.includes(sourceType) ? current.filter((item) => item !== sourceType) : [...current, sourceType],
    );
  }

  function toggleExperienceLevel(level: string) {
    setTargetExperienceLevels((current) =>
      current.includes(level) ? current.filter((item) => item !== level) : [...current, level],
    );
  }

  function setExperiencePreset(preset: "target" | "internships" | "mid" | "non-senior" | "any") {
    if (preset === "target") setTargetExperienceLevels(DEFAULT_EXPERIENCE_LEVELS);
    if (preset === "internships") setTargetExperienceLevels(["internship", "new_grad_entry", "early_career", "unknown"]);
    if (preset === "mid") setTargetExperienceLevels(["new_grad_entry", "early_career", "mid_level", "unknown"]);
    if (preset === "non-senior") setTargetExperienceLevels(["internship", "new_grad_entry", "early_career", "mid_level", "unknown"]);
    if (preset === "any") setTargetExperienceLevels(EXPERIENCE_OPTIONS.map((option) => option.key));
  }

  function activeExperiencePreset(preset: "target" | "internships" | "mid" | "non-senior" | "any") {
    if (preset === "target") return sameSet(targetExperienceLevels, DEFAULT_EXPERIENCE_LEVELS);
    if (preset === "internships") return sameSet(targetExperienceLevels, ["internship", "new_grad_entry", "early_career", "unknown"]);
    if (preset === "mid") return sameSet(targetExperienceLevels, ["new_grad_entry", "early_career", "mid_level", "unknown"]);
    if (preset === "non-senior") return sameSet(targetExperienceLevels, ["internship", "new_grad_entry", "early_career", "mid_level", "unknown"]);
    return sameSet(targetExperienceLevels, EXPERIENCE_OPTIONS.map((option) => option.key));
  }

  function setDegreePreset(preset: "bachelors" | "exclude-grad" | "masters" | "phd" | "any") {
    if (preset === "bachelors" || preset === "exclude-grad") setDegreeFilter(DEFAULT_DEGREE_FILTER);
    if (preset === "masters") setDegreeFilter({ ...DEFAULT_DEGREE_FILTER, allow_masters_required: true });
    if (preset === "phd") setDegreeFilter({ ...DEFAULT_DEGREE_FILTER, allow_masters_required: true, allow_phd_required: true });
    if (preset === "any") {
      setDegreeFilter({
        allow_no_degree: true,
        allow_bachelors: true,
        allow_masters_preferred: true,
        allow_masters_required: true,
        allow_phd_preferred: true,
        allow_phd_required: true,
        allow_unknown: true,
      });
    }
  }

  function setLocationPreset(preset: "bay-area" | "california" | "us-wide" | "any") {
    if (preset === "bay-area") setLocationFilter(DEFAULT_LOCATION_FILTER);
    if (preset === "california") {
      setLocationFilter({
        allow_bay_area: true,
        allow_remote_us: true,
        allow_unknown: true,
        allow_non_bay_area_california: true,
        allow_other_us: false,
        allow_international: false,
      });
    }
    if (preset === "us-wide") {
      setLocationFilter({
        allow_bay_area: true,
        allow_remote_us: true,
        allow_unknown: true,
        allow_non_bay_area_california: true,
        allow_other_us: true,
        allow_international: false,
      });
    }
    if (preset === "any") {
      setLocationFilter({
        allow_bay_area: true,
        allow_remote_us: true,
        allow_unknown: true,
        allow_non_bay_area_california: true,
        allow_other_us: true,
        allow_international: true,
      });
    }
  }

  function activeDegreePreset(preset: "bachelors" | "exclude-grad" | "masters" | "phd" | "any") {
    if (preset === "bachelors" || preset === "exclude-grad") return degreeFilterEquals(degreeFilter, DEFAULT_DEGREE_FILTER);
    if (preset === "masters") return degreeFilterEquals(degreeFilter, { ...DEFAULT_DEGREE_FILTER, allow_masters_required: true });
    if (preset === "phd") return degreeFilterEquals(degreeFilter, { ...DEFAULT_DEGREE_FILTER, allow_masters_required: true, allow_phd_required: true });
    return DEGREE_OPTIONS.every((option) => degreeFilter[option.key]);
  }

  function activeLocationPreset(preset: "bay-area" | "california" | "us-wide" | "any") {
    if (preset === "bay-area") return locationFilterEquals(locationFilter, DEFAULT_LOCATION_FILTER);
    if (preset === "california") {
      return locationFilterEquals(locationFilter, {
        allow_bay_area: true,
        allow_remote_us: true,
        allow_unknown: true,
        allow_non_bay_area_california: true,
        allow_other_us: false,
        allow_international: false,
      });
    }
    if (preset === "us-wide") {
      return locationFilterEquals(locationFilter, {
        allow_bay_area: true,
        allow_remote_us: true,
        allow_unknown: true,
        allow_non_bay_area_california: true,
        allow_other_us: true,
        allow_international: false,
      });
    }
    return LOCATION_OPTIONS.every((option) => locationFilter[option.key]);
  }

  function excludedExperienceLevels() {
    return targetExperienceLevels.includes("senior") ? [] : ["senior"];
  }

  function requestExperienceLevels() {
    if (targetExperienceLevels.length > 0) {
      return targetExperienceLevels;
    }
    setTargetExperienceLevels(DEFAULT_EXPERIENCE_LEVELS);
    setMessage("Experience filters were empty, so CareerAgent restored the default target levels.");
    return DEFAULT_EXPERIENCE_LEVELS;
  }

  function requestDegreeFilter() {
    if (DEGREE_OPTIONS.some((option) => degreeFilter[option.key])) {
      return degreeFilter;
    }
    setDegreeFilter(DEFAULT_DEGREE_FILTER);
    setMessage("Degree filters were empty, so CareerAgent restored the Bachelor's-friendly default.");
    return DEFAULT_DEGREE_FILTER;
  }

  function requestLocationFilter() {
    if (LOCATION_OPTIONS.some((option) => locationFilter[option.key])) {
      return locationFilter;
    }
    setLocationFilter(DEFAULT_LOCATION_FILTER);
    setMessage("Location filters were empty, so CareerAgent restored the Bay Area target default.");
    return DEFAULT_LOCATION_FILTER;
  }

  function ensureSourceType(sourceType: string) {
    setSourceTypes((current) => (current.includes(sourceType) ? current : [...current, sourceType]));
  }

  function useDefaultQueries() {
    setQueries(DEFAULT_QUERIES.join("\n"));
    setMessage("Broad default Job Finder keywords loaded.");
    setError(null);
  }

  function useMyDefaultSearch() {
    setLocation("Bay Area");
    setSourceTypes(DEFAULT_SOURCES);
    setExperiencePreset("target");
    setDegreePreset("bachelors");
    setLocationPreset("bay-area");
    setQueries(DEFAULT_QUERIES.join("\n"));
    setMessage("Default search loaded: Bay Area, early-career data/ML roles, and source-based ATS discovery.");
    setError(null);
  }

  function useExampleSource(sourceType: "lever" | "greenhouse" | "workday") {
    setSourceUrls(EXAMPLE_SOURCES[sourceType]);
    ensureSourceType(sourceType);
    setSourceRequired(false);
    setMessage(
      sourceType === "workday"
        ? "Workday example loaded. It may return partial results because Workday pages are JavaScript-heavy."
        : `${sourceLabels.get(sourceType) || sourceType} example loaded.`,
    );
    setError(null);
  }

  function clearSources() {
    setSourceUrls("");
    setManualLinks("");
    setMessage("Sources cleared. Paste real company career pages or ATS board URLs before running discovery.");
    setError(null);
  }

  async function handleGenerateQueries(useAi = false) {
    setBusy(useAi ? "ai-queries" : "queries");
    setError(null);
    setMessage(null);
    try {
      if (useAi && !aiQueryAssistEnabled) {
        setMessage("Enable optional AI query generation before requesting AI search keyword help.");
        return;
      }
      const response = await generateJobFinderQueries({
        use_ai: useAi,
        user_enabled: useAi ? aiQueryAssistEnabled : false,
        user_triggered: true,
      });
      setQueries(response.queries.join("\n"));
      setMessage(
        useAi
          ? response.api_used
            ? `${response.provider || "Selected AI provider"} suggested search keywords. Matching, filtering, and scoring stay local.`
            : `AI query generation did not use an external API. ${response.warnings.join(" ") || "Rule-based keywords were loaded."}`
          : "Rule-based search keywords generated locally.",
      );
    } catch (queryError) {
      setError(queryError instanceof Error ? queryError.message : "Failed to generate queries.");
    } finally {
      setBusy(null);
    }
  }

  async function handleImportSources(format: "csv" | "json") {
    setBusy(`import-${format}`);
    setError(null);
    setMessage(null);
    try {
      const response = await importJobSourceFile({
        format,
        path:
          format === "csv"
            ? "job-database-script/outputs/source_discovery/job_sources.csv"
            : "job-database-script/outputs/source_discovery/job_sources.json",
        skip_existing: true,
        replace_existing: true,
      });
      await refreshSourceDatabase();
      setMessage(
        `Synced source ${format.toUpperCase()}: ${response.summary.created} created, ${response.summary.updated} updated, ${response.summary.deleted} removed.`,
      );
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : `Failed to import source ${format.toUpperCase()}.`);
    } finally {
      setBusy(null);
    }
  }

  async function handleRefreshSources() {
    setBusy("refresh-sources");
    setError(null);
    try {
      await refreshSourceDatabase();
      setMessage("Source database summary refreshed.");
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Failed to refresh source database.");
    } finally {
      setBusy(null);
    }
  }

  async function handleSearchSavedSources(atsTypes: string[]) {
    setBusy(`search-${atsTypes.join("-") || "all"}`);
    setError(null);
    setMessage(null);
    setSourceRequired(false);
    try {
      const safeExperienceLevels = requestExperienceLevels();
      const safeDegreeFilter = requestDegreeFilter();
      const safeLocationFilter = requestLocationFilter();
      const response = await searchSavedJobSources({
        ats_types: atsTypes,
        use_enabled_sources: true,
        limit: 5,
        offset: 0,
        location,
        queries: lines(queries).length > 0 ? lines(queries) : DEFAULT_QUERIES,
        exclude_duplicates: true,
        exclude_imported: true,
        max_sources: maxSources,
        match_mode: matchMode,
        target_experience_levels: safeExperienceLevels,
        excluded_experience_levels: safeExperienceLevels.includes("senior") ? [] : ["senior"],
        degree_filter: safeDegreeFilter,
        allow_unknown_location: safeLocationFilter.allow_unknown,
        location_filter: safeLocationFilter,
      });
      setCandidates(response.candidates);
      setSummary(response.summary);
      setSavedSourceResults(response.source_results || []);
      setDiagnostics(response.diagnostics || null);
      setSourceResults([]);
      setShowSourceDetails(false);
      setSelected(new Set());
      setCurrentRunId(response.run_id);
      setShowAllCandidates(false);
      setResultOffset(response.offset);
      setResultLimit(response.limit);
      setTotalMatches(response.total_matches);
      setHasMore(response.has_more);
      setMessage(
        response.diagnostics?.near_match_fallback_used
          ? `Run #${response.run_id}: 0 strong matches found, showing near matches for review.`
          : `Run #${response.run_id}: found ${response.total_matches} reviewable matches from ${response.summary.sources_checked ?? 0} saved sources using ${MATCH_MODES.find((mode) => mode.key === matchMode)?.label}.`,
      );
      await Promise.all([refreshRuns(), refreshSourceDatabase()]);
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : "Saved source search failed.");
    } finally {
      setBusy(null);
    }
  }

  async function handleCandidatePage(nextOffset: number) {
    if (currentRunId === null) {
      return;
    }
    setBusy("page-candidates");
    setError(null);
    try {
      const response = await getJobFinderRunCandidates(currentRunId, { limit: resultLimit, offset: Math.max(0, nextOffset) });
      setCandidates(response.candidates);
      setResultOffset(response.offset);
      setResultLimit(response.limit);
      setTotalMatches(response.total_matches);
      setHasMore(response.has_more);
      setSelected(new Set());
    } catch (pageError) {
      setError(pageError instanceof Error ? pageError.message : "Failed to load candidates.");
    } finally {
      setBusy(null);
    }
  }

  async function handleToggleSavedSource(source: JobSource) {
    setBusy(`source-${source.id}`);
    setError(null);
    try {
      const updated = await updateJobSource(source.id, { enabled: !source.enabled });
      setSavedSources((current) => current.map((item) => (item.id === source.id ? updated : item)));
      await refreshSourceDatabase();
    } catch (sourceError) {
      setError(sourceError instanceof Error ? sourceError.message : "Failed to update source.");
    } finally {
      setBusy(null);
    }
  }

  async function handleRun() {
    const sourceUrlValidation = validateUrls(lines(sourceUrls));
    const manualLinkValidation = validateUrls(lines(manualLinks));
    const validSourceUrls = sourceUrlValidation.valid;
    const validManualLinks = manualLinkValidation.valid;

    setSourceRequired(false);
    setError(null);
    setMessage(null);

    if (sourceTypes.length === 0) {
      setError("Select at least one source type, or use the default search setup.");
      return;
    }
    if (sourceUrlValidation.placeholders.length > 0 || manualLinkValidation.placeholders.length > 0) {
      setError("These look like example placeholders. Paste a real company/ATS URL.");
      return;
    }
    if (sourceUrlValidation.invalid.length > 0 || manualLinkValidation.invalid.length > 0) {
      setError(`Some entries are not valid URLs: ${[...sourceUrlValidation.invalid, ...manualLinkValidation.invalid].join(", ")}`);
      return;
    }
    if (validSourceUrls.length === 0 && validManualLinks.length === 0 && !sourceTypes.includes("web_search")) {
      setSourceRequired(true);
      setCandidates([]);
      setSummary({});
      setSourceResults([]);
      setSavedSourceResults([]);
      setDiagnostics(null);
      setCurrentRunId(null);
      return;
    }

    setBusy("run");
    try {
      const safeExperienceLevels = requestExperienceLevels();
      const safeDegreeFilter = requestDegreeFilter();
      const safeLocationFilter = requestLocationFilter();
      const response = await runJobFinder({
        source_types: sourceTypes,
        queries: lines(queries),
        location,
        source_urls: validSourceUrls,
        manual_links: validManualLinks,
        max_jobs: maxJobs,
        auto_verify: true,
        auto_score: true,
        match_mode: matchMode,
        target_experience_levels: safeExperienceLevels,
        excluded_experience_levels: safeExperienceLevels.includes("senior") ? [] : ["senior"],
        degree_filter: safeDegreeFilter,
        allow_unknown_location: safeLocationFilter.allow_unknown,
        location_filter: safeLocationFilter,
      });
      setCandidates(response.candidates);
      setSummary(response.summary);
      setSourceResults(response.source_results || []);
      setSavedSourceResults([]);
      setShowSourceDetails(false);
      setDiagnostics(null);
      setSelected(new Set());
      setCurrentRunId(response.run.id);
      setResultOffset(0);
      setResultLimit(response.candidates.length || 5);
      setTotalMatches(response.candidates.length);
      setHasMore(false);
      setShowAllCandidates(false);
      setMessage(response.message || `Discovery run #${response.run.id} completed with ${response.candidates.length} candidates.`);
      await refreshRuns();
      if (response.errors.length > 0) {
        setError(response.errors.join(" "));
      }
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Job discovery failed.");
    } finally {
      setBusy(null);
    }
  }

  async function handleToggleAllCandidates(checked: boolean) {
    setShowAllCandidates(checked);
    setBusy("load-candidates");
    setError(null);
    try {
      await loadCandidateView(currentRunId, checked);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load candidates.");
    } finally {
      setBusy(null);
    }
  }

  async function handleImport(candidateId: number) {
    setBusy(`import-${candidateId}`);
    setError(null);
    setMessage("Saving, verifying, and scoring...");
    try {
      const response = await saveCandidate(candidateId);
      setCandidates((current) => current.map((candidate) => (candidate.id === candidateId ? response.candidate : candidate)));
      setMessage(
        response.verified && response.scored
          ? "Saved. View in Saved Jobs."
          : `Saved. View in Saved Jobs. Verification/scoring may need retry. ${response.warnings.join(" ")}`,
      );
      await refreshRuns();
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : "Failed to import candidate.");
    } finally {
      setBusy(null);
    }
  }

  async function handleImportSelected() {
    const candidateIds = Array.from(selected);
    if (candidateIds.length === 0) {
      setError("Select at least one candidate to import.");
      return;
    }
    setBusy("import-selected");
    setError(null);
    setMessage("Saving, verifying, and scoring selected jobs...");
    try {
      const response = await saveSelectedCandidates(candidateIds);
      setMessage(
        response.imported_count > 0
          ? "Saved jobs. View them in Saved Jobs."
          : `No new jobs were saved. ${response.skipped_count} skipped.`,
      );
      if (response.errors.length > 0) {
        setError(response.errors.join(" "));
      }
      setSelected(new Set());
      await Promise.all([loadCandidateView(currentRunId, showAllCandidates), refreshRuns()]);
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : "Failed to import selected candidates.");
    } finally {
      setBusy(null);
    }
  }

  function clearCurrentView() {
    setCandidates([]);
    setSummary({});
    setSourceResults([]);
    setSavedSourceResults([]);
    setDiagnostics(null);
    setShowSourceDetails(false);
    setSelected(new Set());
    setCurrentRunId(null);
    setResultOffset(0);
    setTotalMatches(0);
    setHasMore(false);
    setShowAllCandidates(false);
    setMessage("Current result view cleared. Old runs remain available in Run History.");
    setError(null);
  }

  return (
    <div className="page">
      <section className="panel">
        <div className="section-title">
          <div>
            <h2>Source Database</h2>
            <p className="subtle">Search sources and save jobs you want to apply to.</p>
          </div>
          <button className="button secondary compact" type="button" onClick={() => void handleRefreshSources()} disabled={busy !== null}>
            Refresh Source Summary
          </button>
        </div>
        {sourceSummary && sourceSummary.total_sources > 0 ? (
          <div className="stats-grid">
            <div className="stat-card">
              <span>Total sources</span>
              <strong>{sourceSummary.total_sources}</strong>
            </div>
            <div className="stat-card">
              <span>Enabled sources</span>
              <strong>{sourceSummary.enabled_sources}</strong>
            </div>
            <div className="stat-card">
              <span>Valid or partial</span>
              <strong>{sourceSummary.valid_sources}</strong>
            </div>
            <div className="stat-card">
              <span>Partial sources</span>
              <strong>{sourceSummary.partial_sources}</strong>
            </div>
            <div className="stat-card">
              <span>Last import</span>
              <strong>{sourceSummary.last_imported_at ? new Date(sourceSummary.last_imported_at).toLocaleDateString() : "None"}</strong>
            </div>
            <div className="stat-card">
              <span>Last run</span>
              <strong>{sourceSummary.last_discovery_run_at ? new Date(sourceSummary.last_discovery_run_at).toLocaleDateString() : "None"}</strong>
            </div>
          </div>
        ) : (
          <div className="message error">
            <h3>No source database imported yet</h3>
            <p>No source database imported yet. Import job_sources.csv from job-database-script or seed example sources.</p>
          </div>
        )}
        <div className="button-row">
          <button className="button" type="button" onClick={() => void handleImportSources("csv")} disabled={busy !== null}>
            Import Source CSV
          </button>
          <button className="button secondary" type="button" onClick={() => void handleImportSources("json")} disabled={busy !== null}>
            Import Source JSON
          </button>
        </div>
        {sourceSummary && Object.keys(sourceSummary.by_ats_type).length > 0 ? (
          <div className="stats-grid source-helper">
            {Object.entries(sourceSummary.by_ats_type).map(([key, value]) => (
              <div className="stat-card" key={key}>
                <span>{key.replace("_", " ")}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        ) : null}
      </section>

      <section className="panel">
        <h2>Query Builder</h2>
        <div className="button-row">
          <button className="button secondary" type="button" onClick={() => void handleGenerateQueries(false)} disabled={busy !== null}>
            Generate Queries
          </button>
          <button className="button secondary" type="button" onClick={() => void handleGenerateQueries(true)} disabled={busy !== null}>
            Generate AI Search Keywords
          </button>
          <button className="button ghost" type="button" onClick={useDefaultQueries}>
            Use Broad Default Keywords
          </button>
        </div>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={aiQueryAssistEnabled}
            onChange={(event) => setAiQueryAssistEnabled(event.target.checked)}
          />
          <span>Enable optional AI query generation for the next explicit click</span>
        </label>
        <p className="subtle">
          AI query generation only suggests search keywords. Saved-source searching, matching, filtering, and scoring stay local/rule-based.
        </p>
        <label className="field-group">
          <span>Search Keywords</span>
          <span className="subtle">These keywords guide ranking. They are not exact required phrases.</span>
          <span className="subtle">
            Default keywords: data scientist, data engineer, machine learning engineer, analytics engineer, data analyst, software engineer data, new grad, entry level, early career, Bay Area, Remote US.
          </span>
          <textarea className="input" rows={8} value={queries} onChange={(event) => setQueries(event.target.value)} />
        </label>
      </section>

      <section className="panel">
        <div className="section-title">
          <h2>Sources</h2>
          <span className="subtle">Search saved sources first. Manual URLs are still available for advanced checks.</span>
        </div>
        <div className="source-helper">
          <h3>Source Type Search</h3>
          <div className="filter-row">
            <label className="field-group">
              <span>Match mode</span>
              <select
                className="input"
                value={matchMode}
                onChange={(event) => setMatchMode(event.target.value as "strict" | "balanced" | "broad")}
              >
                {MATCH_MODES.map((mode) => (
                  <option key={mode.key} value={mode.key}>
                    {mode.label}
                  </option>
                ))}
              </select>
              <span className="subtle">{MATCH_MODES.find((mode) => mode.key === matchMode)?.detail}</span>
            </label>
            <label className="field-group">
              <span>Location</span>
              <input className="input" value={location} onChange={(event) => setLocation(event.target.value)} />
            </label>
            <label className="field-group">
              <span>Max sources per run</span>
              <input
                className="input"
                type="number"
                min={1}
                max={200}
                value={maxSources}
                onChange={(event) => setMaxSources(Number(event.target.value))}
              />
              <span className="subtle">Default is 25. Lower values are faster but may miss jobs.</span>
            </label>
          </div>
          <p className="subtle">
            Search All checks Lever, Greenhouse, Ashby, company career pages, then Workday. Workday sources are searched last because many Workday boards expose limited metadata.
          </p>
          <div className="details-block">
            <h3>Search Fit Filters</h3>
            <div className="message">
              <p><strong>Experience:</strong> {experienceSummary(targetExperienceLevels)}</p>
              <p><strong>Degree:</strong> {degreeSummary(degreeFilter)}</p>
              <p><strong>Location:</strong> {locationSummary(locationFilter)}</p>
            </div>
            <div className="filter-row">
              <div className="field-group">
                <span>Experience Level</span>
                <div className="button-row">
                  <button className={`button compact ${activeExperiencePreset("target") ? "secondary" : "ghost"}`} type="button" onClick={() => setExperiencePreset("target")}>My target level</button>
                  <button className={`button compact ${activeExperiencePreset("internships") ? "secondary" : "ghost"}`} type="button" onClick={() => setExperiencePreset("internships")}>Include internships</button>
                  <button className={`button compact ${activeExperiencePreset("mid") ? "secondary" : "ghost"}`} type="button" onClick={() => setExperiencePreset("mid")}>Include mid-level stretch roles</button>
                  <button className={`button compact ${activeExperiencePreset("non-senior") ? "secondary" : "ghost"}`} type="button" onClick={() => setExperiencePreset("non-senior")}>Any non-senior</button>
                  <button className={`button compact ${activeExperiencePreset("any") ? "secondary" : "ghost"}`} type="button" onClick={() => setExperiencePreset("any")}>Any level</button>
                </div>
                <div className="checkbox-grid">
                  {EXPERIENCE_OPTIONS.map((option) => (
                    <label className="checkbox-row" key={option.key}>
                      <input
                        type="checkbox"
                        checked={targetExperienceLevels.includes(option.key)}
                        onChange={() => toggleExperienceLevel(option.key)}
                      />
                      <span>{option.label}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="field-group">
                <span>Degree Requirement</span>
                <div className="button-row">
                  <button className={`button compact ${activeDegreePreset("bachelors") ? "secondary" : "ghost"}`} type="button" onClick={() => setDegreePreset("bachelors")}>Bachelor's-friendly</button>
                  <button className={`button compact ${activeDegreePreset("exclude-grad") ? "secondary" : "ghost"}`} type="button" onClick={() => setDegreePreset("exclude-grad")}>Exclude strict grad degree</button>
                  <button className={`button compact ${activeDegreePreset("masters") ? "secondary" : "ghost"}`} type="button" onClick={() => setDegreePreset("masters")}>Include Master's required</button>
                  <button className={`button compact ${activeDegreePreset("phd") ? "secondary" : "ghost"}`} type="button" onClick={() => setDegreePreset("phd")}>Include PhD required</button>
                  <button className={`button compact ${activeDegreePreset("any") ? "secondary" : "ghost"}`} type="button" onClick={() => setDegreePreset("any")}>Any degree level</button>
                </div>
                <div className="checkbox-grid">
                  {DEGREE_OPTIONS.map((option) => (
                    <label className="checkbox-row" key={option.key}>
                      <input
                        type="checkbox"
                        checked={degreeFilter[option.key]}
                        onChange={(event) => setDegreeFilter((current) => ({ ...current, [option.key]: event.target.checked }))}
                      />
                      <span>{option.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div className="details-block">
            <h3>Location Fit Filters</h3>
            <div className="button-row">
              <button className={`button compact ${activeLocationPreset("bay-area") ? "secondary" : "ghost"}`} type="button" onClick={() => setLocationPreset("bay-area")}>Bay Area target</button>
              <button className={`button compact ${activeLocationPreset("california") ? "secondary" : "ghost"}`} type="button" onClick={() => setLocationPreset("california")}>California</button>
              <button className={`button compact ${activeLocationPreset("us-wide") ? "secondary" : "ghost"}`} type="button" onClick={() => setLocationPreset("us-wide")}>US-wide</button>
              <button className={`button compact ${activeLocationPreset("any") ? "secondary" : "ghost"}`} type="button" onClick={() => setLocationPreset("any")}>Any location</button>
            </div>
            <div className="checkbox-grid">
              {LOCATION_OPTIONS.map((option) => (
                <label className="checkbox-row" key={option.key}>
                  <input
                    type="checkbox"
                    checked={locationFilter[option.key]}
                    onChange={(event) => setLocationFilter((current) => ({ ...current, [option.key]: event.target.checked }))}
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="button-row">
            <button className="button" type="button" onClick={() => void handleSearchSavedSources(["lever"])} disabled={busy !== null}>
              Search Lever Sources
            </button>
            <button className="button" type="button" onClick={() => void handleSearchSavedSources(["greenhouse"])} disabled={busy !== null}>
              Search Greenhouse Sources
            </button>
            <button className="button" type="button" onClick={() => void handleSearchSavedSources(["ashby"])} disabled={busy !== null}>
              Search Ashby Sources
            </button>
            <button className="button" type="button" onClick={() => void handleSearchSavedSources(["workday"])} disabled={busy !== null}>
              Search Workday Sources
            </button>
            <button className="button secondary" type="button" onClick={() => void handleSearchSavedSources([])} disabled={busy !== null}>
              Search All Enabled Sources
            </button>
          </div>
        </div>

        <details className="details-block">
          <summary>Advanced manual source URL search</summary>
          <p className="subtle">
            Paste real ATS boards or company career pages when you want to test a source that is not in the database yet.
          </p>
          <div className="button-row">
            <button className="button secondary" type="button" onClick={() => useExampleSource("lever")}>
              Use Lever Example
            </button>
            <button className="button secondary" type="button" onClick={() => useExampleSource("greenhouse")}>
              Use Greenhouse Example
            </button>
            <button className="button secondary" type="button" onClick={() => useExampleSource("workday")}>
              Use Workday Example
            </button>
            <button className="button ghost" type="button" onClick={clearSources}>
              Clear Sources
            </button>
          </div>
          <div className="checkbox-grid">
            {(status?.sources || []).map((source) => (
              <label className="checkbox-row" key={source.source_type}>
                <input
                  type="checkbox"
                  checked={sourceTypes.includes(source.source_type)}
                  onChange={() => toggleSource(source.source_type)}
                  disabled={!source.configured && !source.manual_only}
                />
                <span>
                  {source.label} {source.manual_only ? "(manual)" : ""}
                </span>
              </label>
            ))}
          </div>
          <label className="field-group">
            <span>Source URLs</span>
            <textarea
              className="input"
              rows={6}
              placeholder={`Paste real source URLs, one per line. Examples:
${EXAMPLE_SOURCES.lever}
${EXAMPLE_SOURCES.greenhouse}
https://jobs.ashbyhq.com/[company]
${EXAMPLE_SOURCES.workday}
https://www.company.com/careers`}
              value={sourceUrls}
              onChange={(event) => setSourceUrls(event.target.value)}
            />
          </label>
          <label className="field-group">
            <span>Manual links</span>
            <textarea
              className="input"
              rows={4}
              placeholder="Paste LinkedIn, Indeed, Simplify, or direct job URLs here. CareerAgent accepts them as manual candidates and does not scrape LinkedIn or Indeed automatically."
              value={manualLinks}
              onChange={(event) => setManualLinks(event.target.value)}
            />
          </label>
          <div className="filter-row">
            <label className="field-group">
              <span>Max jobs</span>
              <input
                className="input"
                type="number"
                min={1}
                max={200}
                value={maxJobs}
                onChange={(event) => setMaxJobs(Number(event.target.value))}
              />
            </label>
          </div>
          <button className="button" type="button" onClick={() => void handleRun()} disabled={busy !== null}>
            {busy === "run" ? "Finding Jobs..." : "Find Jobs from Manual URLs"}
          </button>
        </details>
        <p className="subtle">Saved candidates are automatically verified and scored.</p>
        {message ? <p className="message success">{message}</p> : null}
        {error ? <p className="message error">{error}</p> : null}
      </section>

      {sourceRequired ? (
        <section className="warning-panel">
          <h2>Job Finder needs sources for this stage.</h2>
          <p>
            To discover jobs, paste a real company career page or ATS board URL. Broad web search comes later.
          </p>
          <div className="button-row">
            <button className="button secondary" type="button" onClick={() => useExampleSource("lever")}>
              Use Lever Example
            </button>
            <button className="button secondary" type="button" onClick={() => useExampleSource("greenhouse")}>
              Use Greenhouse Example
            </button>
            <button className="button secondary" type="button" onClick={() => useExampleSource("workday")}>
              Use Workday Example
            </button>
          </div>
        </section>
      ) : null}

      <section className="panel">
        <div className="section-title">
          <div>
            <h2>Discovery Results</h2>
            <p className="subtle">
              {currentRunId !== null && !showAllCandidates
                ? totalMatches > 0
                  ? `Showing ${resultOffset + 1}-${Math.min(resultOffset + candidates.length, totalMatches)} of ${totalMatches} matches from Run #${currentRunId}.`
                  : `Viewing results from Run #${currentRunId}.`
                : showAllCandidates
                  ? "Viewing all candidates across runs."
                  : "No current run selected."}
            </p>
          </div>
          <button className="button secondary compact" type="button" onClick={() => void handleImportSelected()} disabled={busy !== null || selected.size === 0}>
            Save Selected
          </button>
        </div>
        <div className="button-row">
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={showAllCandidates}
              onChange={(event) => void handleToggleAllCandidates(event.target.checked)}
            />
            Show all candidates
          </label>
          <button className="button ghost compact" type="button" onClick={clearCurrentView}>
            Clear current view
          </button>
          <button
            className="button secondary compact"
            type="button"
            onClick={() => void handleCandidatePage(resultOffset - resultLimit)}
            disabled={busy !== null || currentRunId === null || resultOffset <= 0 || showAllCandidates}
          >
            Previous 5
          </button>
          <button
            className="button secondary compact"
            type="button"
            onClick={() => void handleCandidatePage(resultOffset + resultLimit)}
            disabled={busy !== null || currentRunId === null || !hasMore || showAllCandidates}
          >
            Next 5
          </button>
        </div>
        <div className="stats-grid">
          {["total", "good_match", "weak_match", "excluded", "duplicate", "incomplete", "imported"].map((key) => (
            <div className="stat-card" key={key}>
              <span>{key.replace("_", " ")}</span>
              <strong>{summary[key] ?? 0}</strong>
            </div>
          ))}
        </div>

        {sourceResults.length > 0 ? (
          <div className="source-results">
            <h3>Source Results</h3>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Status</th>
                    <th>Found</th>
                    <th>Saved</th>
                    <th>Good</th>
                    <th>Weak</th>
                    <th>Excluded</th>
                    <th>Duplicates</th>
                    <th>Incomplete</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {sourceResults.map((result, index) => (
                    <tr key={`${result.source_url}-${result.source_type}-${index}`}>
                      <td>
                        <div className="status-stack">
                          <span>{sourceLabels.get(result.source_type) || result.source_type}</span>
                          {result.source_url ? (
                            <a className="inline-link" href={result.source_url} target="_blank" rel="noreferrer">
                              Source URL
                            </a>
                          ) : null}
                        </div>
                      </td>
                      <td><span className={sourceStatusClass(result.status)}>{result.status}</span></td>
                      <td>{result.found}</td>
                      <td>{result.saved_candidates}</td>
                      <td>{result.good_match}</td>
                      <td>{result.weak_match}</td>
                      <td>{result.excluded}</td>
                      <td>{result.duplicates}</td>
                      <td>{result.skipped_incomplete}</td>
                      <td>{[...result.warnings, ...result.errors].join(" ") || "No source warnings."}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}

        {savedSourceResults.length > 0 ? (
          <div className="source-results">
            <div className="section-title">
              <div>
                <h3>Saved Source Results</h3>
                <p className="subtle">{savedSourceDetailsSummary(savedSourceResults)}</p>
              </div>
              <button className="button secondary compact" type="button" onClick={() => setShowSourceDetails((current) => !current)}>
                {showSourceDetails ? "Hide source details" : "Show source details"}
              </button>
            </div>
            {showSourceDetails ? (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>ATS</th>
                      <th>Status</th>
                      <th>Fetched</th>
                      <th>Matches</th>
                      <th>Saved</th>
                      <th>Good</th>
                      <th>Weak</th>
                      <th>Excluded</th>
                      <th>Duplicates</th>
                      <th>Incomplete</th>
                      <th>Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {savedSourceResults.map((result, index) => (
                      <tr key={`${result.source_id}-${result.base_url}-${index}`}>
                        <td>
                          <div className="status-stack">
                            <span>{result.company || "Unknown"}</span>
                            <a className="inline-link" href={result.base_url} target="_blank" rel="noreferrer">
                              Source URL
                            </a>
                          </div>
                        </td>
                        <td>{result.ats_type}</td>
                        <td><span className={sourceStatusClass(result.status)}>{result.status}</span></td>
                        <td>{result.jobs_fetched}</td>
                        <td>{result.matches}</td>
                        <td>{result.candidates_saved}</td>
                        <td>{result.good_match}</td>
                        <td>{result.weak_match}</td>
                        <td>{result.excluded}</td>
                        <td>{result.duplicates}</td>
                        <td>{result.skipped_incomplete}</td>
                        <td>{[...result.warnings, ...result.errors].join(" ") || "No source warnings."}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : null}

        {candidates.length === 0 && (currentRunId !== null || savedSourceResults.length > 0 || sourceResults.length > 0) ? (
          <div className="warning-panel">
            <h3>No reviewable jobs matched this search.</h3>
            <p>
              CareerAgent checked the selected sources, but nothing reviewable survived the current filters.
            </p>
            <div className="stats-grid">
              {[
                ["sources checked", diagnostics?.sources_checked ?? summary.sources_checked ?? 0],
                ["jobs fetched", diagnostics?.jobs_fetched ?? summary.jobs_fetched ?? 0],
                ["jobs excluded", diagnostics?.jobs_excluded ?? summary.excluded ?? 0],
                ["excluded by experience", diagnostics?.excluded_by_experience ?? 0],
                ["excluded by degree", diagnostics?.excluded_by_degree ?? 0],
                ["excluded by location", diagnostics?.excluded_by_location ?? 0],
                ["excluded by role", diagnostics?.excluded_by_role ?? 0],
                ["excluded by confidence", diagnostics?.excluded_by_low_confidence ?? 0],
                ["Bay Area found", diagnostics?.bay_area_found ?? 0],
                ["Remote US found", diagnostics?.remote_us_found ?? 0],
                ["Unknown location found", diagnostics?.unknown_location_found ?? 0],
                ["California found", diagnostics?.non_bay_area_california_found ?? 0],
                ["Other US found", diagnostics?.other_us_found ?? 0],
                ["International found", diagnostics?.international_found ?? 0],
                ["duplicates", diagnostics?.duplicates ?? summary.duplicates ?? 0],
                ["incomplete", diagnostics?.incomplete ?? summary.skipped_incomplete ?? 0],
              ].map(([label, value]) => (
                <div className="stat-card" key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
            {(diagnostics?.top_exclusion_reasons || []).length > 0 ? (
              <>
                <h4>Top exclusion reasons</h4>
                <ul className="list">
                  {diagnostics?.top_exclusion_reasons?.map((entry) => (
                    <li key={entry.reason}>{entry.reason} ({entry.count})</li>
                  ))}
                </ul>
              </>
            ) : null}
            {(diagnostics?.top_incomplete_reasons || []).length > 0 ? (
              <>
                <h4>Incomplete results</h4>
                <ul className="list">
                  {diagnostics?.top_incomplete_reasons?.map((entry) => (
                    <li key={entry.reason}>{entry.reason} ({entry.count})</li>
                  ))}
                </ul>
              </>
            ) : null}
            {(diagnostics?.zero_result_diagnostics?.sample_excluded || []).length > 0 ? (
              <>
                <h4>Sample excluded jobs</h4>
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Company</th>
                        <th>Title</th>
                        <th>Location</th>
                        <th>Role</th>
                        <th>Experience</th>
                        <th>Degree</th>
                        <th>Primary reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {diagnostics?.zero_result_diagnostics?.sample_excluded?.map((sample, index) => (
                        <tr key={`${sample.company}-${sample.title}-${index}`}>
                          <td>{sample.company || "Unknown"}</td>
                          <td>{sample.title || "Missing title"}</td>
                          <td>{sample.location || "Unknown"}</td>
                          <td>{sample.role_category || "Other"}</td>
                          <td>{levelLabel(sample.experience_level)}</td>
                          <td>{sample.degree_level || "unknown"}</td>
                          <td>
                            {(sample.reasons || []).filter((reason) => reason.startsWith("Excluded:")).slice(-1)[0] || sample.primary_exclusion_category || "unclear"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : null}
            <h4>Try next</h4>
            <ul className="list">
              {(diagnostics?.suggestions || [
                "Switch to Broad Match.",
                "Increase max sources or search all enabled sources.",
                "Try Greenhouse or Lever sources first.",
              ]).map((suggestion) => (
                <li key={suggestion}>{suggestion}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {candidates.length > 0 ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Select</th>
                  <th>Company</th>
                  <th>Title</th>
                  <th>Location</th>
                  <th>Location Fit</th>
                  <th>Experience</th>
                  <th>Degree</th>
                  <th>Role</th>
                  <th>Source</th>
                  <th>Score</th>
                  <th>Status</th>
                  <th>Why it matched</th>
                  <th>Description</th>
                  <th>URL</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((candidate) => (
                  <tr key={candidate.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selected.has(candidate.id)}
                        onChange={(event) => setSelected((current) => {
                          const next = new Set(current);
                          if (event.target.checked) {
                            next.add(candidate.id);
                          } else {
                            next.delete(candidate.id);
                          }
                          return next;
                        })}
                        disabled={Boolean(candidate.imported_job_id) || ["duplicate", "imported", "excluded", "incomplete"].includes(candidate.filter_status)}
                      />
                    </td>
                    <td>{candidate.company}</td>
                    <td>{candidate.title || "Missing title"}</td>
                    <td>{candidate.location || "Location unknown"}</td>
                    <td><span className={candidateStatusClass(candidate.location_fit || "unknown")}>{locationFitLabel(candidate.location_fit)}</span></td>
                    <td>
                      <div className="status-stack">
                        <span className={candidateStatusClass(candidate.experience_level || "unknown")}>{experienceDisplay(candidate)}</span>
                        <span className="subtle">{strengthLabel(candidate.experience_requirement_strength)}</span>
                      </div>
                    </td>
                    <td>
                      <div className="status-stack">
                        <span>{degreeDisplay(candidate)}</span>
                        <span className="subtle">{strengthLabel(candidate.degree_requirement_strength)}</span>
                      </div>
                    </td>
                    <td>{candidate.role_category || "Other"}</td>
                    <td>{candidate.source_type}</td>
                    <td>{candidate.relevance_score}</td>
                    <td><span className={candidateStatusClass(candidate.filter_status)}>{candidate.filter_status}</span></td>
                    <td>
                      {candidate.filter_reasons.slice(0, 2).join(" ")}
                      {candidate.filter_reasons.length > 2 ? (
                        <details className="details-block">
                          <summary>More</summary>
                          <p>{candidate.filter_reasons.slice(2).join(" ")}</p>
                        </details>
                      ) : null}
                    </td>
                    <td>
                      {candidateDescription(candidate) ? (
                        <details className="details-block">
                          <summary>View description</summary>
                          <p>{candidateDescription(candidate)}</p>
                        </details>
                      ) : (
                        "Missing"
                      )}
                    </td>
                    <td>{candidate.url ? <a className="inline-link" href={candidate.url} target="_blank" rel="noreferrer">Open</a> : "None"}</td>
                    <td>
                      {candidate.imported_job_id ? (
                        <Link className="inline-link" href={`/jobs/${candidate.imported_job_id}`}>
                          Saved
                        </Link>
                      ) : (
                        <button
                          className="button secondary compact"
                          type="button"
                          onClick={() => void handleImport(candidate.id)}
                          disabled={busy !== null || ["duplicate", "excluded", "incomplete"].includes(candidate.filter_status)}
                        >
                          Save Job
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="panel">
        <details open>
          <summary>Saved Sources</summary>
          <p className="subtle">Compact view of imported sources. Disable noisy boards without deleting them.</p>
          <div className="table-wrapper details-block">
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>ATS type</th>
                  <th>Base URL</th>
                  <th>Enabled</th>
                  <th>Status</th>
                  <th>Jobs found</th>
                  <th>Last checked</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {savedSources.length === 0 ? (
                  <tr>
                    <td colSpan={8}>No saved sources loaded. Import job_sources.csv from job-database-script.</td>
                  </tr>
                ) : null}
                {savedSources.map((source) => (
                  <tr key={source.id}>
                    <td>{source.name}</td>
                    <td>{source.ats_type || source.source_type}</td>
                    <td>
                      <a className="inline-link" href={source.base_url} target="_blank" rel="noreferrer">
                        Open
                      </a>
                    </td>
                    <td>{source.enabled ? "Yes" : "No"}</td>
                    <td>{source.status || "unknown"}</td>
                    <td>{source.jobs_found ?? "Unknown"}</td>
                    <td>{source.last_checked_at ? new Date(source.last_checked_at).toLocaleString() : "Not checked"}</td>
                    <td>
                      <button
                        className="button secondary compact"
                        type="button"
                        onClick={() => void handleToggleSavedSource(source)}
                        disabled={busy !== null}
                      >
                        {source.enabled ? "Disable" : "Enable"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </section>

      <section className="panel">
        <h2>Run History</h2>
        <div className="timeline-list">
          {runs.length === 0 ? <p className="subtle">No discovery runs yet.</p> : null}
          {runs.map((run) => (
            <button
              className="timeline-item history-button"
              type="button"
              key={run.id}
              onClick={async () => {
                setCurrentRunId(run.id);
                setShowAllCandidates(false);
                setSummary({});
                setSourceResults([]);
                setSavedSourceResults([]);
                setBusy("load-candidates");
                try {
                  await loadCandidateView(run.id, false);
                  setMessage(`Viewing results from Run #${run.id}. Source diagnostics are shown for newly completed runs.`);
                  setError(null);
                } catch (loadError) {
                  setError(loadError instanceof Error ? loadError.message : "Failed to load run candidates.");
                } finally {
                  setBusy(null);
                }
              }}
            >
              <strong>Run #{run.id} - {run.status}</strong>
              <p className="subtle">
                {run.source_type} - {run.location} - found {run.total_found} - candidates {run.total_candidates} - imported {run.total_imported}
              </p>
              <p className="subtle">{runFitSummary(run)}</p>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
