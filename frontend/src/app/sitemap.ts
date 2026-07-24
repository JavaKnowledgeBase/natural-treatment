import type { MetadataRoute } from "next";
import { locales, defaultLocale, type Locale } from "@/locales";

const SITE_URL = "https://naturalremedyresearch.com";

// Keep in sync with src/app/[locale]/*/page.tsx -- "" is the home page.
const routes = ["", "about", "privacy", "terms"];

function localizedUrl(locale: Locale, route: string): string {
  const prefix = locale === defaultLocale ? "" : `/${locale}`;
  return `${SITE_URL}${prefix}${route ? `/${route}` : ""}`;
}

export default function sitemap(): MetadataRoute.Sitemap {
  return routes.map((route) => ({
    url: localizedUrl(defaultLocale, route),
    lastModified: new Date(),
    alternates: {
      languages: Object.fromEntries(locales.map((locale) => [locale, localizedUrl(locale, route)])),
    },
  }));
}
