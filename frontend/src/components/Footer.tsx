import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-stone-200 px-6 py-6 text-sm text-stone-500">
      <div className="mx-auto flex max-w-3xl flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p>&copy; {new Date().getFullYear()} Rootwell. Informational only — not medical advice.</p>
        <div className="flex gap-4">
          <Link href="/about" className="hover:text-stone-800">
            About &amp; Contact
          </Link>
          <Link href="/privacy" className="hover:text-stone-800">
            Privacy
          </Link>
          <Link href="/terms" className="hover:text-stone-800">
            Terms
          </Link>
        </div>
      </div>
    </footer>
  );
}
