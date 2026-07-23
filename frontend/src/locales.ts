// UI + LLM-conversation language support only. Backend catalog matching
// (mock-mode symptom/cause keyword matching) stays English-only regardless
// of the locale selected here -- see docs/ARCHITECTURE.md for why the
// starter dataset isn't being translated.
export const locales = ["en", "hi", "zh", "fr", "es"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en";

export const localeLabels: Record<Locale, string> = {
  en: "English",
  hi: "हिन्दी",
  zh: "中文",
  fr: "Français",
  es: "Español",
};

// BCP-47-ish name used to instruct the backend LLM which language to
// respond in (see services/agents/intake|mapping|explanation's language
// handling).
export const localeLlmNames: Record<Locale, string> = {
  en: "English",
  hi: "Hindi",
  zh: "Simplified Chinese",
  fr: "French",
  es: "Spanish",
};
