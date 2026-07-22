import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";

export const metadata: Metadata = {
  title: "Rootwell",
  description: "Rootwell traces symptoms back to their likely biochemical root cause and suggests evidence-aware herbal support.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="h-full bg-stone-50 text-stone-900">
        <div className="flex h-screen flex-col">
          <Header />
          <div className="min-h-0 flex-1">{children}</div>
        </div>
      </body>
    </html>
  );
}
