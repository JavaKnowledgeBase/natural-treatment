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
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-brand-100 bg-paper px-6 shadow-[0_1px_0_rgba(21,44,32,0.04)]">
      <Link href={prefix || "/"} aria-label="Natural Remedy Research home">
        <Logo size="sm" />
      </Link>
      <div className="flex items-center gap-4">
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
