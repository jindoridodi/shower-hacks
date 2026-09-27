"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { ApiError, createCommunicationDraft, fetchInstagramProfile, type InstagramProfile } from "../../lib/api";

type Style = "romantic" | "poetic" | "chaotic" | "unhinged";

const STYLE_EMOJI: Record<Style, string> = { romantic: "💕", poetic: "🌙", chaotic: "🎪", unhinged: "🤪" };

function LetterPage() {
  const params = useSearchParams();
  const requestedUsername = params.get("username") || "";
  const projectId = params.get("projectId") || "";
  const [profile, setProfile] = useState<InstagramProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [style, setStyle] = useState<Style | null>(null);
  const [letter, setLetter] = useState<string | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<number[]>([0, 1, 2]);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    const username = requestedUsername.replace(/^@/, "");
    if (!username || username.includes("://")) {
      setError("Choose a profile with a valid Instagram username first.");
      return;
    }
    fetchInstagramProfile(username).then(setProfile).catch(() => setError("Could not load this public Instagram profile."));
  }, [requestedUsername]);

  async function generate() {
    if (!profile || !style) return;
    if (!projectId) { setError("This profile needs a project before a draft can be generated."); return; }
    setGenerating(true);
    try {
      const excerpts = [
        ...(profile.biography ? [{ sourceId: `instagram:${profile.username}`, text: profile.biography.slice(0, 500), sensitivityStatus: "safe" as const }] : []),
        ...profile.recent_posts.slice(0, 5).filter((_, index) => selectedEvidence.includes(index)).map((post) => ({ sourceId: `instagram:${profile.username}`, text: post.caption.slice(0, 500), sensitivityStatus: "safe" as const })),
      ];
      const draft = await createCommunicationDraft(projectId, profile.full_name || profile.username, style, excerpts);
      setLetter(draft.body || "There was not enough selected public evidence to create a draft.");
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not generate a draft from the selected public evidence."); }
    finally { setGenerating(false); }
  }

  return <main className="mx-auto max-w-3xl px-6 py-10">
    <div className="mb-8 rounded-2xl border-3 border-freaky-dark bg-bg-card p-5 shadow-[3px_3px_0_0] shadow-freaky-dark">
      <p className="font-display text-xs font-bold text-text-muted">writing to</p>
      <h1 className="font-display text-2xl font-bold text-freaky-dark">{profile?.full_name || profile?.username || "Loading profile"}</h1>
      <p className="font-mono text-xs text-text-muted">@{profile?.username || requestedUsername} · Instagram</p>
    </div>
    {error && <p className="rounded-xl border-2 border-freaky-red/30 bg-freaky-red/5 p-4 text-sm text-freaky-red">{error}</p>}
    {profile && <>
      <div className="mb-6 rounded-2xl border-2 border-freaky-dark/15 bg-bg-card p-4"><p className="font-display text-xs font-bold text-text-muted">select up to 5 public excerpts for this draft</p>{profile.biography && <p className="mt-2 text-sm">{profile.biography}</p>}<div className="mt-3 space-y-2">{profile.recent_posts.slice(0, 5).map((post, index) => <label key={post.url || index} className="flex gap-3 rounded-xl border border-freaky-dark/10 p-3"><input type="checkbox" checked={selectedEvidence.includes(index)} onChange={() => setSelectedEvidence((current) => current.includes(index) ? current.filter((item) => item !== index) : current.length < 5 ? [...current, index] : current)} /><span><p className="text-sm">{post.caption.slice(0, 500)}</p><span className="mt-1 flex gap-3 font-mono text-[10px] text-text-muted">{post.timestamp && <span>{new Date(post.timestamp).toLocaleDateString()}</span>}{post.url && <a href={post.url} target="_blank" rel="noreferrer" className="underline">view post</a>}</span></span></label>)}</div></div>
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">{(["romantic", "poetic", "chaotic", "unhinged"] as Style[]).map((item) => <button key={item} onClick={() => setStyle(item)} className={`rounded-xl border-2 p-3 font-display font-bold ${style === item ? "border-freaky-red bg-freaky-red/10" : "border-freaky-dark/20"}`}><span className="mr-1">{STYLE_EMOJI[item]}</span>{item}</button>)}</div>
      <button onClick={generate} disabled={!style || !selectedEvidence.length || generating} className="mx-auto block rounded-xl border-3 border-freaky-dark bg-freaky-pink px-6 py-3 font-display font-bold text-white disabled:opacity-40">{generating ? "writing..." : letter ? "replace the letter 💌" : "write the letter 💌"}</button>
    </>}
    {letter && <div className="mt-10 rounded-2xl border-3 border-freaky-dark bg-bg-card p-6 shadow-[4px_4px_0_0] shadow-freaky-dark"><p className="mb-4 font-display text-xs font-bold text-text-muted">PUBLIC PROFILE DATA ONLY · REVIEW BEFORE USE</p><p className="whitespace-pre-wrap font-body leading-relaxed">{letter}</p></div>}
  </main>;
}

export default function LoveLettersPage() { return <Suspense><LetterPage /></Suspense>; }
