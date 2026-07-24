"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { herbDetails } from "@/data/herbDetails";
import { api } from "@/lib/api";

type ContactPhase = "idle" | "sending" | "sent" | "error";

export default function HerbDetailModal({
  herbId,
  herbName,
  onClose,
}: {
  herbId: string;
  herbName: string;
  onClose: () => void;
}) {
  const t = useTranslations("HerbDetail");
  const detail = herbDetails[herbId];

  const [showContactForm, setShowContactForm] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [phase, setPhase] = useState<ContactPhase>("idle");

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  if (!detail) return null;

  const submitContact = async () => {
    if (!email.trim()) return;
    setPhase("sending");
    try {
      await api.contact(herbName, email.trim(), message.trim(), name.trim() || undefined);
      setPhase("sent");
    } catch {
      setPhase("error");
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-brand-950/40 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-brand-100 bg-white p-6 shadow-panel"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={herbName}
      >
        <div className="flex items-start justify-between gap-4">
          <h2 className="font-serif text-xl font-semibold text-brand-900">{herbName}</h2>
          <button
            onClick={onClose}
            aria-label={t("close")}
            className="shrink-0 text-lg leading-none text-stone-400 transition-colors hover:text-stone-700"
          >
            ×
          </button>
        </div>

        <section className="mt-4">
          <p className="text-xs font-medium uppercase tracking-wider text-brand-600">{t("historyTitle")}</p>
          <p className="mt-1 text-sm leading-relaxed text-stone-600">{detail.history}</p>
        </section>

        <section className="mt-4">
          <p className="text-xs font-medium uppercase tracking-wider text-brand-600">{t("featuresTitle")}</p>
          <p className="mt-1 text-sm leading-relaxed text-stone-600">{detail.features}</p>
        </section>

        <section className="mt-4">
          <p className="text-xs font-medium uppercase tracking-wider text-brand-600">{t("prosTitle")}</p>
          <ul className="mt-1 list-disc space-y-1 pl-4 text-sm leading-relaxed text-stone-600">
            {detail.pros.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </section>

        <section className="mt-4">
          <p className="text-xs font-medium uppercase tracking-wider text-brand-600">{t("consTitle")}</p>
          <ul className="mt-1 list-disc space-y-1 pl-4 text-sm leading-relaxed text-stone-600">
            {detail.cons.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </section>

        <section className="mt-4">
          <p className="text-xs font-medium uppercase tracking-wider text-brand-600">{t("referencesTitle")}</p>
          <ul className="mt-1 space-y-1 text-sm">
            {detail.references.map((ref) => (
              <li key={ref.url}>
                <a
                  href={ref.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-brand-700 underline decoration-brand-200 underline-offset-2 hover:text-brand-900"
                >
                  {ref.title}
                </a>
              </li>
            ))}
          </ul>
        </section>

        <div className="mt-5 border-t border-brand-100 pt-4">
          {phase === "sent" ? (
            <p className="text-sm text-brand-700">{t("sentMessage")}</p>
          ) : !showContactForm ? (
            <p className="text-sm text-stone-600">
              {t("sourcingPrompt")}{" "}
              <button
                onClick={() => setShowContactForm(true)}
                className="font-medium text-brand-700 underline decoration-brand-200 underline-offset-2 hover:text-brand-900"
              >
                {t("contactButton")}
              </button>
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t("namePlaceholder")}
                className="rounded-full border border-stone-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t("emailPlaceholder")}
                className="rounded-full border border-stone-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder={t("messagePlaceholder")}
                rows={2}
                className="rounded-2xl border border-stone-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <button
                onClick={submitContact}
                disabled={phase === "sending" || !email.trim()}
                className="self-start rounded-full bg-brand-700 px-4 py-1.5 text-sm font-medium text-white shadow-card transition-colors hover:bg-brand-800 disabled:opacity-40"
              >
                {phase === "sending" ? t("sending") : t("sendButton")}
              </button>
              {phase === "error" && <p className="text-xs text-rose-600">{t("errorMessage")}</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
