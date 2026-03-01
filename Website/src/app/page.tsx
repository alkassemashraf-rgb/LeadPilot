import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  CheckCircle,
  Users,
  TrendingUp,
  Clock,
} from "lucide-react";
import CTASection from "@/components/CTASection";
import FeatureCard from "@/components/FeatureCard";
import PlanCard from "@/components/PlanCard";
import { getPlans, getModules, getIntegrationProviders, getPublicTemplates, APP_URL } from "@/lib/api";
import { MODULE_MARKETING_MAP } from "@/lib/moduleMap";

export const metadata: Metadata = {
  title: "LeadPilot — AI-Native Lead Capture, Qualification & Routing",
  description:
    "LeadPilot is the AI-native platform that captures, qualifies, and routes leads to the right rep automatically. Close more deals without growing headcount.",
};

// ── Pricing lookup (same as plans page) ─────────────────────────────

const PLAN_PRICING: Record<string, { price: string; priceNote: string; tagline: string; available: boolean }> = {
  free: { price: "$0", priceNote: "/ month", tagline: "Start capturing leads today", available: true },
  growth: { price: "Coming Soon", priceNote: "", tagline: "For growing sales teams", available: false },
  enterprise: { price: "Contact Us", priceNote: "", tagline: "Custom deployment for large organisations", available: false },
};

function entitlementToString(moduleKey: string, hardLimit: number | null): string | null {
  const info = MODULE_MARKETING_MAP[moduleKey];
  if (!info) return null;
  if (hardLimit === null) return `${info.marketingTitle} (Unlimited)`;
  if (hardLimit > 0) return `${info.marketingTitle} (up to ${hardLimit.toLocaleString()})`;
  return info.marketingTitle;
}

// ── Static content (narrative, not feature claims) ──────────────────

const steps = [
  { number: "01", title: "Capture", description: "Leads arrive from any channel — your forms, chat, or integrations. LeadPilot ingests them all instantly." },
  { number: "02", title: "Qualify", description: "Our AI engages, asks the right questions, and scores every lead based on your ideal customer profile." },
  { number: "03", title: "Route", description: "Qualified leads are dispatched to the right rep or team — automatically, with zero manual hand-off." },
  { number: "04", title: "Follow Up", description: "Automated follow-up sequences keep leads warm while your team focuses on closing." },
  { number: "05", title: "Report", description: "Real-time dashboards show conversion rates, pipeline velocity, and where you're losing leads." },
];

// ── Provider icon map ───────────────────────────────────────────────

const PROVIDER_COLORS: Record<string, string> = {
  whatsapp: "#25D366",
  meta: "#1877F2",
  zoho: "#E42527",
};

export default async function HomePage() {
  const [plans, modules, providers, templates] = await Promise.all([
    getPlans(),
    getModules(),
    getIntegrationProviders(),
    getPublicTemplates(),
  ]);

  // Feature highlights — up to 6 enabled modules
  const featureHighlights = modules
    .filter((m) => MODULE_MARKETING_MAP[m.key] && m.is_enabled)
    .slice(0, 6)
    .map((m) => ({
      ...MODULE_MARKETING_MAP[m.key],
      moduleKey: m.key,
    }));

  // Featured templates
  const featuredTemplates = templates.filter((t) => t.is_featured).slice(0, 5);

  // Waitlist plan names
  const waitlistNames = plans
    .filter((p) => !PLAN_PRICING[p.name]?.available)
    .map((p) => p.display_name);

  return (
    <>
      {/* ─── HERO ─────────────────────────────────────────────────── */}
      <section
        className="relative min-h-screen flex items-center overflow-hidden"
        style={{ background: "#0B1320" }}
        aria-labelledby="hero-heading"
      >
        <div className="absolute inset-0 cockpit-grid opacity-60" aria-hidden="true" />
        <div
          className="absolute inset-0 pointer-events-none"
          aria-hidden="true"
          style={{
            background: "radial-gradient(ellipse 70% 60% at 50% 0%, rgba(15,118,110,0.3) 0%, transparent 65%)",
          }}
        />
        <div
          className="absolute top-1/3 left-0 w-64 h-64 rounded-full pointer-events-none"
          aria-hidden="true"
          style={{ background: "rgba(15,118,110,0.12)", filter: "blur(80px)" }}
        />
        <div
          className="absolute top-1/3 right-0 w-64 h-64 rounded-full pointer-events-none"
          aria-hidden="true"
          style={{ background: "rgba(20,184,166,0.1)", filter: "blur(80px)" }}
        />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-32 text-center">
          <div
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-8"
            style={{ background: "rgba(15,118,110,0.15)", border: "1px solid rgba(20,184,166,0.3)" }}
          >
            <span className="w-2 h-2 rounded-full animate-pulse-glow" style={{ background: "#14B8A6" }} aria-hidden="true" />
            <span className="text-xs font-semibold tracking-wider" style={{ color: "#14B8A6" }}>
              AI-NATIVE LEAD PLATFORM
            </span>
          </div>

          <h1
            id="hero-heading"
            className="text-5xl sm:text-6xl md:text-7xl font-bold text-white mb-6 tracking-tight leading-none"
          >
            Close More Leads.
            <br />
            <span className="gradient-text">Waste Zero Hours.</span>
          </h1>

          <p
            className="text-lg sm:text-xl max-w-2xl mx-auto mb-10 leading-relaxed"
            style={{ color: "rgba(148,163,184,0.9)" }}
          >
            LeadPilot captures, qualifies, and routes every inbound lead to the right rep —
            automatically. Turn raw traffic into closed revenue without adding headcount.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/contact" className="px-8 py-4 rounded-xl font-semibold text-base btn-primary">
              Book a Demo
            </Link>
            <Link
              href="/product"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-xl font-semibold text-sm btn-ghost-dark"
            >
              See Product
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
          </div>

          <div className="mt-20 grid grid-cols-3 gap-4 max-w-lg mx-auto">
            {[
              { icon: TrendingUp, label: "More pipeline", sub: "per rep" },
              { icon: Clock, label: "Faster response", sub: "on average" },
              { icon: Users, label: "Less headcount", sub: "needed to scale" },
            ].map(({ icon: Icon, label, sub }) => (
              <div key={label} className="text-center">
                <Icon className="w-5 h-5 mx-auto mb-2" style={{ color: "#14B8A6" }} aria-hidden="true" />
                <p className="text-xs font-semibold text-white">{label}</p>
                <p className="text-xs" style={{ color: "#475569" }}>{sub}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1" aria-hidden="true">
          <span className="text-xs" style={{ color: "#475569" }}>scroll</span>
          <div className="w-px h-8 animate-pulse" style={{ background: "linear-gradient(to bottom, #0F766E, transparent)" }} />
        </div>
      </section>

      {/* ─── SOCIAL PROOF STRIP ───────────────────────────────────── */}
      <section
        className="py-12 border-y"
        style={{ background: "#0E1826", borderColor: "rgba(255,255,255,0.06)" }}
        aria-label="Trusted by teams across industries"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-xs font-semibold uppercase tracking-widest mb-8" style={{ color: "#475569" }}>
            Trusted by revenue teams in
          </p>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-8 items-center">
            {["Real Estate", "Healthcare Clinics", "Marketing Agencies", "B2B Services", "Automotive", "Retail & SMB"].map((industry) => (
              <div key={industry} className="text-center">
                <span className="text-sm font-medium" style={{ color: "rgba(148,163,184,0.5)" }}>{industry}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── PROBLEM → SOLUTION ───────────────────────────────────── */}
      <section
        className="py-24"
        style={{ background: "#F8FAFC" }}
        aria-labelledby="problem-heading"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#EF4444" }}>The Problem</p>
              <h2 id="problem-heading" className="text-3xl sm:text-4xl font-bold mb-6 tracking-tight" style={{ color: "#0F172A" }}>
                Leads slip through the cracks every day.
              </h2>
              <ul className="space-y-4">
                {[
                  "Your sales team spends hours qualifying leads that never convert.",
                  "Hot prospects wait hours (or days) for a reply — then go cold.",
                  "No clear routing means the wrong rep picks up the wrong lead.",
                  "You can't see where the pipeline breaks without real-time data.",
                ].map((point) => (
                  <li key={point} className="flex items-start gap-3">
                    <div className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0" style={{ background: "#EF4444" }} aria-hidden="true" />
                    <p className="text-sm leading-relaxed" style={{ color: "#64748B" }}>{point}</p>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#0F766E" }}>The Solution</p>
              <h2 className="text-3xl sm:text-4xl font-bold mb-6 tracking-tight" style={{ color: "#0F172A" }}>
                LeadPilot handles the pipeline. You handle the close.
              </h2>
              <ul className="space-y-4">
                {[
                  "AI qualifies every lead the moment it arrives — 24/7, no lag.",
                  "Smart routing delivers leads to the right rep in seconds, not hours.",
                  "Automated follow-ups keep prospects engaged between touchpoints.",
                  "Real-time analytics show you exactly where revenue is being left behind.",
                ].map((point) => (
                  <li key={point} className="flex items-start gap-3">
                    <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" style={{ color: "#0F766E" }} aria-hidden="true" />
                    <p className="text-sm leading-relaxed" style={{ color: "#64748B" }}>{point}</p>
                  </li>
                ))}
              </ul>
              <Link href="/product" className="inline-flex items-center gap-2 mt-8 text-sm font-semibold text-link-primary">
                See how it works
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ─── HOW IT WORKS ─────────────────────────────────────────── */}
      <section
        className="py-24 relative overflow-hidden"
        style={{ background: "#0B1320" }}
        aria-labelledby="how-it-works-heading"
      >
        <div
          className="absolute inset-0 pointer-events-none"
          aria-hidden="true"
          style={{ background: "radial-gradient(ellipse 50% 60% at 50% 100%, rgba(15,118,110,0.2) 0%, transparent 70%)" }}
        />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#14B8A6" }}>How It Works</p>
            <h2 id="how-it-works-heading" className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
              Five steps from lead to revenue
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
            {steps.map((step, i) => (
              <div
                key={step.number}
                className="relative rounded-xl p-6"
                style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}
              >
                {i < steps.length - 1 && (
                  <div className="hidden lg:block absolute top-10 -right-3 w-6 h-px" aria-hidden="true" style={{ background: "rgba(15,118,110,0.4)" }} />
                )}
                <span
                  className="text-3xl font-bold block mb-4"
                  style={{ background: "linear-gradient(135deg, #0F766E, #14B8A6)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}
                >
                  {step.number}
                </span>
                <h3 className="text-white font-semibold mb-2">{step.title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: "#64748B" }}>{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FEATURE HIGHLIGHTS (DB-driven) ───────────────────────── */}
      <section
        className="py-24"
        style={{ background: "#F8FAFC" }}
        aria-labelledby="features-heading"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#0F766E" }}>Platform Features</p>
            <h2 id="features-heading" className="text-3xl sm:text-4xl font-bold tracking-tight" style={{ color: "#0F172A" }}>
              Everything your revenue team needs
            </h2>
            <p className="mt-4 text-base max-w-xl mx-auto" style={{ color: "#64748B" }}>
              One platform for the entire lead lifecycle — from first touch to closed deal.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {featureHighlights.map((feat) => (
              <FeatureCard
                key={feat.moduleKey}
                iconName={feat.iconName}
                benefit={feat.benefit}
                title={feat.marketingTitle}
                description={feat.description}
              />
            ))}
          </div>
          <div className="text-center mt-10">
            <Link href="/features" className="inline-flex items-center gap-2 text-sm font-semibold text-link-primary">
              View all features
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>

      {/* ─── TEMPLATES TEASER (DB-driven) ─────────────────────────── */}
      {featuredTemplates.length > 0 && (
        <section
          className="py-24 relative overflow-hidden"
          style={{ background: "#0B1320" }}
          aria-labelledby="templates-teaser-heading"
        >
          <div className="absolute inset-0 cockpit-grid opacity-30" aria-hidden="true" />
          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#14B8A6" }}>
                Templates
              </p>
              <h2 id="templates-teaser-heading" className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
                Ready-made automation flows
              </h2>
              <p className="mt-4 text-base max-w-xl mx-auto" style={{ color: "#64748B" }}>
                Clone a template, customise it for your business, and go live in minutes.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
              {featuredTemplates.map((t) => (
                <div key={t.id} className="catalog-card p-5">
                  <span className="badge-category" data-category={t.category}>
                    {t.category.replace(/_/g, " ")}
                  </span>
                  <h3 className="text-white font-semibold text-sm mt-3 mb-1">{t.name}</h3>
                  <p className="text-xs leading-relaxed line-clamp-2" style={{ color: "rgba(148,163,184,0.8)" }}>
                    {t.description}
                  </p>
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {t.platforms.map((p) => (
                      <span key={p} className="badge-platform">{p}</span>
                    ))}
                  </div>
                  {t.clone_count > 0 && (
                    <p className="text-[10px] mt-2" style={{ color: "#475569" }}>
                      {t.clone_count.toLocaleString()} clones
                    </p>
                  )}
                </div>
              ))}
            </div>
            <div className="text-center mt-10">
              <Link href="/templates" className="inline-flex items-center gap-2 text-sm font-semibold text-link-teal">
                Browse all templates
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ─── INTEGRATIONS TEASER (DB-driven) ──────────────────────── */}
      {providers.length > 0 && (
        <section
          className="py-24"
          style={{ background: "#F8FAFC" }}
          aria-labelledby="integrations-teaser-heading"
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#0F766E" }}>
                Integrations
              </p>
              <h2 id="integrations-teaser-heading" className="text-3xl sm:text-4xl font-bold tracking-tight" style={{ color: "#0F172A" }}>
                Connect your entire stack
              </h2>
              <p className="mt-4 text-base max-w-xl mx-auto" style={{ color: "#64748B" }}>
                Native integrations with the platforms your revenue team already uses.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-3xl mx-auto">
              {providers.map((p) => (
                <div
                  key={p.key}
                  className="rounded-xl p-6 text-center feature-card-light"
                >
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-4"
                    style={{
                      background: `${PROVIDER_COLORS[p.key] ?? "#0F766E"}15`,
                      border: `1px solid ${PROVIDER_COLORS[p.key] ?? "#0F766E"}30`,
                    }}
                  >
                    <span className="text-lg font-bold" style={{ color: PROVIDER_COLORS[p.key] ?? "#0F766E" }}>
                      {p.label.charAt(0)}
                    </span>
                  </div>
                  <h3 className="font-semibold text-base mb-1" style={{ color: "#1E293B" }}>
                    {p.label}
                  </h3>
                  <p className="text-xs leading-relaxed" style={{ color: "#64748B" }}>
                    {p.description}
                  </p>
                </div>
              ))}
            </div>
            <div className="text-center mt-10">
              <Link href="/integrations" className="inline-flex items-center gap-2 text-sm font-semibold text-link-primary">
                View all integrations
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ─── MINI PLANS PREVIEW (DB-driven) ───────────────────────── */}
      <section
        className="py-24 relative overflow-hidden"
        style={{ background: "#0B1320" }}
        aria-labelledby="plans-preview-heading"
      >
        <div
          className="absolute inset-0 pointer-events-none"
          aria-hidden="true"
          style={{ background: "radial-gradient(ellipse 60% 50% at 50% 50%, rgba(15,118,110,0.15) 0%, transparent 70%)" }}
        />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#14B8A6" }}>Plans</p>
            <h2 id="plans-preview-heading" className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
              Start free. Scale when ready.
            </h2>
          </div>

          <div className={`grid grid-cols-1 ${plans.length === 3 ? "md:grid-cols-3" : "md:grid-cols-2"} gap-6 max-w-4xl mx-auto`}>
            {plans.map((plan) => {
              const pricing = PLAN_PRICING[plan.name] ?? { price: "Contact Us", priceNote: "", tagline: "", available: false };
              const featureLines = plan.entitlements
                .map((e) => entitlementToString(e.module_key, e.hard_limit))
                .filter((s): s is string => s !== null)
                .slice(0, 6);

              return (
                <PlanCard
                  key={plan.id}
                  name={plan.display_name}
                  tagline={pricing.tagline || plan.description || ""}
                  price={pricing.price}
                  priceNote={pricing.priceNote}
                  features={featureLines}
                  ctaLabel={pricing.available ? "Get Started Free" : "Coming Soon"}
                  ctaHref={`${APP_URL}/signup`}
                  available={pricing.available}
                  highlighted={plan.name === "free"}
                />
              );
            })}
          </div>

          {waitlistNames.length > 0 && (
            <p className="text-center mt-8 text-sm" style={{ color: "#475569" }}>
              Join the waitlist for {waitlistNames.join(" and ")} —{" "}
              <Link href="/plans" className="underline underline-offset-2 transition-colors duration-200" style={{ color: "#14B8A6" }}>
                see Plans page
              </Link>
            </p>
          )}
        </div>
      </section>

      {/* ─── FINAL CTA ────────────────────────────────────────────── */}
      <CTASection
        headline="Your pipeline shouldn't depend on manual work."
        subheadline="LeadPilot automates lead capture, qualification, and routing so your team can focus on closing."
        primaryLabel="Book a Demo"
        primaryHref="/contact"
        secondaryLabel="Sign Up Free"
        secondaryHref={`${APP_URL}/signup`}
      />
    </>
  );
}
