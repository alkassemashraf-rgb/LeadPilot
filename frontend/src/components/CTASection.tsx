import Link from "next/link";
import { APP_URL } from "@/lib/api";

interface CTASectionProps {
  headline?: string;
  subheadline?: string;
  primaryLabel?: string;
  primaryHref?: string;
  secondaryLabel?: string;
  secondaryHref?: string;
}

function SmartLink({
  href,
  className,
  children,
}: {
  href: string;
  className: string;
  children: React.ReactNode;
}) {
  if (href.startsWith("http")) {
    return (
      <a href={href} className={className}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}

export default function CTASection({
  headline = "Your leads aren't waiting. Neither should you.",
  subheadline = "Start capturing and qualifying leads today — no credit card required.",
  primaryLabel = "Book a Demo",
  primaryHref = "/contact",
  secondaryLabel = "Sign Up Free",
  secondaryHref = `${APP_URL}/signup`,
}: CTASectionProps) {
  return (
    <section
      className="relative overflow-hidden py-32"
      style={{ background: "var(--dark-bg)" }}
      aria-labelledby="cta-heading"
    >
      {/* Background glow and grids */}
      <div className="absolute inset-0 cockpit-grid opacity-20" aria-hidden="true" />
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 60% 50% at 50% 100%, rgba(34, 211, 238, 0.15) 0%, transparent 70%)",
        }}
      />

      <div className="relative max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center animate-fade-up">
        <h2
          id="cta-heading"
          className="text-3xl sm:text-4xl font-bold text-white mb-4 tracking-tight"
        >
          {headline}
        </h2>
        <p
          className="text-lg mb-10"
          style={{ color: "rgba(148,163,184,0.9)" }}
        >
          {subheadline}
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <SmartLink
            href={primaryHref}
            className="px-8 py-4 rounded-xl font-semibold text-base btn-primary glow-primary"
          >
            {primaryLabel}
          </SmartLink>
          <SmartLink
            href={secondaryHref}
            className="px-8 py-4 rounded-xl font-semibold text-sm glass-panel hover:border-cyan-400 transition-colors text-white"
          >
            {secondaryLabel}
          </SmartLink>
        </div>
      </div>
    </section>
  );
}
