import Link from "next/link";
import AnimateOnScroll from "./AnimateOnScroll";

interface Props {
  headline?: string;
  subheadline?: string;
  primaryLabel?: string;
  primaryHref?: string;
  secondaryLabel?: string;
  secondaryHref?: string;
}

export default function CTASection({
  headline = "Your leads aren't waiting. Neither should you.",
  subheadline = "Start capturing and qualifying leads today — free, no credit card required.",
  primaryLabel = "Start for Free",
  primaryHref = "/app/signup",
  secondaryLabel = "See Product",
  secondaryHref = "/product",
}: Props) {
  return (
    <section
      className="relative overflow-hidden py-28"
      style={{ background: "var(--mk-dark-bg)" }}
      aria-labelledby="mk-cta-heading"
    >
      {/* Radial glow */}
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 70% 60% at 50% 120%, rgba(15,118,110,0.3) 0%, transparent 65%)",
        }}
      />
      {/* Shimmer top border */}
      <div
        className="absolute top-0 left-0 right-0 h-px mk-shimmer-border"
        aria-hidden="true"
      />

      <div className="relative max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <AnimateOnScroll animation="fadeUp">
          <h2
            id="mk-cta-heading"
            className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-5 tracking-tight"
          >
            {headline}
          </h2>
        </AnimateOnScroll>
        <AnimateOnScroll animation="fadeUp" delay={80}>
          <p className="text-lg mb-10" style={{ color: "rgba(148,163,184,0.9)" }}>
            {subheadline}
          </p>
        </AnimateOnScroll>
        <AnimateOnScroll animation="zoomIn" delay={160}>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href={primaryHref}
              className="px-9 py-4 rounded-xl font-semibold text-base mk-btn-primary"
            >
              {primaryLabel}
            </a>
            <Link
              href={secondaryHref}
              className="px-9 py-4 rounded-xl font-semibold text-sm mk-btn-ghost-dark"
            >
              {secondaryLabel}
            </Link>
          </div>
        </AnimateOnScroll>
      </div>
    </section>
  );
}
