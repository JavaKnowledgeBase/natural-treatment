"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";

type Phase = "idle" | "requesting" | "awaiting-code" | "confirming" | "sent" | "error";

export default function EmailExport({
  sessionId,
  onSessionPurged,
}: {
  sessionId: string;
  onSessionPurged: () => void;
}) {
  const t = useTranslations("EmailExport");
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
      setError(t("errorRequest"));
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
      setError(t("errorConfirm"));
      setPhase("awaiting-code");
    }
  };

  if (phase === "sent") {
    return (
      <div className="rounded-xl border border-brand-200 bg-brand-50 p-4 text-sm text-brand-900 shadow-card">
        {t("sentMessage")}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-brand-100 bg-white p-4 shadow-card">
      <p className="mb-2 text-sm font-medium text-stone-700">{t("prompt")}</p>
      <p className="mb-3 text-xs text-stone-500">{t("privacyNote")}</p>

      {phase === "idle" || phase === "requesting" || phase === "error" ? (
        <div className="flex gap-2">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t("emailPlaceholder")}
            className="flex-1 rounded-full border border-stone-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          <button
            onClick={requestCode}
            disabled={phase === "requesting" || !email.trim()}
            className="rounded-full bg-brand-700 px-4 py-1.5 text-sm font-medium text-white shadow-card transition-colors hover:bg-brand-800 disabled:opacity-40"
          >
            {phase === "requesting" ? t("sending") : t("sendMe")}
          </button>
        </div>
      ) : (
        <div className="flex gap-2">
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder={mockMode ? t("codePlaceholderMock") : t("codePlaceholder")}
            className="flex-1 rounded-full border border-stone-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          <button
            onClick={confirmAndSend}
            disabled={phase === "confirming" || !code.trim()}
            className="rounded-full bg-brand-900 px-4 py-1.5 text-sm font-medium text-white shadow-card transition-colors hover:bg-brand-800 disabled:opacity-40"
          >
            {phase === "confirming" ? t("sending") : t("confirmAndSend")}
          </button>
        </div>
      )}

      {error && <p className="mt-2 text-xs text-rose-600">{error}</p>}
    </div>
  );
}
