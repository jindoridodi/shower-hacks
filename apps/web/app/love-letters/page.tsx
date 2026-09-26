"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

// --- Types ---

type LetterStyle = "romantic" | "unhinged" | "poetic" | "chaotic";

type GeneratedLetter = {
  id: string;
  style: LetterStyle;
  content: string;
  subject: string;
};

type ChatMessage = {
  id: string;
  role: "user" | "ai" | "system";
  text: string;
};

// --- Style config ---

const STYLE_CONFIG: Record<
  LetterStyle,
  { label: string; emoji: string; color: string; border: string; description: string }
> = {
  romantic: {
    label: "Romantic",
    emoji: "💕",
    color: "text-freaky-pink bg-freaky-pink/10",
    border: "border-freaky-pink",
    description: "sweet & sincere",
  },
  unhinged: {
    label: "Unhinged",
    emoji: "🤪",
    color: "text-freaky-red bg-freaky-red/10",
    border: "border-freaky-red",
    description: "absolutely feral",
  },
  poetic: {
    label: "Poetic",
    emoji: "🌙",
    color: "text-freaky-purple bg-freaky-purple/10",
    border: "border-freaky-purple",
    description: "artsy yearning",
  },
  chaotic: {
    label: "Chaotic",
    emoji: "🎪",
    color: "text-freaky-blue bg-freaky-blue/10",
    border: "border-freaky-blue",
    description: "gen z brain rot",
  },
};

// --- Mock letter content ---

const SAMPLE_LETTERS: Record<LetterStyle, { subject: string; content: string }> = {
  romantic: {
    subject: "I've been thinking about you",
    content: `Dear {name},

I know this might seem forward, but I've been following your work with public archives and I have to say... the way you talk about community storytelling? It does something to my heart.

The Neighborhood Memory Map project you did in 2024 — combining oral histories with old photographs — that's not just design work. That's someone who sees beauty in the stories people leave behind. And I think that's incredibly attractive.

I'd love to get a coffee sometime and hear about the Open Archives Symposium. Or honestly, I'd listen to you talk about spreadsheets all day.

With admiration (and a little bit of a crush),
A secret admirer 💕

P.S. What if we've already passed each other at a food cart?`,
  },
  unhinged: {
    subject: "I am UNWELL about you",
    content: `{name}.

I have looked at your profile SEVENTEEN times today. SEVENTEEN. Do you know what that does to a person?? Your aesthetic alone has me in a CHOKEHOLD.

The way you described the Neighborhood Memory Map as "combining oral histories with photographs from local public collections" — I SCREAMED. I actually screamed out loud in a coffee shop. People stared. I don't care. YOU GET IT.

I'm not saying I would reorganize my entire Spotify around your interests but I absolutely already did that. My playlist goes HARD and it's all for you.

Please acknowledge my existence,
Someone who needs professional help 🫠

P.S. I made a spreadsheet ranking your projects by how much they made me feel things. Everything is #1.`,
  },
  poetic: {
    subject: "On archives and longing",
    content: `{name},

There is a kind of tenderness in the way you handle other people's memories — as though each photograph, each oral history, is a small animal you've been asked to hold.

I think about the Neighborhood Memory Map and I see you there, somewhere between the past and the present, building bridges out of the things we almost forgot to keep.

At the symposium, you stood before a room and said: here is what we found. Here is what we don't know. And the courage of that second sentence — the honest admission of gaps — that's where I fell.

Not into love, exactly. Into attention. The kind that doesn't look away.

Probably you'd laugh. I hope you'd laugh.

In the rain, thinking of archives,
An anonymous reader 🌙`,
  },
  chaotic: {
    subject: "no thoughts just vibes (and u)",
    content: `yo {name}

ok so hear me out

you: *posts literally anything*
me: 🧎

you: *makes a whole project called Neighborhood Memory Map*
me: is this a marriage proposal??

real talk tho your work is fire. like you really said "I'm gonna take old photos and oral histories and make people FEEL things" and then you just... DID THAT??? the audacity. the RANGE.

i made you a tier list:
- S tier: everything about you
- F tier: the fact that I don't know you irl

anyway this is my application to be your favorite internet weirdo. references available upon request (they are all screenshots of your profile).

your biggest fan (gender neutral) 🎪

tl;dr: you're cool and I'm normal about it (lie)`,
  },
};

// --- Persona chat responses ---

const AI_RESPONSES: Record<string, string> = {
  default:
    "omg hiii!! so like, I'm literally just here vibing with my archive projects and my oat milk latte. what do you wanna know about me? 🗂️✨",
  hobby:
    "okay so my WHOLE thing is public archives and community storytelling?? like I literally spent all of 2024 on this project called Neighborhood Memory Map where we combined oral histories with old photos from local collections. it's giving... civic engagement but make it aesthetic 📸",
  work: "I'm a design researcher!! currently doing a lot of work around public records and how communities interact with their own histories. presented at the Open Archives Symposium in March 2025 which was literally life-changing ngl 🎤",
  portland:
    "portland is my WHOLE personality at this point lol. the food carts, the rain, the passive aggression... I wouldn't trade it for anything. plus the archive scene here is actually incredible?? 🌲☕",
  music:
    "okay don't judge me but I have a very curated 'archiving in the rain' playlist that's mostly ambient + japanese city pop??? it helps me focus when I'm digitizing old newspaper clippings at 2am 🎵",
  food: "I'm a food cart CONNOISSEUR. there's this one cart on Hawthorne that does these amazing dumplings and I literally go there 3x a week. also I make my own kombucha which is very portland of me I know 🥟",
  dating:
    "haha omg are you asking if I'm single?? let's just say my love language is showing someone a really well-organized spreadsheet of primary sources 📊💕 ...yeah I'm single",
};

function getAIResponse(msg: string): string {
  const l = msg.toLowerCase();
  if (l.includes("hobby") || l.includes("archive") || l.includes("project") || l.includes("interest")) return AI_RESPONSES.hobby;
  if (l.includes("work") || l.includes("job") || l.includes("career") || l.includes("research")) return AI_RESPONSES.work;
  if (l.includes("portland") || l.includes("city") || l.includes("live") || l.includes("where")) return AI_RESPONSES.portland;
  if (l.includes("music") || l.includes("listen") || l.includes("song") || l.includes("playlist")) return AI_RESPONSES.music;
  if (l.includes("food") || l.includes("eat") || l.includes("restaurant") || l.includes("cook")) return AI_RESPONSES.food;
  if (l.includes("dating") || l.includes("single") || l.includes("relationship") || l.includes("love")) return AI_RESPONSES.dating;
  return AI_RESPONSES.default;
}

// --- Main page component (wrapped in Suspense) ---

function LoveLettersContent() {
  const searchParams = useSearchParams();
  const targetName = searchParams.get("name") || "Avery Chen";
  const targetUsername = searchParams.get("username") || "@avery.chen.pdx";
  const targetPlatform = searchParams.get("platform") || "Instagram";

  const [selectedStyle, setSelectedStyle] = useState<LetterStyle | null>(null);
  const [generating, setGenerating] = useState(false);
  const [letter, setLetter] = useState<GeneratedLetter | null>(null);
  const [copied, setCopied] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  function generateLetter() {
    if (!selectedStyle) return;
    setGenerating(true);
    setLetter(null);

    setTimeout(() => {
      const template = SAMPLE_LETTERS[selectedStyle];
      setLetter({
        id: `letter-${Date.now()}`,
        style: selectedStyle,
        subject: template.subject,
        content: template.content.replace(/\{name\}/g, targetName),
      });
      setGenerating(false);
    }, 2000);
  }

  function copyLetter() {
    if (!letter) return;
    navigator.clipboard.writeText(letter.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function regenerate() {
    setLetter(null);
    setSelectedStyle(null);
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      {/* Target header */}
      <div className="mb-8 flex items-center gap-4 rounded-2xl border-3 border-freaky-dark bg-bg-card p-5 shadow-[3px_3px_0_0] shadow-freaky-dark">
        <div className="flex h-14 w-14 items-center justify-center rounded-xl border-2 border-freaky-dark bg-freaky-peach text-2xl">
          💌
        </div>
        <div className="flex-1">
          <p className="font-display text-xs font-bold text-text-muted">
            writing to
          </p>
          <h1 className="font-display text-2xl font-bold text-freaky-dark">
            {targetName}
          </h1>
          <p className="font-mono text-xs text-text-muted">
            {targetUsername} · {targetPlatform}
          </p>
        </div>
        <button
          onClick={() => setChatOpen(true)}
          className="flex items-center gap-2 rounded-xl border-2 border-freaky-dark bg-freaky-yellow/30 px-4 py-2 font-display text-sm font-bold text-freaky-dark transition-all hover:bg-freaky-yellow/50 hover:-rotate-1"
        >
          🎭 chat with them
        </button>
      </div>

      {/* Style picker */}
      {!letter && (
        <>
          <div className="mb-6">
            <h2 className="mb-1 font-display text-lg font-bold text-freaky-dark">
              pick your vibe ✨
            </h2>
            <p className="font-body text-sm text-text-secondary">
              how freaky are we getting today?
            </p>
          </div>

          <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {(Object.entries(STYLE_CONFIG) as [LetterStyle, typeof STYLE_CONFIG[LetterStyle]][]).map(
              ([style, config]) => (
                <button
                  key={style}
                  onClick={() => setSelectedStyle(style)}
                  className={`rounded-2xl border-3 p-4 text-center transition-all ${
                    selectedStyle === style
                      ? `${config.border} ${config.color} shadow-[3px_3px_0_0] shadow-current -translate-y-1`
                      : "border-freaky-dark/15 bg-bg-card hover:border-freaky-dark/30 hover:-translate-y-0.5"
                  }`}
                >
                  <span className="mb-1 block text-2xl">{config.emoji}</span>
                  <span className="block font-display text-sm font-bold text-freaky-dark">
                    {config.label}
                  </span>
                  <span className="block text-[10px] text-text-muted">
                    {config.description}
                  </span>
                </button>
              ),
            )}
          </div>

          {/* Generate button */}
          <div className="mb-10 text-center">
            <button
              onClick={generateLetter}
              disabled={!selectedStyle || generating}
              className="inline-flex items-center gap-2 rounded-2xl border-3 border-freaky-dark bg-freaky-pink px-8 py-4 font-display text-lg font-bold text-white shadow-[4px_4px_0_0] shadow-freaky-dark transition-all hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0_0] hover:shadow-freaky-dark disabled:opacity-40"
            >
              {generating ? (
                <>
                  <span className="inline-block animate-spin">💕</span>
                  cooking up something special...
                </>
              ) : (
                <>write the letter 💌</>
              )}
            </button>
          </div>
        </>
      )}

      {/* Generated letter */}
      {letter && (
        <div className="animate-pop-in">
          <div className="mb-6 overflow-hidden rounded-2xl border-3 border-freaky-dark shadow-[4px_4px_0_0] shadow-freaky-dark">
            {/* Envelope header */}
            <div className="flex items-center justify-between border-b-3 border-freaky-dark bg-freaky-peach/40 px-5 py-3">
              <div className="flex items-center gap-3">
                <span className="text-xl">
                  {STYLE_CONFIG[letter.style].emoji}
                </span>
                <div>
                  <p className="font-display text-[10px] font-bold text-text-muted">
                    TO: {targetName} ({targetUsername})
                  </p>
                  <p className="font-display text-sm font-bold text-freaky-dark">
                    {letter.subject}
                  </p>
                </div>
              </div>
              <span
                className={`rounded-full border-2 px-3 py-1 font-display text-[10px] font-bold ${STYLE_CONFIG[letter.style].color} ${STYLE_CONFIG[letter.style].border}`}
              >
                {STYLE_CONFIG[letter.style].label}
              </span>
            </div>

            {/* Letter body */}
            <div className="bg-bg-card p-6">
              <div className="whitespace-pre-wrap font-body text-sm leading-relaxed text-freaky-dark">
                {letter.content}
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between border-t-3 border-freaky-dark bg-freaky-peach/20 px-5 py-3">
              <p className="font-display text-[10px] font-bold text-text-muted">
                AI-GENERATED · PUBLIC DATA ONLY · REVIEW BEFORE USE
              </p>
              <div className="flex gap-2">
                <button
                  onClick={regenerate}
                  className="rounded-full border-2 border-freaky-dark/30 px-4 py-1.5 font-display text-xs font-bold text-freaky-dark transition-all hover:border-freaky-dark hover:bg-freaky-dark/5"
                >
                  try again 🔄
                </button>
                <button
                  onClick={copyLetter}
                  className="rounded-full border-2 border-freaky-dark px-4 py-1.5 font-display text-xs font-bold text-freaky-dark transition-all hover:bg-freaky-dark hover:text-white"
                >
                  {copied ? "copied! ✅" : "copy 📋"}
                </button>
              </div>
            </div>
          </div>

          {/* Warning */}
          <div className="rounded-2xl border-2 border-dashed border-freaky-red/40 bg-freaky-red/5 px-5 py-3 text-center">
            <p className="font-display text-xs font-bold text-freaky-red">
              🚨 AI-generated based on public data. don&apos;t send without
              consent. be cool. 🚨
            </p>
          </div>
        </div>
      )}

      {/* Persona chat popup */}
      {chatOpen && (
        <PersonaChat
          name={targetName}
          username={targetUsername}
          platform={targetPlatform}
          onClose={() => setChatOpen(false)}
        />
      )}
    </main>
  );
}

export default function LoveLettersPage() {
  return (
    <Suspense>
      <LoveLettersContent />
    </Suspense>
  );
}

// --- Persona Chat Popup ---

function PersonaChat({
  name,
  username,
  platform,
  onClose,
}: {
  name: string;
  username: string;
  platform: string;
  onClose: () => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "sys-1",
      role: "system",
      text: `chatting with AI pretending to be ${name}. everything is from public data. don't be weird... or do 🫣`,
    },
    { id: "ai-1", role: "ai", text: AI_RESPONSES.default },
  ]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  function send() {
    const text = input.trim();
    if (!text || typing) return;
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: "user", text },
    ]);
    setInput("");
    setTyping(true);
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        { id: `a-${Date.now()}`, role: "ai", text: getAIResponse(text) },
      ]);
      setTyping(false);
    }, 1000 + Math.random() * 800);
  }

  const prompts = [
    "what are your hobbies?",
    "tell me about your work",
    "what music do you like?",
    "are you single? 👀",
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end p-4 sm:p-6">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-freaky-dark/20 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Chat window */}
      <div className="animate-pop-in relative flex h-[520px] w-full max-w-md flex-col overflow-hidden rounded-2xl border-3 border-freaky-dark bg-bg shadow-[5px_5px_0_0] shadow-freaky-dark sm:h-[560px]">
        {/* Header */}
        <div className="flex items-center gap-3 border-b-3 border-freaky-dark bg-freaky-peach/40 px-4 py-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border-2 border-freaky-dark bg-freaky-yellow/40 text-lg">
            🎭
          </div>
          <div className="flex-1">
            <p className="font-display text-sm font-bold text-freaky-dark">
              {name}
            </p>
            <p className="font-mono text-[10px] text-text-muted">
              {username} · {platform} · AI PERSONA
            </p>
          </div>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg border-2 border-freaky-dark/20 text-freaky-dark/60 transition-colors hover:bg-freaky-red/10 hover:text-freaky-red"
          >
            ✕
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 space-y-2.5 overflow-y-auto p-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "system" ? (
                <div className="w-full rounded-xl border-2 border-dashed border-freaky-dark/15 bg-freaky-yellow/15 px-3 py-1.5 text-center font-display text-[10px] text-text-muted">
                  {msg.text}
                </div>
              ) : msg.role === "ai" ? (
                <div className="max-w-[85%] rounded-2xl rounded-tl-sm border-2 border-freaky-dark/15 bg-freaky-peach/25 px-3.5 py-2.5">
                  <p className="text-xs leading-relaxed text-freaky-dark">
                    {msg.text}
                  </p>
                </div>
              ) : (
                <div className="max-w-[85%] rounded-2xl rounded-tr-sm border-2 border-freaky-red bg-freaky-red px-3.5 py-2.5">
                  <p className="text-xs leading-relaxed text-white">
                    {msg.text}
                  </p>
                </div>
              )}
            </div>
          ))}

          {typing && (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-tl-sm border-2 border-freaky-dark/15 bg-freaky-peach/25 px-3.5 py-2.5">
                <div className="flex gap-1">
                  <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-freaky-dark/30" style={{ animationDelay: "0ms" }} />
                  <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-freaky-dark/30" style={{ animationDelay: "150ms" }} />
                  <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-freaky-dark/30" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        {/* Quick prompts */}
        <div className="flex gap-1.5 overflow-x-auto border-t border-freaky-dark/10 px-3 py-2">
          {prompts.map((p) => (
            <button
              key={p}
              onClick={() => setInput(p)}
              className="shrink-0 rounded-full border border-freaky-dark/15 bg-bg-card px-2.5 py-1 font-display text-[10px] font-bold text-text-muted hover:border-freaky-red/40 hover:text-freaky-red"
            >
              {p}
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="flex gap-2 border-t-2 border-freaky-dark/20 bg-bg-card px-3 py-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") send();
            }}
            placeholder="ask them anything..."
            className="flex-1 rounded-xl border-2 border-freaky-dark/20 bg-bg px-3 py-2 font-display text-xs font-bold text-freaky-dark placeholder:font-normal placeholder:text-text-muted focus:border-freaky-red/40 focus:outline-none"
          />
          <button
            onClick={send}
            disabled={!input.trim() || typing}
            className="rounded-xl border-2 border-freaky-dark bg-freaky-red px-3 py-2 font-display text-xs font-bold text-white transition-all hover:bg-freaky-red/90 disabled:opacity-40"
          >
            send
          </button>
        </div>
      </div>
    </div>
  );
}
