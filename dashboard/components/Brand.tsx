import type { ReactNode } from "react";
import Link from "next/link";

export function PulseMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <span className={`relative inline-flex items-center justify-center text-paper ${className}`}>
      <span className="pulse-ring absolute inset-[-14%] rounded-full border border-paper/25" />
      <svg viewBox="0 0 32 32" className="relative h-full w-full" aria-hidden="true">
        <circle
          cx="16"
          cy="16"
          r="12"
          fill="none"
          stroke="currentColor"
          strokeOpacity="0.28"
          strokeWidth="1.2"
        />
        <circle cx="16" cy="16" r="2.1" fill="currentColor" />
        <path
          d="M5.5 16h4.6l2.1-5.2 3.4 10.6 2.4-5.4H26.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.65"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}

export function PulseWordmark({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const text = size === "lg" ? "text-[2rem]" : size === "sm" ? "text-lg" : "text-[1.35rem]";
  const mark = size === "lg" ? "h-10 w-10" : size === "sm" ? "h-6 w-6" : "h-8 w-8";
  return (
    <span className="inline-flex items-center gap-2.5 text-paper">
      <PulseMark className={mark} />
      <span className={`font-serif italic leading-none tracking-tight ${text}`}>Pulse</span>
    </span>
  );
}

export function BrandScreen({
  title,
  children,
  actions,
}: {
  title: string;
  children: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-6 py-16">
      <Link href="/" className="inline-flex w-fit !text-paper hover:!text-paper">
        <PulseWordmark />
      </Link>
      <h1 className="mt-8 text-3xl font-semibold tracking-tight text-paper">{title}</h1>
      <div className="mt-3 text-sm leading-relaxed text-mist">{children}</div>
      {actions ? <div className="mt-8 flex flex-wrap items-center gap-3">{actions}</div> : null}
    </main>
  );
}
