"use client";

import { useTranslations } from "next-intl";
import { CachedItem, Recommendation } from "@/lib/api";

const CONFIDENCE_BADGE: Record<string, string> = {
  high: "bg-brand-100 text-brand-800",
  moderate: "bg-gold-100 text-gold-700",
  low: "bg-stone-100 text-stone-600",
};

function ItemChip({ item, onRemove }: { item: CachedItem; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-brand-100 px-3 py-1 text-sm text-brand-900">
      {item.label}
      <button
        onClick={onRemove}
        aria-label={`Remove ${item.label}`}
        className="ml-1 text-brand-700 hover:text-brand-950"
      >
        ×
      </button>
    </span>
  );
}

export default function SummaryPanel({
  step,
  symptoms,
  causes,
  recommendations,
  onRemoveSymptom,
  onRemoveCause,
}: {
  step: string;
  symptoms: CachedItem[];
  causes: CachedItem[];
  recommendations: Recommendation[];
  onRemoveSymptom: (id: string) => void;
  onRemoveCause: (id: string) => void;
}) {
  const t = useTranslations("SummaryPanel");

  const isEmpty = symptoms.length === 0 && causes.length === 0 && recommendations.length === 0;

  const stepLabels: Record<string, string> = {
    greeting: t("stepGreeting"),
    symptom_collection: t("stepSymptomCollection"),
    cause_collection: t("stepCauseCollection"),
    analysis: t("stepAnalysis"),
    results: t("stepResults"),
    email_sent: t("stepEmailSent"),
  };

  return (
    <div className="flex h-full flex-col gap-6 overflow-y-auto bg-paper p-6">
      <div>
        <p className="text-xs uppercase tracking-wider text-brand-600">{t("currentStep")}</p>
        <p className="font-serif text-xl font-semibold text-brand-900">{stepLabels[step] ?? step}</p>
      </div>

      {isEmpty && (
        <div className="rounded-lg border border-brand-100 bg-white p-4 shadow-sm">
          <p className="font-serif text-base font-semibold text-brand-700">{t("introTagline")}</p>
          <p className="mt-3 text-[11px] font-medium uppercase tracking-wider text-brand-500">
            {t("howItWorksTitle")}
          </p>
          <ol className="mt-1.5 space-y-1.5 text-xs leading-relaxed text-stone-600">
            <li className="flex gap-1.5">
              <span className="font-medium text-brand-600">1.</span>
              {t("howItWorksStep1")}
            </li>
            <li className="flex gap-1.5">
              <span className="font-medium text-brand-600">2.</span>
              {t("howItWorksStep2")}
            </li>
            <li className="flex gap-1.5">
              <span className="font-medium text-brand-600">3.</span>
              {t("howItWorksStep3")}
            </li>
            <li className="flex gap-1.5">
              <span className="font-medium text-brand-600">4.</span>
              {t("howItWorksStep4")}
            </li>
          </ol>
        </div>
      )}

      <div>
        <p className="mb-2 text-sm font-medium text-stone-700">
          {t("symptoms")} ({symptoms.length})
        </p>
        <div className="flex flex-wrap gap-2">
          {symptoms.length === 0 && <p className="text-sm text-stone-400">{t("nothingAddedYet")}</p>}
          {symptoms.map((s) => (
            <ItemChip key={s.id} item={s} onRemove={() => onRemoveSymptom(s.id)} />
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-sm font-medium text-stone-700">
          {t("possibleCauses")} ({causes.length})
        </p>
        <div className="flex flex-wrap gap-2">
          {causes.length === 0 && <p className="text-sm text-stone-400">{t("nothingAddedYet")}</p>}
          {causes.map((c) => (
            <ItemChip key={c.id} item={c} onRemove={() => onRemoveCause(c.id)} />
          ))}
        </div>
      </div>

      {recommendations.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-medium text-stone-700">{t("topRecommendations")}</p>
          <ol className="space-y-3">
            {recommendations.map((r) => (
              <li key={r.herb_id} className="rounded-xl border border-brand-100 bg-white p-4 shadow-card">
                <div className="flex items-center justify-between">
                  <span className="font-serif text-base font-semibold text-brand-900">{r.herb_name}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      CONFIDENCE_BADGE[r.confidence_band] ?? "bg-stone-100 text-stone-600"
                    }`}
                  >
                    {t("confidenceLabel", { band: r.confidence_band })}
                  </span>
                </div>
                <p className="mt-1 text-sm text-stone-600">{r.reason}</p>
                <p className="mt-1 text-xs text-stone-400">
                  {t("evidenceLevel")}: {t("evidenceLevelValue", { level: r.evidence_level })}
                </p>
                {r.safety_note && <p className="mt-1 text-xs text-rose-700">⚠ {r.safety_note}</p>}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
