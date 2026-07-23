import { getTranslations } from "next-intl/server";
import Footer from "@/components/Footer";

export async function generateMetadata({ params: { locale } }: { params: { locale: string } }) {
  const t = await getTranslations({ locale, namespace: "Terms" });
  return { title: `${t("title")} — Rootwell` };
}

export default async function TermsPage() {
  const t = await getTranslations("Terms");

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-paper">
      <div className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
        <h1 className="font-serif text-3xl font-semibold text-brand-900">{t("title")}</h1>
        <p className="mt-2 text-sm text-stone-500">{t("draftNote")}</p>

        <h2 className="mt-8 font-serif text-xl font-semibold text-brand-900">{t("notMedicalAdviceTitle")}</h2>
        <p className="mt-2 text-stone-600">{t("notMedicalAdviceBody")}</p>

        <h2 className="mt-8 font-serif text-xl font-semibold text-brand-900">{t("starterDatasetTitle")}</h2>
        <p className="mt-2 text-stone-600">{t("starterDatasetBody")}</p>

        <h2 className="mt-8 font-serif text-xl font-semibold text-brand-900">{t("noGuaranteeTitle")}</h2>
        <p className="mt-2 text-stone-600">{t("noGuaranteeBody")}</p>

        <h2 className="mt-8 font-serif text-xl font-semibold text-brand-900">{t("contactTitle")}</h2>
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
