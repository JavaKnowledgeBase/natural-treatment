import Footer from "@/components/Footer";

export const metadata = {
  title: "Privacy Policy — Rootwell",
};

export default function PrivacyPage() {
  return (
    <div className="flex h-full flex-col overflow-y-auto bg-stone-50">
      <div className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
        <h1 className="text-2xl font-semibold text-stone-800">Privacy Policy</h1>
        <p className="mt-2 text-sm text-stone-500">
          Draft — reflects the current implementation. Have this reviewed by counsel before
          launch.
        </p>

        <h2 className="mt-8 text-lg font-semibold text-stone-800">What we store</h2>
        <p className="mt-2 text-stone-600">
          Rootwell has no database. Everything about your session — the conversation, the
          symptoms and possible causes you share, and the resulting recommendations — is kept
          only in an in-memory cache for the duration of that session.
        </p>

        <h2 className="mt-8 text-lg font-semibold text-stone-800">What we never ask for</h2>
        <p className="mt-2 text-stone-600">
          Rootwell never proactively asks for your age, pregnancy status, medications, allergies,
          or medical conditions. If you volunteer any of that in your own words, it's used only to
          apply relevant safety checks for that session and is deleted along with everything else
          when the session ends.
        </p>

        <h2 className="mt-8 text-lg font-semibold text-stone-800">When your data is deleted</h2>
        <p className="mt-2 text-stone-600">
          Your session is deleted automatically after a period of inactivity, or immediately when
          you end it, or immediately after an email summary is sent if you choose that option.
        </p>

        <h2 className="mt-8 text-lg font-semibold text-stone-800">Email summaries</h2>
        <p className="mt-2 text-stone-600">
          If you ask to have your session emailed to you, we ask you to confirm a one-time code
          sent to that address before anything is sent, so the feature can't be used to send mail
          to an address that isn't yours. The email itself is sent through a third-party
          transactional email provider.
        </p>

        <h2 className="mt-8 text-lg font-semibold text-stone-800">Contact</h2>
        <p className="mt-2 text-stone-600">
          Questions about this policy:{" "}
          <a href="mailto:hello@rootwell.app" className="text-emerald-700 underline">
            hello@rootwell.app
          </a>
        </p>
      </div>
      <Footer />
    </div>
  );
}
