const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    const code =
      typeof detail === "object" && detail?.code
        ? detail.code
        : `http_${res.status}`;
    const message =
      typeof detail === "string"
        ? detail
        : typeof detail === "object" && detail?.message
          ? detail.message
          : res.statusText;
    throw new ApiError(res.status, code, message);
  }

  return res.json() as Promise<T>;
}

// ── Instagram ──────────────────────────────────────────────

export type InstagramPost = {
  caption: string;
  url: string | null;
  timestamp: string | null;
  likes_count: number | null;
  comments_count: number | null;
};

export type InstagramProfile = {
  username: string;
  full_name: string | null;
  biography: string | null;
  profile_url: string | null;
  profile_picture_url: string | null;
  external_url: string | null;
  category: string | null;
  followers_count: number | null;
  follows_count: number | null;
  posts_count: number | null;
  is_verified: boolean | null;
  is_private: boolean | null;
  recent_posts: InstagramPost[];
};

export function fetchInstagramProfile(
  username: string,
): Promise<InstagramProfile> {
  return request<InstagramProfile>("/instagram/profiles", {
    method: "POST",
    body: JSON.stringify({ username }),
  });
}

// ── Discovery ──────────────────────────────────────────────

export type CandidateSource = {
  url: string;
  platform: string;
  candidateUsername: string | null;
  confidence: "high" | "medium" | "low";
  matchReason: string;
};

export type SavedSource = {
  sourceId: string;
  projectId: string;
  username: string;
  url: string;
  platform: string;
  confidence: "high" | "medium" | "low";
  matchReason: string;
  createdAt: string;
};

export type DiscoveryResponse = {
  query: string;
  candidates: CandidateSource[];
  providersUsed: string[];
  providerEvidence: Record<string, string[]>;
  savedSources: SavedSource[];
  partial: boolean;
  warnings: string[];
};

export function discover(
  query: string,
  projectId?: string,
): Promise<DiscoveryResponse> {
  return request<DiscoveryResponse>("/api/discovery", {
    method: "POST",
    body: JSON.stringify({
      query,
      ...(projectId ? { projectId } : {}),
    }),
  });
}

// ── Projects ───────────────────────────────────────────────

export type Project = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

export function createProject(
  name: string,
  description?: string,
): Promise<Project> {
  return request<Project>("/projects", {
    method: "POST",
    body: JSON.stringify({ name, description: description ?? null }),
  });
}

export function getProject(projectId: string): Promise<Project> {
  return request<Project>(`/projects/${projectId}`);
}

// ── Sources ────────────────────────────────────────────────

export type Source = {
  id: string;
  project_id: string;
  url: string;
  canonical_url: string;
  status: string;
  content_hash: string | null;
  scraped_at: string | null;
  created_at: string;
  updated_at: string;
};

export function createSource(
  projectId: string,
  url: string,
): Promise<Source> {
  return request<Source>("/sources", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, url }),
  });
}

export function listSources(projectId: string): Promise<Source[]> {
  return request<Source[]>(`/sources?project_id=${encodeURIComponent(projectId)}`);
}

// ── Crawls ─────────────────────────────────────────────────

export type Crawl = {
  id: string;
  source_id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export function queueCrawl(sourceId: string): Promise<Crawl> {
  return request<Crawl>(`/sources/${sourceId}/queue`, { method: "POST" });
}

export function listCrawls(sourceId: string): Promise<Crawl[]> {
  return request<Crawl[]>(`/crawls?source_id=${encodeURIComponent(sourceId)}`);
}

export function getCrawl(crawlId: string): Promise<Crawl> {
  return request<Crawl>(`/crawls/${crawlId}`);
}

// ── Reports ────────────────────────────────────────────────

export type ClaimSource = {
  id: string;
  claim_id: string;
  source_id: string;
  excerpt: string;
  created_at: string;
};

export type Claim = {
  id: string;
  report_id: string;
  claim_text: string;
  position: number;
  created_at: string;
  sources: ClaimSource[];
};

export type Report = {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  claims: Claim[];
};

export function createReport(
  projectId: string,
  title: string,
): Promise<Report> {
  return request<Report>("/reports", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, title }),
  });
}

export function getReport(reportId: string): Promise<Report> {
  return request<Report>(`/reports/${reportId}`);
}

// ── Health ─────────────────────────────────────────────────

export function healthCheck(): Promise<{ status: string }> {
  return request<{ status: string }>("/health");
}
