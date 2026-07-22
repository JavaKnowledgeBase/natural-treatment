"use client";

import { CachedItem, Recommendation } from "@/lib/api";

const STEP_LABELS: Record<string, string> = {
  greeting: "Getting started",
  symptom_collection: "Sharing symptoms",
  cause_collection: "Sharing possible causes",
  analysis: "Analyzing",
  results: "Results ready",
  email_sent: "Sent — session ended",
};

function ItemChip({ item, onRemove }: { item: CachedItem; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 text-sm text-emerald-900">
      {item.label}
      <button
        onClick={onRemove}
        aria-label={`Remove ${item.label}`}
        className="ml-1 text-emerald-700 hover:text-emerald-950"
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
  return (
    <div className="flex h-full flex-col gap-6 overflow-y-auto p-6">
      <div>
        <p className="text-xs uppercase tracking-wide text-stone-500">Current step</p>
        <p className="text-lg font-semibold text-stone-800">{STEP_LABELS[step] ?? step}</p>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
        This app is informational only and not a substitute for professional medical advice.
        Nothing here is stored beyond this session unless you choose to email it to yourself.
      </div>

      <div>
        <p className="mb-2 text-sm font-medium text-stone-700">Symptoms ({symptoms.length})</p>
        <div className="flex flex-wrap gap-2">
          {symptoms.length === 0 && <p className="text-sm text-stone-400">Nothing added yet.</p>}
          {symptoms.map((s) => (
            <ItemChip key={s.id} item={s} onRemove={() => onRemoveSymptom(s.id)} />
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-sm font-medium text-stone-700">Possible causes ({causes.length})</p>
        <div className="flex flex-wrap gap-2">
          {causes.length === 0 && <p className="text-sm text-stone-400">Nothing added yet.</p>}
          {causes.map((c) => (
            <ItemChip key={c.id} item={c} onRemove={() => onRemoveCause(c.id)} />
          ))}
        </div>
      </div>

      {recommendations.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-medium text-stone-700">Top recommendations</p>
          <ol className="space-y-3">
            {recommendations.map((r) => (
              <li key={r.herb_id} className="rounded-lg border border-stone-200 bg-white p-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-stone-800">{r.herb_name}</span>
                  <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-600">
                    {r.confidence_band} confidence
                  </span>
                </div>
                <p className="mt-1 text-sm text-stone-600">{r.reason}</p>
                <p className="mt-1 text-xs text-stone-400">Evidence level: {r.evidence_level}</p>
                {r.safety_note && <p className="mt-1 text-xs text-rose-700">⚠ {r.safety_note}</p>}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
