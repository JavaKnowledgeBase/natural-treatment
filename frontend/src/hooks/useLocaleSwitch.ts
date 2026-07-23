"use client";

import { usePathname, useRouter } from "next/navigation";
import { useLocale } from "next-intl";
import { defaultLocale, Locale } from "@/locales";

// Manual locale-prefix handling rather than next-intl's navigation helpers,
// since `localePrefix: "as-needed"` means English has no prefix (per user
// request: English stays the default, unprefixed locale) while the other
// four languages are prefixed (e.g. /hi, /fr). Shared by both the header
// dropdown (LanguageSwitcher) and the first-visit language picker
// (LanguagePicker) so the path-rewriting logic lives in exactly one place.
export function useLocaleSwitch() {
  const locale = useLocale() as Locale;
  const pathname = usePathname();
  const router = useRouter();

  const switchTo = (nextLocale: Locale) => {
    const segments = pathname.split("/");
    const pathHasCurrentLocalePrefix = locale !== defaultLocale && segments[1] === locale;
    const unprefixedPath = pathHasCurrentLocalePrefix ? "/" + segments.slice(2).join("/") : pathname;
    const cleanPath = unprefixedPath === "//" ? "/" : unprefixedPath;

    const nextPath =
      nextLocale === defaultLocale ? cleanPath : `/${nextLocale}${cleanPath === "/" ? "" : cleanPath}`;

    router.push(nextPath || "/");
  };

  return { locale, switchTo };
}
