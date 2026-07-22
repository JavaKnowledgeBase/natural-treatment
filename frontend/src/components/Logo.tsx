export function LogoMark({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 3c-6 4-8 9-6 14 C 8 20, 16 20, 18 17 C 20 12, 18 7, 12 3 Z" />
      <path d="M12 4 L12 17" />
      <path d="M12 17 L9 22" />
      <path d="M12 17 L12 22" />
      <path d="M12 17 L15 22" />
    </svg>
  );
}

export default function Logo({
  size = "md",
  showWordmark = true,
}: {
  size?: "sm" | "md" | "lg";
  showWordmark?: boolean;
}) {
  const iconSize = { sm: "h-5 w-5", md: "h-7 w-7", lg: "h-12 w-12" }[size];
  const textSize = { sm: "text-base", md: "text-xl", lg: "text-4xl" }[size];

  return (
    <div className="flex items-center gap-2">
      <LogoMark className={`${iconSize} text-emerald-700`} />
      {showWordmark && (
        <span className={`${textSize} font-semibold tracking-tight text-stone-800`}>
          Root<span className="text-emerald-600">well</span>
        </span>
      )}
    </div>
  );
}
