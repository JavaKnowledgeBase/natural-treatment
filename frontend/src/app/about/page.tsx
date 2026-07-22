import Logo from "@/components/Logo";
import Footer from "@/components/Footer";

export const metadata = {
  title: "About & Contact — Rootwell",
};

export default function AboutPage() {
  return (
    <div className="flex h-full flex-col overflow-y-auto bg-stone-50">
      <div className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
        <Logo size="lg" />

        <h1 className="mt-8 text-2xl font-semibold text-stone-800">
          Tracing symptoms back to their likely root cause
        </h1>
        <p className="mt-4 text-stone-600">
          Rootwell is a conversational, evidence-aware assistant that helps you explore how
          everyday symptoms may connect to underlying biochemical patterns — and which herbs
          have historical or clinical evidence for supporting them. Everything you share lives
          only in this session's cache and is deleted the moment the session ends, whether that's
          because you asked for an email summary or simply closed the tab.
        </p>

        <div className="mt-8 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          Rootwell is informational only and is not a substitute for professional medical advice,
          diagnosis, or treatment. Always consult a licensed clinician about symptoms that are
          severe, persistent, or concerning.
        </div>

        <h2 className="mt-10 text-lg font-semibold text-stone-800">Who's behind this</h2>
        <p className="mt-2 text-stone-600">Ravi Kafley, Founder</p>

        <h2 className="mt-10 text-lg font-semibold text-stone-800">Contact</h2>
        <p className="mt-2 text-stone-600">
          Questions, feedback, or concerns about a recommendation:{" "}
          <a href="mailto:hello@rootwell.app" className="text-emerald-700 underline">
            hello@rootwell.app
          </a>
        </p>
      </div>
      <Footer />
    </div>
  );
}
