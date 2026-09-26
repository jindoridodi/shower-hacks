"use client";

import { useState } from "react";

type LetterStyle = "romantic" | "unhinged" | "poetic" | "chaotic";

type GeneratedLetter = {
  id: string;
  style: LetterStyle;
  recipient: string;
  content: string;
  subject: string;
};

const STYLE_CONFIG: Record<
  LetterStyle,
  { label: string; emoji: string; color: string; description: string }
> = {
  romantic: {
    label: "Romantic",
    emoji: "💕",
    color: "border-freaky-pink bg-freaky-pink/10 text-freaky-pink",
    description: "sweet, sincere, butterflies-in-stomach energy",
  },
  unhinged: {
    label: "Unhinged",
    emoji: "🤪",
    color: "border-freaky-red bg-freaky-red/10 text-freaky-red",
    description: "absolutely feral, no filter, chaotic devotion",
  },
  poetic: {
    label: "Poetic",
    emoji: "🌙",
    color: "border-freaky-purple bg-freaky-purple/10 text-freaky-purple",
    description: "literary, metaphor-heavy, artsy yearning",
  },
  chaotic: {
    label: "Chaotic Neutral",
    emoji: "🎪",
    color: "border-freaky-blue bg-freaky-blue/10 text-freaky-blue",
    description: "memes, inside jokes, gen z brain rot",
  },
};

const SAMPLE_LETTERS: Record<LetterStyle, Omit<GeneratedLetter, "id" | "recipient">> = {
  romantic: {
    style: "romantic",
    subject: "I've been thinking about you",
    content: `Dear Avery,

I know this might seem forward, but I've been following your work with public archives and I have to say... the way you talk about community storytelling? It does something to my heart.

The Neighborhood Memory Map project you did in 2024 — combining oral histories with old photographs — that's not just design work. That's someone who sees beauty in the stories people leave behind. And I think that's incredibly attractive.

I'd love to get a coffee sometime and hear about the Open Archives Symposium. Or honestly, I'd listen to you talk about spreadsheets all day.

With admiration (and a little bit of a crush),
A secret admirer 💕

P.S. I also live in Portland. What if we've already passed each other at a food cart?`,
  },
  unhinged: {
    style: "unhinged",
    subject: "I am UNWELL about you",
    content: `AVERY CHEN.

I have looked at your portfolio website SEVENTEEN times today. SEVENTEEN. Do you know what that does to a person?? Your typography choices alone have me in a CHOKEHOLD.

The way you described the Neighborhood Memory Map as "combining oral histories with photographs from local public collections" — I SCREAMED. I actually screamed out loud in a coffee shop. People stared. I don't care. YOU GET IT.

And your Open Archives Symposium talk??? "Designing With Public Records"??? I would walk through RAIN (Portland rain, the relentless kind) for that title alone.

I'm not saying I would reorganize my entire Spotify around your research interests but I absolutely already did that. My "archiving in the mist" playlist goes HARD and it's all for you.

Please acknowledge my existence,
Someone who needs professional help 🫠

P.S. I made a spreadsheet ranking your projects by how much they made me feel things. The Neighborhood Memory Map is #1. Everything is #1.`,
  },
  poetic: {
    style: "poetic",
    subject: "On archives and longing",
    content: `Avery,

There is a kind of tenderness in the way you handle other people's memories — as though each photograph, each oral history, is a small animal you've been asked to hold.

I think about the Neighborhood Memory Map and I see you there, somewhere between the past and the present, building bridges out of the things we almost forgot to keep.

Portland gives you rain and you give it back stories. That feels like a fair exchange, or maybe the most unfair one — because you're clearly giving more.

At the symposium, you stood before a room and said: here is what we found. Here is what we don't know. And the courage of that second sentence — the honest admission of gaps — that's where I fell.

Not into love, exactly. Into attention. The kind that doesn't look away.

I wonder what you'd think if you knew someone out here was reading your work like poetry, finding meter in your metadata, rhyme in your research notes.

Probably you'd laugh. I hope you'd laugh.

In the rain, thinking of archives,
An anonymous reader 🌙`,
  },
  chaotic: {
    style: "chaotic",
    subject: "no thoughts just vibes (and u)",
    content: `yo avery

ok so hear me out

you: *posts about public archives*
me: 🧎‍♂️

you: *makes a whole project called Neighborhood Memory Map*
me: is this a marriage proposal??

real talk tho your work is fire. like you really said "I'm gonna take old photos and oral histories and make people FEEL things" and then you just... DID THAT??? the audacity. the RANGE.

and presenting at the Open Archives Symposium?? babe that's not a talk that's a TED talk for people who actually care about things. huge W.

i made you a tier list:
- S tier: your design work, your research, your Portland food cart opinions
- A tier: everything else about you
- F tier: the fact that I don't know you irl

anyway this is my application to be your favorite internet weirdo. references available upon request (they are all screenshots of your portfolio).

sending this from a food cart on Hawthorne (probably the same one you go to??),
your biggest fan (gender neutral) 🎪

tl;dr: you're cool and I'm normal about it (lie)`,
  },
};

export default function LoveLettersPage() {
  const [selectedStyle, setSelectedStyle] = useState<LetterStyle | null>(null);
  const [recipientName, setRecipientName] = useState("Avery Chen");
  const [generating, setGenerating] = useState(false);
  const [letter, setLetter] = useState<GeneratedLetter | null>(null);
  const [copied, setCopied] = useState(false);

  function generateLetter() {
    if (!selectedStyle || !recipientName.trim()) return;
    setGenerating(true);
    setLetter(null);

    setTimeout(() => {
      const template = SAMPLE_LETTERS[selectedStyle];
      setLetter({
        id: `letter-${Date.now()}`,
        recipient: recipientName,
        ...template,
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

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      {/* Header */}
      <div className="mb-10 text-center">
        <div className="mb-4 inline-block animate-float text-5xl">💌</div>
        <h1 className="mb-2 font-display text-4xl font-bold text-freaky-dark">
          love letter{" "}
          <span className="inline-block animate-wiggle text-freaky-pink">
            generator
          </span>
        </h1>
        <p className="font-body text-text-secondary">
          craft the perfect message based on what we know about them 💘
        </p>
      </div>

      {/* Recipient */}
      <div className="mb-8">
        <label className="mb-2 block font-display text-sm font-bold text-freaky-dark">
          who&apos;s the lucky person? 👀
        </label>
        <input
          type="text"
          value={recipientName}
          onChange={(e) => setRecipientName(e.target.value)}
          placeholder="their name..."
          className="w-full rounded-2xl border-3 border-freaky-dark bg-bg-card px-5 py-3 font-display text-sm font-bold text-freaky-dark shadow-[3px_3px_0_0] shadow-freaky-dark placeholder:font-normal placeholder:text-text-muted focus:shadow-[4px_4px_0_0] focus:shadow-freaky-pink focus:outline-none"
        />
      </div>

      {/* Style selector */}
      <div className="mb-8">
        <label className="mb-3 block font-display text-sm font-bold text-freaky-dark">
          pick your vibe ✨
        </label>
        <div className="grid grid-cols-2 gap-3">
          {(Object.entries(STYLE_CONFIG) as [LetterStyle, typeof STYLE_CONFIG[LetterStyle]][]).map(
            ([style, config]) => (
              <button
                key={style}
                onClick={() => setSelectedStyle(style)}
                className={`rounded-2xl border-3 p-4 text-left transition-all ${
                  selectedStyle === style
                    ? `${config.color} shadow-[4px_4px_0_0] shadow-current`
                    : "border-freaky-dark/20 bg-bg-card hover:border-freaky-dark/40"
                }`}
              >
                <div className="mb-1 flex items-center gap-2">
                  <span className="text-xl">{config.emoji}</span>
                  <span className="font-display text-base font-bold text-freaky-dark">
                    {config.label}
                  </span>
                </div>
                <p className="text-xs text-text-secondary">
                  {config.description}
                </p>
              </button>
            ),
          )}
        </div>
      </div>

      {/* Generate button */}
      <div className="mb-10 text-center">
        <button
          onClick={generateLetter}
          disabled={!selectedStyle || !recipientName.trim() || generating}
          className="inline-flex items-center gap-2 rounded-2xl border-3 border-freaky-dark bg-freaky-pink px-8 py-4 font-display text-lg font-bold text-white shadow-[4px_4px_0_0] shadow-freaky-dark transition-all hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0_0] hover:shadow-freaky-dark disabled:opacity-50"
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

      {/* Generated letter */}
      {letter && (
        <div className="animate-pop-in">
          {/* Letter envelope effect */}
          <div className="mb-6 overflow-hidden rounded-2xl border-3 border-freaky-dark shadow-[4px_4px_0_0] shadow-freaky-dark">
            {/* Letter header */}
            <div className="flex items-center justify-between border-b-3 border-freaky-dark bg-freaky-peach/40 px-5 py-3">
              <div className="flex items-center gap-2">
                <span className="text-lg">
                  {STYLE_CONFIG[letter.style].emoji}
                </span>
                <div>
                  <p className="font-display text-xs font-bold text-text-secondary">
                    TO: {letter.recipient}
                  </p>
                  <p className="font-display text-sm font-bold text-freaky-dark">
                    {letter.subject}
                  </p>
                </div>
              </div>
              <span
                className={`rounded-full border-2 px-3 py-1 font-display text-[10px] font-bold ${STYLE_CONFIG[letter.style].color}`}
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

            {/* Letter footer */}
            <div className="flex items-center justify-between border-t-3 border-freaky-dark bg-freaky-peach/20 px-5 py-3">
              <p className="font-display text-[10px] font-bold text-text-muted">
                AI-GENERATED · BASED ON PUBLIC DATA ONLY · REVIEW BEFORE SENDING
              </p>
              <button
                onClick={copyLetter}
                className="rounded-full border-2 border-freaky-dark px-4 py-1.5 font-display text-xs font-bold text-freaky-dark transition-all hover:bg-freaky-dark hover:text-white"
              >
                {copied ? "copied! ✅" : "copy 📋"}
              </button>
            </div>
          </div>

          {/* Warning */}
          <div className="rounded-2xl border-2 border-dashed border-freaky-red/40 bg-freaky-red/5 px-5 py-3 text-center">
            <p className="font-display text-xs font-bold text-freaky-red">
              🚨 this is AI-generated satire based on public data. don&apos;t
              actually send this to someone without their consent. be cool. 🚨
            </p>
          </div>
        </div>
      )}

      {/* Fun footer */}
      {!letter && !generating && (
        <div className="mt-12 text-center">
          <p className="font-display text-sm text-text-muted">
            all letters are generated from publicly available information only.
            <br />
            no private data. no real feelings. just vibes. 🫶
          </p>
        </div>
      )}
    </main>
  );
}
