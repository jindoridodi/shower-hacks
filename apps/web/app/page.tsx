"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  type CandidateSource,
  type DiscoveryResponse,
  type InstagramProfile,
  ApiError,
  discover,
  fetchInstagramProfile,
} from "../lib/api";
import { useProject } from "../lib/use-project";

// ── Types ──────────────────────────────────────────────────

type SavedProfile = {
  id: string;
  name: string;
  username: string;
  platform: string;
  profileUrl: string;
  savedAt: number;
  projectId?: string;
};

function instagramUsernameFromUrl(value: string): string | null {
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase().replace(/^www\./, "");
    const username = url.pathname.split("/").filter(Boolean)[0];
    return host === "instagram.com" && username && /^[A-Za-z0-9._]+$/.test(username)
      ? username
      : null;
  } catch {
    return null;
  }
}

// ── Platform styling ───────────────────────────────────────

const PLATFORM_EMOJI: Record<string, string> = {
  Instagram: "📸",
  Twitter: "🐦",
  "Twitter / X": "🐦",
  LinkedIn: "💼",
  TikTok: "🎵",
  GitHub: "💻",
  Facebook: "👤",
  Reddit: "🤖",
  YouTube: "🎬",
  Pinterest: "📌",
};

const PLATFORM_COLORS: Record<string, string> = {
  Instagram: "from-freaky-pink to-freaky-purple",
  Twitter: "from-freaky-blue to-freaky-blue",
  "Twitter / X": "from-freaky-blue to-freaky-blue",
  LinkedIn: "from-blue-400 to-blue-600",
  TikTok: "from-freaky-dark to-freaky-dark",
  GitHub: "from-gray-700 to-gray-900",
  Facebook: "from-blue-500 to-blue-700",
  Reddit: "from-orange-500 to-orange-700",
  YouTube: "from-red-500 to-red-700",
  Pinterest: "from-red-400 to-red-600",
};

const CONFIDENCE_BADGE: Record<string, string> = {
  high: "bg-green-100 text-green-700 border-green-300",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-300",
  low: "bg-red-100 text-red-700 border-red-300",
};

// ── LocalStorage helpers ───────────────────────────────────

function loadProfiles(): SavedProfile[] {
  try {
    const raw = localStorage.getItem("freakypeeky-profiles");
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveProfiles(profiles: SavedProfile[]) {
  try {
    localStorage.setItem("freakypeeky-profiles", JSON.stringify(profiles));
  } catch {}
}

// ── Page ───────────────────────────────────────────────────

export default function HomePage() {
  const router = useRouter();
  const { project, loading: projectLoading, create: createProj, clear: clearProject } = useProject();
  const [query, setQuery] = useState("");
  const [candidates, setCandidates] = useState<CandidateSource[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [providersUsed, setProvidersUsed] = useState<string[]>([]);

  const [selectedCandidate, setSelectedCandidate] = useState<CandidateSource | null>(null);
  const [igProfile, setIgProfile] = useState<InstagramProfile | null>(null);
  const [igLoading, setIgLoading] = useState(false);
  const [igError, setIgError] = useState<string | null>(null);

  const [savedProfiles, setSavedProfiles] = useState<SavedProfile[]>([]);
  const [showSaved, setShowSaved] = useState(false);

  useEffect(() => {
    setSavedProfiles(loadProfiles());
  }, []);

  const handleSearch = useCallback(async () => {
    const q = query.trim();
    if (!q) return;
    setSearching(true);
    setCandidates([]);
    setSearched(false);
    setSearchError(null);
    setWarnings([]);
    setProvidersUsed([]);
    setSelectedCandidate(null);
    setIgProfile(null);
    setIgError(null);

    try {
      let pid = project?.id;
      if (!pid) {
        const p = await createProj(q);
        pid = p?.id ?? undefined;
      }
      const res: DiscoveryResponse = await discover(q, pid);
      const directUsername = instagramUsernameFromUrl(q);
      const resolvedCandidates = res.candidates.map((candidate) =>
        directUsername && candidate.platform.toLowerCase() === "instagram"
          ? { ...candidate, candidateUsername: directUsername }
          : candidate,
      );
      setCandidates(resolvedCandidates);
      setWarnings(res.warnings);
      setProvidersUsed(res.providersUsed);
      setSearched(true);
      const directCandidate = resolvedCandidates.find(
        (candidate) => candidate.platform.toLowerCase() === "instagram" && candidate.candidateUsername,
      );
      if (directCandidate) await handleCandidateClick(directCandidate);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 422) {
          setSearchError("invalid query — try a username or profile link");
        } else {
          setSearchError(err.message);
        }
      } else {
        setSearchError("could not reach the backend — is the API running?");
      }
    } finally {
      setSearching(false);
    }
  }, [query, project, createProj]);

  async function handleCandidateClick(candidate: CandidateSource) {
    setSelectedCandidate(candidate);
    setIgProfile(null);
    setIgError(null);

    if (candidate.platform.toLowerCase() === "instagram" && candidate.candidateUsername) {
      setIgLoading(true);
      try {
        const profile = await fetchInstagramProfile(candidate.candidateUsername);
        setIgProfile(profile);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.code === "apify_not_configured") {
            setIgError("Instagram lookup isn't configured — APIFY_API_TOKEN is missing on the backend.");
          } else if (err.status === 404) {
            setIgError("Instagram profile not found.");
          } else if (err.status === 503) {
            setIgError("Instagram lookup is temporarily unavailable.");
          } else {
            setIgError(err.message);
          }
        } else {
          setIgError("could not reach the backend for Instagram lookup.");
        }
      } finally {
        setIgLoading(false);
      }
    }
  }

  function handleSaveProfile(candidate: CandidateSource) {
    const username = igProfile?.username ?? candidate.candidateUsername;
    if (!username) return;
    const existing = savedProfiles.find(
      (p) => p.username === username && p.platform === candidate.platform,
    );
    if (existing) return;
    const profile: SavedProfile = {
      id: `${candidate.platform}-${username}-${Date.now()}`,
      name: igProfile?.full_name ?? username,
      username,
      platform: candidate.platform,
      profileUrl: candidate.url,
      savedAt: Date.now(),
      projectId: project?.id,
    };
    const updated = [profile, ...savedProfiles];
    setSavedProfiles(updated);
    saveProfiles(updated);
  }

  function handleDeleteProfile(id: string) {
    const updated = savedProfiles.filter((p) => p.id !== id);
    setSavedProfiles(updated);
    saveProfiles(updated);
  }

  function handleLoadProfile(profile: SavedProfile) {
    const params = new URLSearchParams({
      name: profile.name,
      username: profile.username,
      platform: profile.platform,
      profileUrl: profile.profileUrl,
      ...(profile.projectId ? { projectId: profile.projectId } : {}),
    });
    router.push(`/love-letters?${params.toString()}`);
  }

  function isCandidateSaved(candidate: CandidateSource) {
    const username = candidate.candidateUsername ?? candidate.url;
    return savedProfiles.some(
      (p) => p.username === username && p.platform === candidate.platform,
    );
  }

  function formatCount(n: number | null): string {
    if (n == null) return "—";
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}m`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
    return n.toString();
  }

  const inputHint = query.includes("@")
    ? "searching by username..."
    : query.startsWith("http")
      ? "looking up profile link..."
      : "searching by name...";

  return (
    <main className="mx-auto max-w-3xl px-6 pb-12">
      {/* Banner */}
      <div className="mb-10 flex justify-center">
        <Image
          src="/banner.png"
          alt="Supporting Devotion in Motion"
          width={400}
          height={278}
          className="h-auto w-64 sm:w-80"
          priority
        />
      </div>

      {/* Heading */}
      <div className="mb-10 text-center">
        <h1 className="mb-3 font-display text-4xl font-bold text-freaky-dark sm:text-5xl">
          who&apos;s your{" "}
          <span className="inline-block animate-wiggle text-freaky-red">
            crush
          </span>
          ?
        </h1>
        <p className="mx-auto max-w-md font-body text-base text-text-secondary">
          enter their name, username, or a profile link and we&apos;ll find
          their accounts 👣
        </p>
      </div>

      {/* Search */}
      <div className="mb-8">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <span className="absolute top-1/2 left-4 -translate-y-1/2 text-xl">
              🔍
            </span>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSearch();
              }}
              placeholder="name, @username, or profile link..."
              className="w-full rounded-2xl border-3 border-freaky-dark bg-bg-card py-4 pr-4 pl-12 font-display text-lg font-bold text-freaky-dark shadow-[4px_4px_0_0] shadow-freaky-dark placeholder:font-normal placeholder:text-text-muted transition-shadow focus:shadow-[6px_6px_0_0] focus:shadow-freaky-red focus:outline-none"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={!query.trim() || searching}
            className="rounded-2xl border-3 border-freaky-dark bg-freaky-red px-6 py-4 font-display text-lg font-bold text-white shadow-[4px_4px_0_0] shadow-freaky-dark transition-all hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0_0] hover:shadow-freaky-dark active:translate-x-[4px] active:translate-y-[4px] active:shadow-none disabled:opacity-50"
          >
            {searching ? (
              <span className="inline-block animate-spin">👀</span>
            ) : (
              "peek!"
            )}
          </button>
        </div>
        {query.trim() && !searching && !searched && !searchError && (
          <p className="mt-2 pl-2 font-display text-xs text-text-muted">
            {inputHint}
          </p>
        )}
      </div>

      {/* Project indicator */}
      {!projectLoading && project && (
        <div className="mb-4 flex items-center gap-2 rounded-xl border-2 border-freaky-dark/15 bg-freaky-peach/15 px-4 py-2">
          <span className="text-sm">📁</span>
          <p className="flex-1 font-display text-xs font-bold text-freaky-dark/70">
            project: {project.name}
          </p>
          <button
            onClick={clearProject}
            className="font-display text-[10px] font-bold text-text-muted transition-colors hover:text-freaky-red"
          >
            new project
          </button>
        </div>
      )}

      {/* Saved profiles toggle */}
      <div className="mb-6 flex items-center justify-between">
        <button
          onClick={() => setShowSaved(!showSaved)}
          className="flex items-center gap-2 rounded-full border-2 border-freaky-dark/20 bg-bg-card px-4 py-2 font-display text-sm font-bold text-freaky-dark transition-all hover:border-freaky-red/40 hover:bg-freaky-red/5"
        >
          <span>💾</span>
          saved profiles
          {savedProfiles.length > 0 && (
            <span className="rounded-full bg-freaky-red px-2 py-0.5 text-[10px] font-bold text-white">
              {savedProfiles.length}
            </span>
          )}
          <span className={`transition-transform ${showSaved ? "rotate-180" : ""}`}>
            ▾
          </span>
        </button>
      </div>

      {/* Saved profiles list */}
      {showSaved && (
        <div className="animate-pop-in mb-8">
          {savedProfiles.length === 0 ? (
            <div className="rounded-2xl border-2 border-dashed border-freaky-dark/15 bg-bg-card/50 px-5 py-8 text-center">
              <p className="font-display text-sm text-text-muted">
                no saved profiles yet. search for someone and hit the 💾 button!
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {savedProfiles.map((profile) => (
                <div
                  key={profile.id}
                  className="flex items-center gap-3 rounded-2xl border-2 border-freaky-dark/20 bg-bg-card p-3 transition-all hover:border-freaky-dark/40"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-display text-sm font-bold text-freaky-dark">
                      {profile.name}
                    </p>
                    <p className="font-mono text-[10px] text-text-muted">
                      {profile.username} · {profile.platform}
                    </p>
                  </div>
                  <button
                    onClick={() => handleLoadProfile(profile)}
                    className="shrink-0 rounded-xl border-2 border-freaky-dark bg-freaky-pink px-3 py-1.5 font-display text-xs font-bold text-white transition-all hover:bg-freaky-red"
                  >
                    write 💌
                  </button>
                  <button
                    onClick={() => handleDeleteProfile(profile.id)}
                    className="shrink-0 rounded-xl border-2 border-freaky-dark/20 px-2 py-1.5 font-display text-xs text-text-muted transition-all hover:border-freaky-red hover:bg-freaky-red/10 hover:text-freaky-red"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Searching state */}
      {searching && (
        <div className="py-12 text-center">
          <p className="animate-wiggle font-display text-2xl font-bold text-freaky-dark">
            snooping around... 🕵️
          </p>
          <p className="mt-2 font-display text-sm text-text-muted">
            running OSINT discovery providers
          </p>
        </div>
      )}

      {/* Search error */}
      {searchError && (
        <div className="mb-8 rounded-2xl border-3 border-freaky-red/40 bg-freaky-red/5 px-5 py-4 text-center">
          <p className="font-display text-sm font-bold text-freaky-red">
            {searchError}
          </p>
          <button
            onClick={handleSearch}
            className="mt-3 rounded-xl border-2 border-freaky-red px-4 py-1.5 font-display text-xs font-bold text-freaky-red transition-all hover:bg-freaky-red hover:text-white"
          >
            try again
          </button>
        </div>
      )}

      {/* Warnings from discovery */}
      {warnings.length > 0 && (
        <div className="mb-4 rounded-2xl border-2 border-dashed border-yellow-400/50 bg-yellow-50/50 px-4 py-3">
          {warnings.map((w, i) => (
            <p key={i} className="font-display text-xs text-yellow-700">
              ⚠️ {w}
            </p>
          ))}
        </div>
      )}

      {/* Discovery results */}
      {searched && !searching && (
        <div className="mb-8">
          <div className="mb-4">
            <h2 className="font-display text-xl font-bold text-freaky-dark">
              {candidates.length === 0
                ? "no accounts found 😢"
                : `found ${candidates.length} candidate${candidates.length !== 1 ? "s" : ""} 👀`}
            </h2>
            {candidates.length > 0 && (
              <p className="mt-1 font-display text-xs text-text-muted">
                these are suggestions, not identity proof. click to inspect. providers: {providersUsed.join(", ") || "none"}
              </p>
            )}
          </div>

          {candidates.length === 0 && (
            <div className="rounded-2xl border-2 border-dashed border-freaky-dark/15 bg-bg-card/50 px-5 py-8 text-center">
              <p className="font-display text-sm text-text-muted">
                no matching profiles found. try a different username or link.
              </p>
            </div>
          )}

          <div className="space-y-3">
            {candidates.map((candidate, i) => {
              const isSelected = selectedCandidate?.url === candidate.url;
              const alreadySaved = isCandidateSaved(candidate);
              const emoji = PLATFORM_EMOJI[candidate.platform] ?? "🌐";

              return (
                <div
                  key={`${candidate.url}-${i}`}
                  className="animate-pop-in"
                  style={{ animationDelay: `${i * 60}ms` }}
                >
                  <div
                    className={`rounded-2xl border-3 p-4 transition-all ${
                      isSelected
                        ? "border-freaky-red bg-freaky-red/5 shadow-[4px_4px_0_0] shadow-freaky-red"
                        : "border-freaky-dark bg-bg-card shadow-[3px_3px_0_0] shadow-freaky-dark"
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      {/* Platform badge */}
                      <button
                        onClick={() => handleCandidateClick(candidate)}
                        className="flex h-12 w-12 shrink-0 cursor-pointer items-center justify-center rounded-xl transition-transform hover:scale-110"
                      >
                        <div
                          className={`flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br text-xl ${PLATFORM_COLORS[candidate.platform] ?? "from-gray-500 to-gray-700"}`}
                        >
                          <span>{emoji}</span>
                        </div>
                      </button>

                      {/* Info */}
                      <button
                        onClick={() => handleCandidateClick(candidate)}
                        className="min-w-0 flex-1 cursor-pointer text-left"
                      >
                        <div className="mb-0.5 flex items-center gap-2">
                          <span className="font-display text-base font-bold text-freaky-dark">
                            {candidate.candidateUsername ?? candidate.platform}
                          </span>
                          <span className="rounded-full bg-freaky-dark/10 px-2 py-0.5 font-display text-[10px] font-bold text-freaky-dark/60">
                            {candidate.platform}
                          </span>
                          <span
                            className={`rounded-full border px-2 py-0.5 font-display text-[10px] font-bold ${CONFIDENCE_BADGE[candidate.confidence]}`}
                          >
                            {candidate.confidence}
                          </span>
                        </div>
                        <p className="truncate font-mono text-xs text-freaky-dark/50">
                          {candidate.url}
                        </p>
                        <p className="mt-0.5 text-sm text-text-secondary">
                          {candidate.matchReason}
                        </p>
                      </button>

                      {/* Save */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSaveProfile(candidate);
                        }}
                        disabled={alreadySaved}
                        className={`shrink-0 rounded-lg border-2 p-1.5 text-sm transition-all ${
                          alreadySaved
                            ? "cursor-default border-freaky-dark/10 bg-freaky-dark/5 text-text-muted"
                            : "cursor-pointer border-freaky-dark/20 hover:border-freaky-pink hover:bg-freaky-pink/10"
                        }`}
                        title={alreadySaved ? "Already saved" : "Save profile"}
                      >
                        {alreadySaved ? "✅" : "💾"}
                      </button>
                    </div>

                    {/* Instagram profile detail (expanded) */}
                    {isSelected && candidate.platform.toLowerCase() === "instagram" && (
                      <div className="mt-4 border-t-2 border-freaky-dark/10 pt-4">
                        <InstagramDetail
                          profile={igProfile}
                          loading={igLoading}
                          error={igError}
                          formatCount={formatCount}
                        />
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* No results hint */}
      {!searching && !searched && !searchError && candidates.length === 0 && (
        <div className="mt-4 grid grid-cols-3 gap-3 text-center">
          <HintCard emoji="👤" label="Name" example="Avery Chen" />
          <HintCard emoji="@" label="Username" example="@averychen_" />
          <HintCard emoji="🔗" label="Link" example="instagram.com/..." />
        </div>
      )}
    </main>
  );
}

// ── Instagram Detail Panel ─────────────────────────────────

function InstagramDetail({
  profile,
  loading,
  error,
  formatCount,
}: {
  profile: InstagramProfile | null;
  loading: boolean;
  error: string | null;
  formatCount: (n: number | null) => string;
}) {
  if (loading) {
    return (
      <div className="py-4 text-center">
        <span className="inline-block animate-spin text-2xl">📸</span>
        <p className="mt-2 font-display text-xs text-text-muted">
          fetching Instagram profile...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border-2 border-dashed border-freaky-red/30 bg-freaky-red/5 px-4 py-3 text-center">
        <p className="font-display text-xs font-bold text-freaky-red">{error}</p>
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className="space-y-3">
      {/* Header row */}
      <div className="flex items-start gap-3">
        {profile.profile_picture_url && (
          <img
            src={profile.profile_picture_url}
            alt={profile.username}
            className="h-14 w-14 rounded-xl border-2 border-freaky-dark/20 object-cover"
          />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="font-display text-sm font-bold text-freaky-dark">
              {profile.full_name ?? profile.username}
            </p>
            {profile.is_verified && (
              <span className="rounded-full bg-blue-100 px-2 py-0.5 font-display text-[10px] font-bold text-blue-600">
                verified
              </span>
            )}
            {profile.is_private && (
              <span className="rounded-full bg-gray-100 px-2 py-0.5 font-display text-[10px] font-bold text-gray-600">
                private
              </span>
            )}
          </div>
          <p className="font-mono text-xs text-text-muted">@{profile.username}</p>
          {profile.biography && (
            <p className="mt-1 text-xs leading-relaxed text-text-secondary">
              {profile.biography}
            </p>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2">
        <StatPill label="posts" value={formatCount(profile.posts_count)} />
        <StatPill label="followers" value={formatCount(profile.followers_count)} />
        <StatPill label="following" value={formatCount(profile.follows_count)} />
      </div>

      {/* Links */}
      <div className="flex flex-wrap gap-2">
        {profile.category && (
          <span className="rounded-full border border-freaky-dark/15 bg-freaky-peach/20 px-2.5 py-1 font-display text-[10px] font-bold text-freaky-dark/70">
            {profile.category}
          </span>
        )}
        {profile.external_url && (
          <a
            href={profile.external_url}
            target="_blank"
            rel="noopener noreferrer"
            className="truncate rounded-full border border-freaky-dark/15 bg-bg-card px-2.5 py-1 font-mono text-[10px] text-freaky-dark/60 transition-colors hover:text-freaky-red"
          >
            🔗 {profile.external_url}
          </a>
        )}
      </div>

      {/* Recent posts */}
      {profile.recent_posts.length > 0 && (
        <div>
          <p className="mb-2 font-display text-xs font-bold text-freaky-dark/60">
            recent posts ({profile.recent_posts.length})
          </p>
          <div className="space-y-1.5">
            {profile.recent_posts.slice(0, 5).map((post, i) => (
              <div
                key={i}
                className="rounded-xl border border-freaky-dark/10 bg-bg-card/50 px-3 py-2"
              >
                <p className="line-clamp-2 text-xs text-text-secondary">
                  {post.caption}
                </p>
                <div className="mt-1 flex gap-3 font-mono text-[10px] text-text-muted">
                  {post.likes_count != null && <span>❤️ {formatCount(post.likes_count)}</span>}
                  {post.comments_count != null && <span>💬 {formatCount(post.comments_count)}</span>}
                  {post.timestamp && (
                    <span>{new Date(post.timestamp).toLocaleDateString()}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Small components ───────────────────────────────────────

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-freaky-dark/10 bg-bg-card/50 px-3 py-2 text-center">
      <p className="font-display text-sm font-bold text-freaky-dark">{value}</p>
      <p className="font-display text-[10px] text-text-muted">{label}</p>
    </div>
  );
}

function HintCard({
  emoji,
  label,
  example,
}: {
  emoji: string;
  label: string;
  example: string;
}) {
  return (
    <div className="rounded-2xl border-2 border-dashed border-freaky-dark/15 bg-bg-card/50 px-3 py-4">
      <span className="mb-1 block text-2xl">{emoji}</span>
      <p className="font-display text-xs font-bold text-freaky-dark">{label}</p>
      <p className="font-mono text-[10px] text-text-muted">{example}</p>
    </div>
  );
}
