import { getTranslations } from "next-intl/server";
import Logo from "@/components/Logo";
import Footer from "@/components/Footer";

export async function generateMetadata({ params: { locale } }: { params: { locale: string } }) {
  const t = await getTranslations({ locale, namespace: "About" });
  return { title: `${t("contactTitle")} — Rootwell` };
}

export default async function AboutPage() {
  const t = await getTranslations("About");

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-paper">
      <div className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
        <Logo size="lg" />

        <h1 className="mt-8 font-serif text-3xl font-semibold text-brand-900">{t("heading")}</h1>
        <p className="mt-4 text-stone-600">{t("intro")}</p>

        <div className="mt-8 rounded-xl border border-gold-200 bg-gold-50 p-4 text-sm text-gold-700">
          {t("disclaimer")}
        </div>

        <h2 className="mt-10 font-serif text-xl font-semibold text-brand-900">{t("whoTitle")}</h2>
        <p className="mt-2 text-stone-600">{t("whoBody")}</p>

        <h2 className="mt-10 font-serif text-xl font-semibold text-brand-900">{t("contactTitle")}</h2>
        <p className="mt-2 text-stone-600">
          {t("contactBody")}{" "}
          <a href="mailto:hello@rootwell.app" className="text-brand-700 underline hover:text-brand-800">
            hello@rootwell.app
          </a>
        </p>
      </div>
      <Footer />
    </div>
  );
}
