import Link from "next/link";

interface CTASectionProps {
  headline?: string;
  subheadline?: string;
  primaryLabel?: string;
  primaryHref?: string;
  secondaryLabel?: string;
  secondaryHref?: string;
}

export default function CTASection({
  headline = "Your leads aren't waiting. Neither should you.",
  subheadline = "Start capturing and qualifying leads today — no credit card required.",
  primaryLabel = "Book a Demo",
  primaryHref = "/contact",
  secondaryLabel = "Start Free",
  secondaryHref = "/plans",
}: CTASectionProps) {
  return (
    <section
      className="relative overflow-hidden py-24"
      style={{ background: "#0B1320" }}
      aria-labelledby="cta-heading"
    >
      {/* Background glow */}
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 60% 50% at 50% 100%, rgba(15,118,110,0.25) 0%, transparent 70%)",
        }}
      />

      <div className="relative max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
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
          <Link
            href={primaryHref}
            className="px-8 py-3.5 rounded-xl font-semibold text-sm btn-primary"
          >
            {primaryLabel}
          </Link>
          <Link
            href={secondaryHref}
            className="px-8 py-3.5 rounded-xl font-semibold text-sm btn-ghost-dark"
          >
            {secondaryLabel}
          </Link>
        </div>
      </div>
    </section>
  );
}
