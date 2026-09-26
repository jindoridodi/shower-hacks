"use client";

import { useEffect, useRef, useState } from "react";

type Message = {
  id: string;
  role: "user" | "ai" | "system";
  text: string;
};

const PERSONA = {
  name: "Avery Chen",
  username: "@avery.chen.pdx",
  avatar: "🧑‍🎨",
  vibe: "designer, archivist, portland-based community storyteller",
  traits: [
    "obsessed with public archives",
    "design nerd",
    "portland loyalist",
    "probably owns too many tote bags",
    "uses the word 'praxis' unironically",
  ],
};

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

function getAIResponse(userMessage: string): string {
  const lower = userMessage.toLowerCase();
  if (lower.includes("hobby") || lower.includes("archive") || lower.includes("project") || lower.includes("interest"))
    return AI_RESPONSES.hobby;
  if (lower.includes("work") || lower.includes("job") || lower.includes("career") || lower.includes("research"))
    return AI_RESPONSES.work;
  if (lower.includes("portland") || lower.includes("city") || lower.includes("live") || lower.includes("where"))
    return AI_RESPONSES.portland;
  if (lower.includes("music") || lower.includes("listen") || lower.includes("song") || lower.includes("playlist"))
    return AI_RESPONSES.music;
  if (lower.includes("food") || lower.includes("eat") || lower.includes("restaurant") || lower.includes("cook"))
    return AI_RESPONSES.food;
  if (lower.includes("dating") || lower.includes("single") || lower.includes("relationship") || lower.includes("love"))
    return AI_RESPONSES.dating;
  return AI_RESPONSES.default;
}

export default function PersonaPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "sys-1",
      role: "system",
      text: `you're now chatting with an AI pretending to be ${PERSONA.name}. everything it says is generated from their public data. don't be weird... or do 🫣`,
    },
    {
      id: "ai-1",
      role: "ai",
      text: AI_RESPONSES.default,
    },
  ]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  function sendMessage() {
    const text = input.trim();
    if (!text || typing) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      text,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setTyping(true);

    setTimeout(() => {
      const aiMsg: Message = {
        id: `ai-${Date.now()}`,
        role: "ai",
        text: getAIResponse(text),
      };
      setMessages((prev) => [...prev, aiMsg]);
      setTyping(false);
    }, 1200 + Math.random() * 800);
  }

  const prompts = [
    "what are your hobbies?",
    "tell me about your work",
    "what's portland like?",
    "what music do you listen to?",
    "are you single? 👀",
  ];

  return (
    <main className="mx-auto flex max-w-3xl flex-col px-6 py-8" style={{ height: "calc(100vh - 4rem)" }}>
      {/* Persona header */}
      <div className="mb-4 flex items-center gap-4 rounded-2xl border-3 border-freaky-dark bg-bg-card p-4 shadow-[3px_3px_0_0] shadow-freaky-dark">
        <div className="flex h-14 w-14 items-center justify-center rounded-xl border-2 border-freaky-dark bg-freaky-peach text-2xl">
          {PERSONA.avatar}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="font-display text-xl font-bold text-freaky-dark">
              {PERSONA.name}
            </h1>
            <span className="rounded-full bg-freaky-red px-2 py-0.5 text-[10px] font-bold text-white">
              AI PERSONA
            </span>
          </div>
          <p className="text-sm text-text-secondary">{PERSONA.vibe}</p>
        </div>
        <div className="animate-wiggle text-2xl">🎭</div>
      </div>

      {/* Traits */}
      <div className="mb-4 flex flex-wrap gap-2">
        {PERSONA.traits.map((trait) => (
          <span
            key={trait}
            className="rounded-full border-2 border-freaky-dark/20 bg-freaky-yellow/30 px-3 py-1 font-display text-xs font-bold text-freaky-dark"
          >
            {trait}
          </span>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-3 overflow-y-auto rounded-2xl border-3 border-freaky-dark bg-bg-card p-4 shadow-[3px_3px_0_0] shadow-freaky-dark">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "system" ? (
              <div className="w-full rounded-xl border-2 border-dashed border-freaky-dark/20 bg-freaky-yellow/20 px-4 py-2 text-center font-display text-xs text-text-secondary">
                {msg.text}
              </div>
            ) : msg.role === "ai" ? (
              <div className="flex max-w-[80%] items-start gap-2">
                <span className="mt-1 text-lg">{PERSONA.avatar}</span>
                <div className="rounded-2xl rounded-tl-sm border-2 border-freaky-dark/20 bg-freaky-peach/30 px-4 py-3">
                  <p className="text-sm leading-relaxed text-freaky-dark">
                    {msg.text}
                  </p>
                </div>
              </div>
            ) : (
              <div className="max-w-[80%] rounded-2xl rounded-tr-sm border-2 border-freaky-red bg-freaky-red px-4 py-3">
                <p className="text-sm leading-relaxed text-white">{msg.text}</p>
              </div>
            )}
          </div>
        ))}

        {typing && (
          <div className="flex items-start gap-2">
            <span className="mt-1 text-lg">{PERSONA.avatar}</span>
            <div className="rounded-2xl rounded-tl-sm border-2 border-freaky-dark/20 bg-freaky-peach/30 px-4 py-3">
              <div className="flex gap-1">
                <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-freaky-dark/40" style={{ animationDelay: "0ms" }} />
                <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-freaky-dark/40" style={{ animationDelay: "150ms" }} />
                <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-freaky-dark/40" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Prompt suggestions */}
      <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
        {prompts.map((prompt) => (
          <button
            key={prompt}
            onClick={() => {
              setInput(prompt);
            }}
            className="shrink-0 rounded-full border-2 border-freaky-dark/20 bg-bg-card px-3 py-1.5 font-display text-xs font-bold text-text-secondary transition-all hover:border-freaky-red hover:bg-freaky-red/5 hover:text-freaky-red"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="mt-3 flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") sendMessage();
          }}
          placeholder="ask them anything... 👀"
          className="flex-1 rounded-2xl border-3 border-freaky-dark bg-bg-card px-5 py-3 font-display text-sm font-bold text-freaky-dark shadow-[3px_3px_0_0] shadow-freaky-dark placeholder:font-normal placeholder:text-text-muted focus:shadow-[4px_4px_0_0] focus:shadow-freaky-red focus:outline-none"
        />
        <button
          onClick={sendMessage}
          disabled={!input.trim() || typing}
          className="rounded-2xl border-3 border-freaky-dark bg-freaky-red px-5 py-3 font-display font-bold text-white shadow-[3px_3px_0_0] shadow-freaky-dark transition-all hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[1px_1px_0_0] hover:shadow-freaky-dark disabled:opacity-50"
        >
          send 💬
        </button>
      </div>
    </main>
  );
}
