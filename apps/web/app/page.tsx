"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

type Account = {
  id: string;
  platform: string;
  username: string;
  displayName: string;
  bio: string;
  avatar: string;
  followers: string;
  url: string;
};

const MOCK_RESULTS: Account[] = [
  {
    id: "1",
    platform: "Instagram",
    username: "@avery.chen.pdx",
    displayName: "Avery Chen",
    bio: "designer / archivist / portland. community storytelling & public memory projects",
    avatar: "🧑‍🎨",
    followers: "2.4k",
    url: "https://example.test/avery-ig",
  },
  {
    id: "2",
    platform: "Twitter / X",
    username: "@averychen_",
    displayName: "avery chen",
    bio: "open archives, public records, design research. she/her",
    avatar: "🐦",
    followers: "891",
    url: "https://example.test/avery-tw",
  },
  {
    id: "3",
    platform: "LinkedIn",
    username: "avery-chen-pdx",
    displayName: "Avery Chen",
    bio: "Design Researcher at Portland Public Archives • University of Oregon '21",
    avatar: "💼",
    followers: "500+",
    url: "https://example.test/avery-li",
  },
  {
    id: "4",
    platform: "TikTok",
    username: "@averychennn",
    displayName: "avery 🗂️",
    bio: "archive nerd. making history cool. portland based 🌲",
    avatar: "🎵",
    followers: "12.3k",
    url: "https://example.test/avery-tt",
  },
  {
    id: "5",
    platform: "GitHub",
    username: "averychen",
    displayName: "Avery Chen",
    bio: "data viz & civic tech. contributions to open-source archive tools.",
    avatar: "💻",
    followers: "156",
    url: "https://example.test/avery-gh",
  },
];

const PLATFORM_COLORS: Record<string, string> = {
  Instagram: "bg-gradient-to-r from-freaky-pink to-freaky-purple",
  "Twitter / X": "bg-freaky-blue",
  LinkedIn: "bg-blue-500",
  TikTok: "bg-freaky-dark",
  GitHub: "bg-gray-800",
};

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Account[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  function handleSearch() {
    if (!query.trim()) return;
    setSearching(true);
    setResults([]);
    setSearched(false);

    setTimeout(() => {
      setResults(MOCK_RESULTS.slice(0, 2));
    }, 600);
    setTimeout(() => {
      setResults(MOCK_RESULTS.slice(0, 4));
    }, 1100);
    setTimeout(() => {
      setResults(MOCK_RESULTS);
      setSearching(false);
      setSearched(true);
    }, 1600);
  }

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      {/* Hero */}
      <div className="mb-12 text-center">
        <div className="mb-6 inline-block animate-peek">
          <Image
            src="/logo.png"
            alt="freakypeeky logo"
            width={280}
            height={100}
            className="mx-auto h-auto w-56 sm:w-72"
            priority
          />
        </div>

        <h1 className="mb-3 font-display text-4xl font-bold text-freaky-dark sm:text-5xl">
          who are you{" "}
          <span className="inline-block animate-wiggle text-freaky-red">
            stalking
          </span>{" "}
          today?
        </h1>
        <p className="font-body text-lg text-text-secondary">
          enter a name and we&apos;ll find their digital footprint 👣
        </p>
      </div>

      {/* Search */}
      <div className="mb-10">
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
              placeholder="type a name... e.g. Avery Chen"
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
      </div>

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
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-display text-xl font-bold text-freaky-dark">
              {searching ? "finding accounts..." : `found ${results.length} accounts 👀`}
            </h2>
            {selected.size > 0 && (
              <span className="rounded-full bg-freaky-red px-3 py-1 font-display text-xs font-bold text-white">
                {selected.size} selected
              </span>
            )}
          </div>

          <div className="space-y-3">
            {results.map((account, i) => (
              <button
                key={account.id}
                onClick={() => toggleSelect(account.id)}
                className="animate-pop-in w-full text-left"
                style={{ animationDelay: `${i * 80}ms` }}
              >
                <div
                  className={`flex items-center gap-4 rounded-2xl border-3 p-4 transition-all ${
                    selected.has(account.id)
                      ? "border-freaky-red bg-freaky-red/5 shadow-[4px_4px_0_0] shadow-freaky-red"
                      : "border-freaky-dark bg-bg-card shadow-[3px_3px_0_0] shadow-freaky-dark hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[2px_2px_0_0]"
                  }`}
                >
                  {/* Avatar */}
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl border-2 border-freaky-dark bg-bg text-2xl">
                    {account.avatar}
                  </div>

                  {/* Info */}
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-center gap-2">
                      <span className="font-display text-base font-bold text-freaky-dark">
                        {account.displayName}
                      </span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold text-white ${PLATFORM_COLORS[account.platform] ?? "bg-gray-500"}`}
                      >
                        {account.platform}
                      </span>
                    </div>
                    <p className="text-sm font-bold text-freaky-dark/70">
                      {account.username}
                    </p>
                    <p className="truncate text-sm text-text-secondary">
                      {account.bio}
                    </p>
                  </div>

                  {/* Followers + check */}
                  <div className="shrink-0 text-right">
                    <p className="font-display text-sm font-bold text-text-muted">
                      {account.followers}
                    </p>
                    <div
                      className={`mt-1 flex h-6 w-6 items-center justify-center rounded-full border-2 transition-colors ${
                        selected.has(account.id)
                          ? "border-freaky-red bg-freaky-red text-white"
                          : "border-freaky-dark/30"
                      }`}
                    >
                      {selected.has(account.id) && (
                        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Action button */}
      {selected.size > 0 && (
        <div className="animate-pop-in sticky bottom-6 flex justify-center">
          <Link
            href="/persona"
            className="inline-flex items-center gap-2 rounded-2xl border-3 border-freaky-dark bg-freaky-red px-8 py-4 font-display text-lg font-bold text-white shadow-[4px_4px_0_0] shadow-freaky-dark transition-all hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0_0] hover:shadow-freaky-dark"
          >
            get freaky with {selected.size} account{selected.size !== 1 ? "s" : ""} 🎭
          </Link>
        </div>
      )}

      {/* Empty state after search */}
      {searched && !searching && results.length > 0 && selected.size === 0 && (
        <p className="text-center font-display text-sm text-text-muted">
          tap accounts to select them, then get freaky 🫣
        </p>
      )}
    </main>
  );
}
