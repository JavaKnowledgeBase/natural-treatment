"use client";

import { useTranslations } from "next-intl";
import { useLocaleSwitch } from "@/hooks/useLocaleSwitch";
import { locales, localeLabels, Locale } from "@/locales";

export default function LanguageSwitcher() {
  const { locale, switchTo } = useLocaleSwitch();
  const t = useTranslations("Header");

  return (
    <label className="flex items-center gap-1.5 text-sm text-stone-500">
      <span className="sr-only">{t("language")}</span>
      <select
        value={locale}
        onChange={(e) => switchTo(e.target.value as Locale)}
        className="cursor-pointer rounded-full border border-stone-200 bg-white px-2 py-1 text-sm text-stone-600 transition-colors hover:border-brand-300 focus:border-brand-500 focus:outline-none"
        aria-label={t("language")}
      >
        {locales.map((code) => (
          <option key={code} value={code}>
            {localeLabels[code]}
          </option>
        ))}
      </select>
    </label>
  );
}
