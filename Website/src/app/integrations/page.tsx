import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Cable, RefreshCw, Zap } from "lucide-react";
import { getIntegrationProviders } from "@/lib/api";
import CTASection from "@/components/CTASection";

export const metadata: Metadata = {
  title: "Integrations — Connect Your Entire Stack",
  description:
    "LeadPilot integrates natively with WhatsApp Cloud API, Meta (Instagram/Messenger), and Zoho CRM. Connect, sync, and automate.",
};

const PROVIDER_COLORS: Record<string, string> = {
  whatsapp: "#25D366",
  meta: "#1877F2",
  zoho: "#E42527",
};

const howItWorks = [
  {
    icon: Cable,
    step: "01",
    title: "Connect",
    description:
      "Add your integration credentials from the Integrations Hub. LeadPilot handles authentication and connection health.",
  },
  {
    icon: RefreshCw,
    step: "02",
    title: "Sync",
    description:
      "Leads, contacts, and conversations flow bidirectionally between LeadPilot and your connected platforms in real time.",
  },
  {
    icon: Zap,
    step: "03",
    title: "Automate",
    description:
      "Build automation flows that span platforms — capture on WhatsApp, qualify with AI, push to Zoho CRM. All in one pipeline.",
  },
];

export default async function IntegrationsPage() {
  const providers = await getIntegrationProviders();

  return (
    <>
      {/* ─── HERO ─────────────────────────────────────────────────── */}
      <section
        className="relative py-28 overflow-hidden"
        style={{ background: "#0B1320" }}
        aria-labelledby="integrations-hero-heading"
      >
        <div className="absolute inset-0 cockpit-grid opacity-40" aria-hidden="true" />
        <div
          className="absolute inset-0 pointer-events-none"
          aria-hidden="true"
          style={{
            background:
              "radial-gradient(ellipse 60% 50% at 50% 0%, rgba(15,118,110,0.25) 0%, transparent 70%)",
          }}
        />
        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p
            className="text-xs font-bold uppercase tracking-widest mb-4"
            style={{ color: "#14B8A6" }}
          >
            Integrations
          </p>
          <h1
            id="integrations-hero-heading"
            className="text-4xl sm:text-5xl md:text-6xl font-bold text-white mb-6 tracking-tight"
          >
            Connect your entire stack.
            <br />
            <span className="gradient-text">No code required.</span>
          </h1>
          <p
            className="text-lg max-w-2xl mx-auto leading-relaxed"
            style={{ color: "rgba(148,163,184,0.9)" }}
          >
            Native integrations with the messaging platforms and CRM your revenue team already uses.
            Set up in minutes, stay connected forever.
          </p>
        </div>
      </section>

      {/* ─── PROVIDER CARDS ───────────────────────────────────────── */}
      <section
        className="py-24"
        style={{ background: "#0B1320" }}
        aria-labelledby="providers-heading"
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 id="providers-heading" className="sr-only">Available integrations</h2>

          {providers.length === 0 ? (
            <p className="text-center text-lg" style={{ color: "#64748B" }}>
              Integrations are loading. Check back soon.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {providers.map((p) => {
                const color = PROVIDER_COLORS[p.key] ?? "#0F766E";
                return (
                  <div
                    key={p.key}
                    className="catalog-card p-8 flex flex-col"
                  >
                    {/* Icon */}
                    <div
                      className="w-14 h-14 rounded-xl flex items-center justify-center mb-5"
                      style={{
                        background: `${color}15`,
                        border: `1px solid ${color}30`,
                      }}
                    >
                      <span className="text-2xl font-bold" style={{ color }}>
                        {p.label.charAt(0)}
                      </span>
                    </div>

                    {/* Name + description */}
                    <h3 className="text-white font-bold text-lg mb-2">{p.label}</h3>
                    <p
                      className="text-sm leading-relaxed mb-5 flex-1"
                      style={{ color: "rgba(148,163,184,0.85)" }}
                    >
                      {p.description}
                    </p>

                    {/* Required fields */}
                    {p.fields.length > 0 && (
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "#475569" }}>
                          What you need
                        </p>
                        <ul className="space-y-1">
                          {p.fields.map((f) => (
                            <li key={f.name} className="text-xs" style={{ color: "#94A3B8" }}>
                              • {f.label}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* ─── HOW IT WORKS ─────────────────────────────────────────── */}
      <section
        className="py-24 border-t"
        style={{ background: "#0E1826", borderColor: "rgba(255,255,255,0.06)" }}
        aria-labelledby="how-integrations-work"
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <p
              className="text-xs font-bold uppercase tracking-widest mb-3"
              style={{ color: "#14B8A6" }}
            >
              How It Works
            </p>
            <h2
              id="how-integrations-work"
              className="text-3xl sm:text-4xl font-bold text-white tracking-tight"
            >
              Three steps to a connected pipeline
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {howItWorks.map(({ icon: Icon, step, title, description }) => (
              <div key={step} className="text-center">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-5"
                  style={{
                    background: "rgba(15,118,110,0.15)",
                    border: "1px solid rgba(20,184,166,0.3)",
                  }}
                >
                  <Icon className="w-5 h-5" style={{ color: "#14B8A6" }} aria-hidden="true" />
                </div>
                <span
                  className="text-xl font-bold block mb-2"
                  style={{
                    background: "linear-gradient(135deg, #0F766E, #14B8A6)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    backgroundClip: "text",
                  }}
                >
                  {step}
                </span>
                <h3 className="text-white font-semibold text-base mb-2">{title}</h3>
                <p className="text-sm leading-relaxed" style={{ color: "#94A3B8" }}>
                  {description}
                </p>
              </div>
            ))}
          </div>

          <div className="text-center mt-12">
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 text-sm font-semibold text-link-teal"
            >
              Need help connecting? Contact us
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>

      {/* ─── CTA ──────────────────────────────────────────────────── */}
      <CTASection
        headline="Ready to connect your stack?"
        subheadline="Set up integrations in minutes and start automating your lead pipeline today."
        primaryLabel="Book a Demo"
        primaryHref="/contact"
        secondaryLabel="See Templates"
        secondaryHref="/templates"
      />
    </>
  );
}
