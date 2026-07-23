"use client";

import { usePathname, useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { locales, localeLabels, defaultLocale, Locale } from "@/locales";

// Manual locale-prefix handling rather than next-intl's navigation helpers,
// since `localePrefix: "as-needed"` means English has no prefix (per user
// request: English stays the default, unprefixed locale) while the other
// four languages are prefixed (e.g. /hi, /fr).
export default function LanguageSwitcher() {
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const t = useTranslations("Header");

  const switchTo = (nextLocale: Locale) => {
    const segments = pathname.split("/");
    const pathHasCurrentLocalePrefix = locale !== defaultLocale && segments[1] === locale;
    const unprefixedPath = pathHasCurrentLocalePrefix ? "/" + segments.slice(2).join("/") : pathname;
    const cleanPath = unprefixedPath === "//" ? "/" : unprefixedPath;

    const nextPath =
      nextLocale === defaultLocale ? cleanPath : `/${nextLocale}${cleanPath === "/" ? "" : cleanPath}`;

    router.push(nextPath || "/");
  };

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
