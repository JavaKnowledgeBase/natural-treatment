import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";
import Logo from "./Logo";
import LanguageSwitcher from "./LanguageSwitcher";
import { defaultLocale } from "@/locales";

export default async function Header() {
  const locale = await getLocale();
  const t = await getTranslations("Header");
  const prefix = locale === defaultLocale ? "" : `/${locale}`;

  return (
    <header className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-1 border-b border-brand-100 bg-paper px-6 py-3 shadow-[0_1px_0_rgba(21,44,32,0.04)]">
      <Link href={prefix || "/"} aria-label="Natural Remedy Research home" className="shrink-0">
        <Logo size="sm" />
      </Link>
      <p className="min-w-0 flex-1 text-xs leading-snug text-brand-600">{t("trustNote")}</p>
      <div className="flex shrink-0 items-center gap-4">
        <nav className="text-sm text-stone-500">
          <Link href={`${prefix}/about`} className="transition-colors hover:text-brand-700">
            {t("aboutContact")}
          </Link>
        </nav>
        <LanguageSwitcher />
      </div>
    </header>
  );
}
