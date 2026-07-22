import Footer from "@/components/Footer";

export const metadata = {
  title: "Terms of Use — Rootwell",
};

export default function TermsPage() {
  return (
    <div className="flex h-full flex-col overflow-y-auto bg-stone-50">
      <div className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
        <h1 className="text-2xl font-semibold text-stone-800">Terms of Use</h1>
        <p className="mt-2 text-sm text-stone-500">
          Draft — have this reviewed by counsel before launch.
        </p>

        <h2 className="mt-8 text-lg font-semibold text-stone-800">Not medical advice</h2>
        <p className="mt-2 text-stone-600">
          Rootwell provides general, informational content about herbs and traditional or
          researched associations with symptoms. It does not diagnose conditions, prescribe
          treatment, or replace consultation with a licensed clinician. Always seek professional
          medical advice for symptoms that are severe, persistent, or concerning, and before
          starting, stopping, or combining any herb or supplement — especially if you are
          pregnant, nursing, managing a chronic condition, or taking medication.
        </p>

        <h2 className="mt-8 text-lg font-semibold text-stone-800">Starter dataset</h2>
        <p className="mt-2 text-stone-600">
          The herb, compound, and symptom data currently used by Rootwell is an unreviewed
          starter dataset assembled for development purposes. It has not been through an expert
          curation or clinical review process.
        </p>

        <h2 className="mt-8 text-lg font-semibold text-stone-800">No guarantee of outcome</h2>
        <p className="mt-2 text-stone-600">
          Recommendations are scored estimates based on available evidence and are not a
          guarantee of safety or effectiveness for any individual.
        </p>

        <h2 className="mt-8 text-lg font-semibold text-stone-800">Contact</h2>
        <p className="mt-2 text-stone-600">
          Questions about these terms:{" "}
          <a href="mailto:hello@rootwell.app" className="text-emerald-700 underline">
            hello@rootwell.app
          </a>
        </p>
      </div>
      <Footer />
    </div>
  );
}
