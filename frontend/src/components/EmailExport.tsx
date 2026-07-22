"use client";

import { useState } from "react";
import { api } from "@/lib/api";

type Phase = "idle" | "requesting" | "awaiting-code" | "confirming" | "sent" | "error";

export default function EmailExport({
  sessionId,
  onSessionPurged,
}: {
  sessionId: string;
  onSessionPurged: () => void;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [verificationToken, setVerificationToken] = useState("");
  const [error, setError] = useState("");
  const [mockMode, setMockMode] = useState(false);

  const requestCode = async () => {
    if (!email.trim()) return;
    setPhase("requesting");
    setError("");
    try {
      const result = await api.requestEmail(sessionId, email.trim());
      setVerificationToken(result.verification_token);
      setMockMode(result.mock_mode);
      setPhase("awaiting-code");
    } catch (e) {
      setError("Couldn't send a verification code. Please try again.");
      setPhase("error");
    }
  };

  const confirmAndSend = async () => {
    if (!code.trim()) return;
    setPhase("confirming");
    setError("");
    try {
      await api.confirmEmail(sessionId, verificationToken, code.trim());
      setPhase("sent");
      onSessionPurged();
    } catch (e) {
      setError("That code didn't match, or it expired. You can request a new one.");
      setPhase("awaiting-code");
    }
  };

  if (phase === "sent") {
    return (
      <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-900">
        Sent — this session's data has been deleted from our cache.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4">
      <p className="mb-2 text-sm font-medium text-stone-700">
        Want a copy of this conversation and your recommendations?
      </p>
      <p className="mb-3 text-xs text-stone-500">
        We only ask for your email if you choose to send yourself this summary. Nothing is
        stored after it's sent.
      </p>

      {phase === "idle" || phase === "requesting" || phase === "error" ? (
        <div className="flex gap-2">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="flex-1 rounded-full border border-stone-300 px-3 py-1.5 text-sm focus:border-emerald-500 focus:outline-none"
          />
          <button
            onClick={requestCode}
            disabled={phase === "requesting" || !email.trim()}
            className="rounded-full bg-emerald-600 px-4 py-1.5 text-sm text-white disabled:opacity-40"
          >
            {phase === "requesting" ? "Sending..." : "Email me this"}
          </button>
        </div>
      ) : (
        <div className="flex gap-2">
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder={mockMode ? "Check the server console for your code" : "Enter the code we sent"}
            className="flex-1 rounded-full border border-stone-300 px-3 py-1.5 text-sm focus:border-emerald-500 focus:outline-none"
          />
          <button
            onClick={confirmAndSend}
            disabled={phase === "confirming" || !code.trim()}
            className="rounded-full bg-stone-900 px-4 py-1.5 text-sm text-white disabled:opacity-40"
          >
            {phase === "confirming" ? "Sending..." : "Confirm and send"}
          </button>
        </div>
      )}

      {error && <p className="mt-2 text-xs text-rose-600">{error}</p>}
    </div>
  );
}
