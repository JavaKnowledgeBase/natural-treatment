"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ChatMessage, Suggestion } from "@/lib/api";
import EmailExport from "./EmailExport";
import LanguagePicker from "./LanguagePicker";

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-brand-700 text-white shadow-card"
            : "border border-brand-100 bg-white text-stone-800 shadow-card"
        }`}
      >
        {message.text}
      </div>
    </div>
  );
}

function ConfirmDone({
  question,
  keepGoingLabel,
  confirmLabel,
  onKeepGoing,
  onConfirm,
  confirming,
}: {
  question: string;
  keepGoingLabel: string;
  confirmLabel: string;
  onKeepGoing: () => void;
  onConfirm: () => void;
  confirming: boolean;
}) {
  return (
    <div className="rounded-xl border border-gold-200 bg-gold-50 p-3">
      <p className="text-sm text-gold-700">{question}</p>
      <div className="mt-2 flex gap-2">
        <button
          onClick={onKeepGoing}
          className="rounded-full border border-gold-300 bg-white px-3 py-1.5 text-xs font-medium text-gold-700 transition-colors hover:bg-gold-100"
        >
          {keepGoingLabel}
        </button>
        <button
          onClick={onConfirm}
          disabled={confirming}
          className="rounded-full bg-brand-700 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-brand-800 disabled:opacity-50"
        >
          {confirmLabel}
        </button>
      </div>
    </div>
  );
}

const MIN_SYMPTOMS_BEFORE_ADVANCE = 2;

export default function ChatPanel({
  sessionId,
  messages,
  suggestions,
  step,
  sending,
  analyzing,
  symptomCount,
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
  symptomCount: number;
  canAnalyze: boolean;
  onSend: (text: string) => void;
  onPickSuggestion: (s: Suggestion) => void;
  onAdvanceToCauses: () => void;
  onAnalyze: () => void;
  onSessionPurged: () => void;
}) {
  const t = useTranslations("ChatPanel");
  const [draft, setDraft] = useState("");
  const [confirmAdvance, setConfirmAdvance] = useState(false);
  const [confirmAnalyze, setConfirmAnalyze] = useState(false);

  const submit = () => {
    const text = draft.trim();
    if (!text || sending) return;
    setConfirmAdvance(false);
    setConfirmAnalyze(false);
    onSend(text);
    setDraft("");
  };

  const pickSuggestion = (s: Suggestion) => {
    setConfirmAdvance(false);
    setConfirmAnalyze(false);
    onPickSuggestion(s);
  };

  const canChat = step === "greeting" || step === "symptom_collection" || step === "cause_collection";
  const canShowStickyButton = (step === "symptom_collection" || step === "cause_collection") && canAnalyze;

  return (
    <div className="flex h-full flex-col bg-paper-100">
      <div className="flex-1 space-y-3 overflow-y-auto p-6">
        {messages.map((m, i) => (
          <div key={i}>
            <MessageBubble message={m} />
            {i === 0 && <LanguagePicker />}
          </div>
        ))}

        {suggestions.length > 0 && canChat && (
          <div className="flex flex-wrap gap-2 pt-2">
            {suggestions.map((s, i) => (
              <button
                key={`${s.label}-${i}`}
                onClick={() => pickSuggestion(s)}
                className="rounded-full border border-brand-300 bg-white px-3 py-1 text-sm text-brand-800 shadow-card transition-colors hover:border-brand-400 hover:bg-brand-50"
              >
                + {s.label}
              </button>
            ))}
          </div>
        )}

        {step === "symptom_collection" && (
          <div className="pt-2">
            {symptomCount < MIN_SYMPTOMS_BEFORE_ADVANCE ? (
              <p className="text-xs text-stone-400">
                {symptomCount === 0 ? t("shareMoreZero") : t("shareMoreOne")}
              </p>
            ) : confirmAdvance ? (
              <ConfirmDone
                question={t("advanceConfirmQuestion")}
                keepGoingLabel={t("keepGoing")}
                confirmLabel={t("advanceConfirm")}
                confirming={false}
                onKeepGoing={() => setConfirmAdvance(false)}
                onConfirm={() => {
                  setConfirmAdvance(false);
                  onAdvanceToCauses();
                }}
              />
            ) : (
              <button
                onClick={() => setConfirmAdvance(true)}
                className="text-sm font-medium text-brand-700 underline decoration-brand-300 underline-offset-2 hover:text-brand-800"
              >
                {t("advanceLink")}
              </button>
            )}
          </div>
        )}

        {step === "results" && (
          <div className="pt-4">
            <EmailExport sessionId={sessionId} onSessionPurged={onSessionPurged} />
          </div>
        )}
      </div>

      {canChat && (
        <div className="border-t border-brand-100 bg-white p-4">
          <div className="flex gap-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder={step === "cause_collection" ? t("placeholderCause") : t("placeholderSymptom")}
              className="flex-1 rounded-full border border-stone-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
            <button
              onClick={submit}
              disabled={sending || !draft.trim()}
              className="rounded-full bg-brand-700 px-5 py-2 text-sm font-medium text-white shadow-card transition-colors hover:bg-brand-800 disabled:opacity-40"
            >
              {t("send")}
            </button>
          </div>
        </div>
      )}

      {canShowStickyButton && (
        <div className="sticky bottom-0 border-t border-brand-100 bg-white p-4">
          {confirmAnalyze ? (
            <ConfirmDone
              question={
                step === "cause_collection"
                  ? t("analyzeConfirmQuestionCauses")
                  : t("analyzeConfirmQuestionSymptoms")
              }
              keepGoingLabel={t("keepGoing")}
              confirmLabel={analyzing ? t("analyzing") : t("analyzeConfirm")}
              confirming={analyzing}
              onKeepGoing={() => setConfirmAnalyze(false)}
              onConfirm={() => {
                onAnalyze();
              }}
            />
          ) : (
            <button
              onClick={() => setConfirmAnalyze(true)}
              disabled={analyzing}
              className="w-full rounded-full bg-brand-900 py-3 text-sm font-medium tracking-wide text-white shadow-card transition-colors hover:bg-brand-800 disabled:opacity-50"
            >
              {analyzing ? t("analyzing") : t("analyzeButton")}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
