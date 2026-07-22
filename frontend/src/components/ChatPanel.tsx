"use client";

import { useState } from "react";
import { ChatMessage, Suggestion } from "@/lib/api";
import EmailExport from "./EmailExport";

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${
          isUser ? "bg-emerald-600 text-white" : "bg-white text-stone-800 border border-stone-200"
        }`}
      >
        {message.text}
      </div>
    </div>
  );
}

export default function ChatPanel({
  sessionId,
  messages,
  suggestions,
  step,
  sending,
  analyzing,
  canAnalyze,
  onSend,
  onPickSuggestion,
  onAdvanceToCauses,
  onAnalyze,
  onSessionPurged,
}: {
  sessionId: string;
  messages: ChatMessage[];
  suggestions: Suggestion[];
  step: string;
  sending: boolean;
  analyzing: boolean;
  canAnalyze: boolean;
  onSend: (text: string) => void;
  onPickSuggestion: (s: Suggestion) => void;
  onAdvanceToCauses: () => void;
  onAnalyze: () => void;
  onSessionPurged: () => void;
}) {
  const [draft, setDraft] = useState("");

  const submit = () => {
    const text = draft.trim();
    if (!text || sending) return;
    onSend(text);
    setDraft("");
  };

  const canChat = step === "greeting" || step === "symptom_collection" || step === "cause_collection";
  const canShowStickyButton = (step === "symptom_collection" || step === "cause_collection") && canAnalyze;

  return (
    <div className="flex h-full flex-col bg-stone-100">
      <div className="flex-1 space-y-3 overflow-y-auto p-6">
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}

        {suggestions.length > 0 && canChat && (
          <div className="flex flex-wrap gap-2 pt-2">
            {suggestions.map((s, i) => (
              <button
                key={`${s.label}-${i}`}
                onClick={() => onPickSuggestion(s)}
                className="rounded-full border border-emerald-400 bg-white px-3 py-1 text-sm text-emerald-700 hover:bg-emerald-50"
              >
                + {s.label}
              </button>
            ))}
          </div>
        )}

        {step === "symptom_collection" && (
          <div className="pt-2">
            <button
              onClick={onAdvanceToCauses}
              className="text-sm text-stone-500 underline hover:text-stone-700"
            >
              I've said everything about my symptoms — let's talk about possible causes
            </button>
          </div>
        )}

        {step === "results" && (
          <div className="pt-4">
            <EmailExport sessionId={sessionId} onSessionPurged={onSessionPurged} />
          </div>
        )}
      </div>

      {canChat && (
        <div className="border-t border-stone-200 bg-white p-4">
          <div className="flex gap-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder={
                step === "cause_collection"
                  ? "What might have contributed to this?"
                  : "Tell me how you're feeling..."
              }
              className="flex-1 rounded-full border border-stone-300 px-4 py-2 text-sm focus:border-emerald-500 focus:outline-none"
            />
            <button
              onClick={submit}
              disabled={sending || !draft.trim()}
              className="rounded-full bg-emerald-600 px-4 py-2 text-sm text-white disabled:opacity-40"
            >
              Send
            </button>
          </div>
        </div>
      )}

      {canShowStickyButton && (
        <div className="sticky bottom-0 border-t border-stone-200 bg-white p-4">
          <button
            onClick={onAnalyze}
            disabled={analyzing}
            className="w-full rounded-full bg-stone-900 py-3 text-sm font-medium text-white hover:bg-stone-800 disabled:opacity-50"
          >
            {analyzing ? "Analyzing..." : "I have said everything I know now — analyze and give me suggestions"}
          </button>
        </div>
      )}
    </div>
  );
}
