import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";
import { defaultLocale } from "@/locales";

export default async function Footer() {
  const locale = await getLocale();
  const t = await getTranslations("Footer");
  const prefix = locale === defaultLocale ? "" : `/${locale}`;

  return (
    <footer className="border-t border-brand-100 bg-paper px-6 py-6 text-sm text-stone-500">
      <div className="mx-auto flex max-w-3xl flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p>&copy; {new Date().getFullYear()} {t("tagline")}</p>
        <div className="flex gap-4">
          <Link href={`${prefix}/about`} className="transition-colors hover:text-brand-700">
            {t("aboutContact")}
          </Link>
          <Link href={`${prefix}/privacy`} className="transition-colors hover:text-brand-700">
            {t("privacy")}
          </Link>
          <Link href={`${prefix}/terms`} className="transition-colors hover:text-brand-700">
            {t("terms")}
          </Link>
        </div>
      </div>
    </footer>
  );
}
