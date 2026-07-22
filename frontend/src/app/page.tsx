"use client";

import { useEffect, useState } from "react";
import { api, CachedItem, ChatMessage, Recommendation, Suggestion } from "@/lib/api";
import SummaryPanel from "@/components/SummaryPanel";
import ChatPanel from "@/components/ChatPanel";

export default function Home() {
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
      .createSession()
      .then((res) => {
        setSessionId(res.session_id);
        setMessages([{ role: "assistant", text: res.greeting, ts: Date.now() / 1000 }]);
      })
      .catch(() => setInitError("Couldn't reach the backend. Is docker-compose running?"));
  }, []);

  const handleSend = async (text: string) => {
    if (!sessionId) return;
    setMessages((prev) => [...prev, { role: "user", text, ts: Date.now() / 1000 }]);
    setSending(true);
    try {
      const res = await api.sendMessage(sessionId, text);
      setStep(res.current_step);
      setSymptoms(res.symptoms);
      setCauses(res.causes);
      setSuggestions(res.suggestions as Suggestion[]);
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
      <div className="flex h-full items-center justify-center bg-stone-50 text-center">
        <div className="max-w-md rounded-lg border border-emerald-200 bg-white p-8 shadow-sm">
          <h1 className="text-lg font-semibold text-stone-800">Session complete</h1>
          <p className="mt-2 text-sm text-stone-600">
            Your summary was sent, and everything from this session has been deleted from our cache.
            Refresh this page to start a new, separate session.
          </p>
        </div>
      </div>
    );
  }

  if (!sessionId) {
    return <div className="flex h-full items-center justify-center text-stone-400">Starting a new session...</div>;
  }

  return (
    <main className="flex h-full w-full">
      <div className="hidden w-1/2 border-r border-stone-200 md:block">
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
          canAnalyze={symptoms.length > 0 || causes.length > 0}
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
