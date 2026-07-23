"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { api, CachedItem, ChatMessage, Recommendation, Suggestion } from "@/lib/api";
import SummaryPanel from "@/components/SummaryPanel";
import ChatPanel from "@/components/ChatPanel";

export default function Home() {
  const locale = useLocale();
  const t = useTranslations("Home");

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [step, setStep] = useState("greeting");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [symptoms, setSymptoms] = useState<CachedItem[]>([]);
  const [causes, setCauses] = useState<CachedItem[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [sending, setSending] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [purged, setPurged] = useState(false);
  const [initError, setInitError] = useState("");

  useEffect(() => {
    api
      .createSession(locale)
      .then((res) => {
        setSessionId(res.session_id);
        setMessages([{ role: "assistant", text: res.greeting, ts: Date.now() / 1000 }]);
      })
      .catch(() => setInitError(t("initError")));
  }, [locale, t]);

  const handleSend = async (text: string) => {
    if (!sessionId) return;
    setMessages((prev) => [...prev, { role: "user", text, ts: Date.now() / 1000 }]);
    setSending(true);
    try {
      const res = await api.sendMessage(sessionId, text);
      setStep(res.current_step);
      setSymptoms(res.symptoms);
      setCauses(res.causes);
      setSuggestions(res.suggestions);
      setMessages((prev) => [...prev, { role: "assistant", text: res.assistant_message, ts: Date.now() / 1000 }]);
    } finally {
      setSending(false);
    }
  };

  const handlePickSuggestion = async (s: Suggestion) => {
    if (!sessionId) return;
    const kind = step === "cause_collection" ? "cause" : "symptom";
    await api.addItem(sessionId, kind, s.label, s.id, s.category);
    const state = await api.getState(sessionId);
    setSymptoms(state.symptoms);
    setCauses(state.causes);
    setSuggestions((prev) => prev.filter((x) => x.label !== s.label));
  };

  const handleRemoveSymptom = async (id: string) => {
    if (!sessionId) return;
    await api.removeItem(sessionId, "symptom", id);
    setSymptoms((prev) => prev.filter((s) => s.id !== id));
  };

  const handleRemoveCause = async (id: string) => {
    if (!sessionId) return;
    await api.removeItem(sessionId, "cause", id);
    setCauses((prev) => prev.filter((c) => c.id !== id));
  };

  const handleAdvanceToCauses = async () => {
    if (!sessionId) return;
    const res = await api.advanceToCauses(sessionId);
    setStep(res.current_step);
    setSuggestions([]);
    setMessages((prev) => [...prev, { role: "assistant", text: res.assistant_message, ts: Date.now() / 1000 }]);
  };

  const handleAnalyze = async () => {
    if (!sessionId) return;
    setAnalyzing(true);
    try {
      const res = await api.analyze(sessionId);
      setStep(res.current_step);
      setRecommendations(res.recommendations);
      if (res.reasoning) {
        setMessages((prev) => [...prev, { role: "assistant", text: res.reasoning as string, ts: Date.now() / 1000 }]);
      }
    } finally {
      setAnalyzing(false);
    }
  };

  if (initError) {
    return <div className="flex h-full items-center justify-center text-stone-500">{initError}</div>;
  }

  if (purged) {
    return (
      <div className="flex h-full items-center justify-center bg-paper text-center">
        <div className="max-w-md rounded-2xl border border-brand-100 bg-white p-8 shadow-panel">
          <h1 className="font-serif text-xl font-semibold text-brand-900">{t("purgedTitle")}</h1>
          <p className="mt-2 text-sm text-stone-600">{t("purgedBody")}</p>
        </div>
      </div>
    );
  }

  if (!sessionId) {
    return <div className="flex h-full items-center justify-center text-stone-400">{t("startingSession")}</div>;
  }

  return (
    <main className="flex h-full w-full bg-paper">
      <div className="hidden w-1/2 border-r border-brand-100 md:block">
        <SummaryPanel
          step={step}
          symptoms={symptoms}
          causes={causes}
          recommendations={recommendations}
          onRemoveSymptom={handleRemoveSymptom}
          onRemoveCause={handleRemoveCause}
        />
      </div>
      <div className="w-full md:w-1/2">
        <ChatPanel
          sessionId={sessionId}
          messages={messages}
          suggestions={suggestions}
          step={step}
          sending={sending}
          analyzing={analyzing}
          symptomCount={symptoms.length}
          canAnalyze={symptoms.length >= 2}
          onSend={handleSend}
          onPickSuggestion={handlePickSuggestion}
          onAdvanceToCauses={handleAdvanceToCauses}
          onAnalyze={handleAnalyze}
          onSessionPurged={() => setPurged(true)}
        />
      </div>
    </main>
  );
}
