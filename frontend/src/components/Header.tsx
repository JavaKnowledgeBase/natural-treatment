import Link from "next/link";
import Logo from "./Logo";

export default function Header() {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-stone-200 bg-white px-6">
      <Link href="/" aria-label="Rootwell home">
        <Logo size="sm" />
      </Link>
      <nav className="text-sm text-stone-500">
        <Link href="/about" className="hover:text-stone-800">
          About &amp; Contact
        </Link>
      </nav>
    </header>
  );
}
