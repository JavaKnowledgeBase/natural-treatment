"use client";

import { useEffect, useState } from "react";
import { useLocaleSwitch } from "@/hooks/useLocaleSwitch";
import { locales, localeLabels, defaultLocale, Locale } from "@/locales";

const STORAGE_KEY = "rootwell-language-chosen";

// Shown once, right under the greeting, so a non-English speaker who might
// miss the small header dropdown has an obvious way to switch before
// typing anything. English isn't offered here -- if the page loaded in
// English, staying in English needs no action. Disappears permanently
// (persisted via localStorage) the moment any button is picked; the
// header dropdown remains the only control after that.
export default function LanguagePicker() {
  const { switchTo } = useLocaleSwitch();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(!window.localStorage.getItem(STORAGE_KEY));
  }, []);

  if (!visible) return null;

  const choose = (code: Locale) => {
    window.localStorage.setItem(STORAGE_KEY, "true");
    setVisible(false);
    switchTo(code);
  };

  const alternatives = locales.filter((code) => code !== defaultLocale);

  return (
    <div className="flex flex-wrap gap-2 pt-1">
      {alternatives.map((code) => (
        <button
          key={code}
          onClick={() => choose(code)}
          className="rounded-full border border-brand-300 bg-white px-3 py-1 text-xs text-brand-800 shadow-card transition-colors hover:border-brand-400 hover:bg-brand-50"
        >
          {localeLabels[code]}
        </button>
      ))}
    </div>
  );
}
