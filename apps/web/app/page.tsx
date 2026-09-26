"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type Account = {
  id: string;
  platform: string;
  username: string;
  displayName: string;
  bio: string;
  avatar: string;
  followers: string;
  profileUrl: string;
};

type SavedProfile = {
  id: string;
  name: string;
  username: string;
  platform: string;
  profileUrl: string;
  savedAt: number;
};

const MOCK_RESULTS: Record<string, Account[]> = {
  default: [
    {
      id: "1",
      platform: "Instagram",
      username: "@avery.chen.pdx",
      displayName: "Avery Chen",
      bio: "designer / archivist / portland. community storytelling & public memory projects",
      avatar: "📸",
      followers: "2.4k",
      profileUrl: "https://instagram.com/avery.chen.pdx",
    },
    {
      id: "2",
      platform: "Twitter / X",
      username: "@averychen_",
      displayName: "avery chen",
      bio: "open archives, public records, design research. she/her",
      avatar: "🐦",
      followers: "891",
      profileUrl: "https://x.com/averychen_",
    },
    {
      id: "3",
      platform: "LinkedIn",
      username: "avery-chen-pdx",
      displayName: "Avery Chen",
      bio: "Design Researcher at Portland Public Archives • University of Oregon '21",
      avatar: "💼",
      followers: "500+",
      profileUrl: "https://linkedin.com/in/avery-chen-pdx",
    },
    {
      id: "4",
      platform: "TikTok",
      username: "@averychennn",
      displayName: "avery 🗂️",
      bio: "archive nerd. making history cool. portland based 🌲",
      avatar: "🎵",
      followers: "12.3k",
      profileUrl: "https://tiktok.com/@averychennn",
    },
    {
      id: "5",
      platform: "GitHub",
      username: "averychen",
      displayName: "Avery Chen",
      bio: "data viz & civic tech. contributions to open-source archive tools.",
      avatar: "💻",
      followers: "156",
      profileUrl: "https://github.com/averychen",
    },
  ],
};

const PLATFORM_COLORS: Record<string, string> = {
  Instagram: "from-freaky-pink to-freaky-purple",
  "Twitter / X": "from-freaky-blue to-freaky-blue",
  LinkedIn: "from-blue-400 to-blue-600",
  TikTok: "from-freaky-dark to-freaky-dark",
  GitHub: "from-gray-700 to-gray-900",
};

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

export default function HomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Account[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [scraping, setScraping] = useState<string | null>(null);
  const [savedProfiles, setSavedProfiles] = useState<SavedProfile[]>([]);
  const [showSaved, setShowSaved] = useState(false);

  useEffect(() => {
    setSavedProfiles(loadProfiles());
  }, []);

  function handleSearch() {
    if (!query.trim()) return;
    setSearching(true);
    setResults([]);
    setSearched(false);

    const mockAccounts = MOCK_RESULTS.default;
    setTimeout(() => setResults(mockAccounts.slice(0, 2)), 500);
    setTimeout(() => setResults(mockAccounts.slice(0, 4)), 900);
    setTimeout(() => {
      setResults(mockAccounts);
      setSearching(false);
      setSearched(true);
    }, 1300);
  }

  function handleAccountClick(account: Account) {
    setScraping(account.id);
    setTimeout(() => {
      const params = new URLSearchParams({
        name: account.displayName,
        username: account.username,
        platform: account.platform,
        profileUrl: account.profileUrl,
      });
      router.push(`/love-letters?${params.toString()}`);
    }, 2000);
  }

  function handleSaveProfile(account: Account) {
    const existing = savedProfiles.find(
      (p) => p.username === account.username && p.platform === account.platform,
    );
    if (existing) return;
    const profile: SavedProfile = {
      id: `${account.platform}-${account.username}-${Date.now()}`,
      name: account.displayName,
      username: account.username,
      platform: account.platform,
      profileUrl: account.profileUrl,
      savedAt: Date.now(),
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
    });
    router.push(`/love-letters?${params.toString()}`);
  }

  function isAccountSaved(account: Account) {
    return savedProfiles.some(
      (p) => p.username === account.username && p.platform === account.platform,
    );
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
        {query.trim() && !searching && !searched && (
          <p className="mt-2 pl-2 font-display text-xs text-text-muted">
            {inputHint}
          </p>
        )}
      </div>

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
                  <div className="flex-1 min-w-0">
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
      {searching && results.length === 0 && (
        <div className="py-12 text-center">
          <p className="animate-wiggle font-display text-2xl font-bold text-freaky-dark">
            snooping around... 🕵️
          </p>
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="mb-8">
          <div className="mb-4">
            <h2 className="font-display text-xl font-bold text-freaky-dark">
              {searching
                ? "finding accounts..."
                : `found ${results.length} accounts 👀`}
            </h2>
            {searched && (
              <p className="mt-1 font-display text-xs text-text-muted">
                click an account to start scraping & write love letters 💌
              </p>
            )}
          </div>

          <div className="space-y-3">
            {results.map((account, i) => {
              const isScraping = scraping === account.id;
              const isDisabled = scraping !== null && !isScraping;
              const alreadySaved = isAccountSaved(account);

              return (
                <div
                  key={account.id}
                  className="animate-pop-in"
                  style={{ animationDelay: `${i * 80}ms` }}
                >
                  <div
                    className={`flex items-center gap-4 rounded-2xl border-3 p-4 transition-all ${
                      isScraping
                        ? "border-freaky-red bg-freaky-red/5 shadow-[4px_4px_0_0] shadow-freaky-red"
                        : isDisabled
                          ? "border-freaky-dark/20 bg-bg-card opacity-40"
                          : "border-freaky-dark bg-bg-card shadow-[3px_3px_0_0] shadow-freaky-dark"
                    }`}
                  >
                    {/* Platform badge */}
                    <button
                      onClick={() => handleAccountClick(account)}
                      disabled={isDisabled || isScraping}
                      className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br text-xl transition-transform hover:scale-110 disabled:hover:scale-100 cursor-pointer disabled:cursor-default"
                    >
                      <div className={`flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${PLATFORM_COLORS[account.platform] ?? "from-gray-500 to-gray-700"}`}>
                        <span>{account.avatar}</span>
                      </div>
                    </button>

                    {/* Info — clickable */}
                    <button
                      onClick={() => handleAccountClick(account)}
                      disabled={isDisabled || isScraping}
                      className="min-w-0 flex-1 text-left cursor-pointer disabled:cursor-default"
                    >
                      <div className="mb-0.5 flex items-center gap-2">
                        <span className="font-display text-base font-bold text-freaky-dark">
                          {account.displayName}
                        </span>
                        <span className="rounded-full bg-freaky-dark/10 px-2 py-0.5 font-display text-[10px] font-bold text-freaky-dark/60">
                          {account.platform}
                        </span>
                      </div>
                      <p className="font-mono text-xs text-freaky-dark/50">
                        {account.username}
                      </p>
                      <p className="mt-0.5 truncate text-sm text-text-secondary">
                        {account.bio}
                      </p>
                    </button>

                    {/* Right side */}
                    <div className="shrink-0 flex items-center gap-2">
                      {isScraping ? (
                        <div className="flex flex-col items-center gap-1">
                          <span className="inline-block animate-spin text-lg">
                            🔍
                          </span>
                          <span className="font-display text-[10px] font-bold text-freaky-red">
                            scraping...
                          </span>
                        </div>
                      ) : (
                        <>
                          <div className="text-right">
                            <p className="font-display text-sm font-bold text-text-muted">
                              {account.followers}
                            </p>
                            <p className="mt-0.5 font-display text-[10px] text-text-muted">
                              followers
                            </p>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSaveProfile(account);
                            }}
                            disabled={alreadySaved}
                            className={`rounded-lg border-2 p-1.5 text-sm transition-all ${
                              alreadySaved
                                ? "border-freaky-dark/10 bg-freaky-dark/5 text-text-muted cursor-default"
                                : "border-freaky-dark/20 hover:border-freaky-pink hover:bg-freaky-pink/10 cursor-pointer"
                            }`}
                            title={alreadySaved ? "Already saved" : "Save profile"}
                          >
                            {alreadySaved ? "✅" : "💾"}
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* No results hint */}
      {!searching && !searched && results.length === 0 && (
        <div className="mt-4 grid grid-cols-3 gap-3 text-center">
          <HintCard emoji="👤" label="Name" example="Avery Chen" />
          <HintCard emoji="@" label="Username" example="@averychen_" />
          <HintCard emoji="🔗" label="Link" example="instagram.com/..." />
        </div>
      )}
    </main>
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
