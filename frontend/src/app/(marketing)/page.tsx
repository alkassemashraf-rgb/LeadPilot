import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  CheckCircle,
  Users,
  TrendingUp,
  Clock,
} from "lucide-react";
import CTASection from "@/components/marketing/CTASection";
import FeatureCard from "@/components/marketing/FeatureCard";
import PlanCard from "@/components/marketing/PlanCard";
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
        className="relative min-h-screen flex items-center overflow-hidden bg-[var(--dark-bg)]"
        aria-labelledby="hero-heading"
      >
        <div className="absolute inset-0 cockpit-grid cockpit-grid-3d opacity-60" aria-hidden="true" />
        {/* Animated scanline */}
        <div className="absolute inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent animate-scanline opacity-50 z-0 shadow-[0_0_15px_rgba(34,211,238,0.8)]" />

        <div
          className="absolute inset-0 pointer-events-none"
          aria-hidden="true"
          style={{
            background: "radial-gradient(ellipse 70% 60% at 50% 10%, rgba(15,118,110,0.3) 0%, var(--dark-bg) 75%)",
          }}
        />
        <div
          className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full pointer-events-none"
          aria-hidden="true"
          style={{ background: "rgba(34, 211, 238, 0.15)", filter: "blur(100px)", mixBlendMode: "screen" }}
        />
        <div
          className="absolute top-1/3 right-1/4 w-96 h-96 rounded-full pointer-events-none"
          aria-hidden="true"
          style={{ background: "rgba(192, 132, 252, 0.15)", filter: "blur(100px)", mixBlendMode: "screen" }}
        />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-32 text-center">
          <div
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-8 animate-fade-up"
            style={{ background: "rgba(34, 211, 238, 0.15)", border: "1px solid rgba(34, 211, 238, 0.3)" }}
          >
            <span className="w-2 h-2 rounded-full animate-pulse-glow" style={{ background: "var(--neon-cyan)" }} aria-hidden="true" />
            <span className="text-xs font-bold tracking-wider" style={{ color: "var(--neon-cyan)" }}>
              AI-NATIVE PIPELINE
            </span>
          </div>

          <h1
            id="hero-heading"
            className="text-5xl sm:text-6xl md:text-7xl font-extrabold text-white mb-6 tracking-tight leading-none animate-fade-up"
            style={{ animationDelay: "0.1s" }}
          >
            Close More Leads.
            <br />
            <span className="gradient-text">Waste Zero Hours.</span>
          </h1>

          <p
            className="text-lg sm:text-xl max-w-2xl mx-auto mb-10 leading-relaxed animate-fade-up"
            style={{ color: "rgba(148,163,184,0.9)", animationDelay: "0.2s" }}
          >
            LeadPilot captures, qualifies, and routes every inbound lead to the right rep —
            automatically. Turn raw traffic into closed revenue without adding headcount.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-fade-up" style={{ animationDelay: "0.3s" }}>
            <Link href="/contact" className="px-8 py-4 rounded-xl font-semibold text-base btn-primary glow-primary">
              Deploy AI Agent
            </Link>
            <Link
              href="/product"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-xl font-semibold text-sm glass-panel hover:border-teal-400 transition-colors text-white"
            >
              See Product
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
          </div>

          <div className="mt-20 grid grid-cols-3 gap-4 max-w-2xl mx-auto animate-fade-up" style={{ animationDelay: "0.4s" }}>
            {[
              { icon: TrendingUp, label: "More pipeline", sub: "per rep", color: "var(--neon-cyan)" },
              { icon: Clock, label: "Instant response", sub: "always online", color: "var(--secondary)" },
              { icon: Users, label: "Less headcount", sub: "needed to scale", color: "var(--neon-purple)" },
            ].map(({ icon: Icon, label, sub, color }) => (
              <div key={label} className="text-center glass-panel p-4 rounded-2xl relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-t from-transparent to-white/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                <Icon className="w-6 h-6 mx-auto mb-3" style={{ color }} aria-hidden="true" />
                <p className="text-sm font-bold text-white">{label}</p>
                <p className="text-xs mt-1" style={{ color: "#94A3B8" }}>{sub}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Decorative Floating Elements */}
        <div className="absolute top-1/4 left-1/4 w-32 h-32 border border-teal-500/20 rounded-full animate-float-delayed flex items-center justify-center -z-10 hidden md:flex">
          <div className="w-16 h-16 border border-teal-400/30 rounded-full flex items-center justify-center">
            <div className="w-2 h-2 bg-teal-400 rounded-full animate-pulse-glow" />
          </div>
        </div>
        <div className="absolute top-1/3 right-1/4 w-40 h-40 border border-cyan-500/20 rounded-full animate-float flex items-center justify-center -z-10 hidden md:flex">
          <div className="w-20 h-20 border border-cyan-400/30 rounded-full flex items-center justify-center">
            <div className="w-3 h-3 bg-cyan-400 rounded-full animate-pulse-glow" />
          </div>
        </div>

        <div className="absolute bottom-12 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2" aria-hidden="true">
          <span className="text-[10px] uppercase font-bold tracking-widest" style={{ color: "var(--neon-cyan)" }}>Initiate</span>
          <div className="w-[2px] h-12 bg-gradient-to-b from-cyan-400 to-transparent animate-pulse" />
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
        className="py-24 relative overflow-hidden"
        style={{ background: "var(--dark-bg)" }}
        aria-labelledby="problem-heading"
      >
        <div className="absolute inset-0 cockpit-grid opacity-20" aria-hidden="true" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            {/* The Problem */}
            <div className="glass-panel p-10 rounded-3xl relative overflow-hidden group">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-500/0 via-red-500/50 to-red-500/0 opacity-50" />
              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#EF4444" }}>The Problem</p>
              <h2 id="problem-heading" className="text-3xl sm:text-4xl font-bold mb-6 tracking-tight text-white">
                Leads slip through the cracks every day.
              </h2>
              <ul className="space-y-5">
                {[
                  "Sales teams spend hours qualifying leads that never convert.",
                  "Hot prospects wait hours (or days) for a reply — then go cold.",
                  "No clear routing means the wrong rep picks up the wrong lead.",
                  "You can't see where the pipeline breaks without real-time data.",
                ].map((point) => (
                  <li key={point} className="flex items-start gap-3">
                    <div className="mt-2 w-1.5 h-1.5 rounded-full shrink-0 shadow-[0_0_8px_#EF4444]" style={{ background: "#EF4444" }} aria-hidden="true" />
                    <p className="text-sm leading-relaxed" style={{ color: "rgba(148,163,184,0.9)" }}>{point}</p>
                  </li>
                ))}
              </ul>
            </div>

            {/* The Solution */}
            <div className="glass-panel p-10 rounded-3xl relative overflow-hidden gradient-border-spin group">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-400/0 via-cyan-400/50 to-cyan-400/0 opacity-50" />
              <p className="text-xs font-bold uppercase tracking-widest mb-3 text-cyan-400 hover:animate-pulse">The Solution</p>
              <h2 className="text-3xl sm:text-4xl font-bold mb-6 tracking-tight text-white">
                AI handles the pipeline. You handle the close.
              </h2>
              <ul className="space-y-5">
                {[
                  "AI agents qualify every lead the moment it arrives — 24/7, zero lag.",
                  "Smart routing rules deliver leads to the right rep in milliseconds.",
                  "Automated, multi-channel follow-ups keep prospects engaged.",
                  "Live analytics show you exactly where revenue is left behind.",
                ].map((point) => (
                  <li key={point} className="flex items-start gap-3">
                    <CheckCircle className="w-5 h-5 mt-0.5 shrink-0 text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.5)]" aria-hidden="true" />
                    <p className="text-sm leading-relaxed" style={{ color: "rgba(148,163,184,0.9)" }}>{point}</p>
                  </li>
                ))}
              </ul>
              <Link href="/product" className="inline-flex items-center gap-2 mt-8 text-sm font-semibold text-cyan-400 hover:text-cyan-300 transition-colors group/link">
                Initiate Sequence
                <ArrowRight className="w-4 h-4 group-hover/link:translate-x-1 transition-transform" aria-hidden="true" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ─── HOW IT WORKS ─────────────────────────────────────────── */}
      <section
        className="py-32 relative overflow-hidden"
        style={{ background: "#060B14" }}
        aria-labelledby="how-it-works-heading"
      >
        <div
          className="absolute inset-0 pointer-events-none"
          aria-hidden="true"
          style={{ background: "radial-gradient(ellipse 80% 50% at 50% 100%, rgba(34, 211, 238, 0.1) 0%, transparent 60%)" }}
        />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-20 animate-fade-up">
            <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "var(--neon-cyan)" }}>Data Pipeline</p>
            <h2 id="how-it-works-heading" className="text-3xl sm:text-4xl md:text-5xl font-bold text-white tracking-tight">
              Five automated jumps to revenue
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-8 lg:gap-4 relative">
            {/* The animated connecting wire (desktop) */}
            <div className="hidden lg:block absolute top-[44px] left-10 right-10 h-0.5 bg-slate-800 -z-10">
              <div
                className="h-full bg-gradient-to-r from-cyan-500/0 via-cyan-400 to-cyan-500/0 animate-scanline"
                style={{ animationDirection: "normal", transformOrigin: "left" }}
              />
            </div>

            {steps.map((step, i) => (
              <div
                key={step.number}
                className="relative rounded-2xl p-6 glass-panel hover:border-cyan-500/50 transition-colors animate-fade-up group"
                style={{ animationDelay: `${i * 0.15 + 0.2}s` }}
              >
                <div className="w-10 h-10 rounded-full flex items-center justify-center bg-cyan-950/50 border border-cyan-500/30 mb-6 group-hover:shadow-[0_0_15px_rgba(34,211,238,0.4)] transition-shadow">
                  <span className="text-sm font-bold text-cyan-400">{step.number}</span>
                </div>
                <h3 className="text-white font-semibold mb-3">{step.title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: "#94A3B8" }}>{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FEATURE HIGHLIGHTS (DB-driven) ───────────────────────── */}
      <section
        className="py-24 relative"
        style={{ background: "#0B1320" }}
        aria-labelledby="features-heading"
      >
        <div className="absolute inset-0 cockpit-grid opacity-30" aria-hidden="true" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 animate-fade-up">
            <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "var(--neon-cyan)" }}>Platform Features</p>
            <h2 id="features-heading" className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
              Everything your revenue team needs
            </h2>
            <p className="mt-4 text-base max-w-xl mx-auto" style={{ color: "rgba(148,163,184,0.9)" }}>
              One platform for the entire lead lifecycle — from first touch to closed deal.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {featureHighlights.map((feat, i) => (
              <div key={feat.moduleKey} className="animate-fade-up" style={{ animationDelay: `${i * 0.1}s` }}>
                <FeatureCard
                  iconName={feat.iconName}
                  benefit={feat.benefit}
                  title={feat.marketingTitle}
                  description={feat.description}
                  dark={true}
                />
              </div>
            ))}
          </div>
          <div className="text-center mt-10">
            <Link href="/features" className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-400 hover:text-cyan-300 transition-colors">
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
          style={{ background: "var(--dark-bg)" }}
          aria-labelledby="templates-teaser-heading"
        >
          <div className="absolute inset-0 cockpit-grid opacity-20" aria-hidden="true" />
          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16 animate-fade-up">
              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "var(--neon-purple)" }}>
                Execution Patterns
              </p>
              <h2 id="templates-teaser-heading" className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
                Ready-made automation flows
              </h2>
              <p className="mt-4 text-base max-w-xl mx-auto" style={{ color: "rgba(148,163,184,0.9)" }}>
                Clone a template, customise it for your business, and go live in minutes.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
              {featuredTemplates.map((t, i) => (
                <div key={t.id} className="catalog-card p-5 animate-fade-up" style={{ animationDelay: `${i * 0.1}s` }}>
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
                    <p className="text-[10px] mt-2 font-mono" style={{ color: "#475569" }}>
                      [{t.clone_count.toLocaleString()} CLONES]
                    </p>
                  )}
                </div>
              ))}
            </div>
            <div className="text-center mt-10">
              <Link href="/templates" className="inline-flex items-center gap-2 text-sm font-semibold text-purple-400 hover:text-purple-300 transition-colors">
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
          className="py-24 relative overflow-hidden"
          style={{ background: "#0B1320" }}
          aria-labelledby="integrations-teaser-heading"
        >
          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16 animate-fade-up">
              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "var(--neon-cyan)" }}>
                Integrations
              </p>
              <h2 id="integrations-teaser-heading" className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
                Connect your entire stack
              </h2>
              <p className="mt-4 text-base max-w-xl mx-auto" style={{ color: "rgba(148,163,184,0.9)" }}>
                Native integrations with the platforms your revenue team already uses.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-3xl mx-auto">
              {providers.map((p, i) => (
                <div
                  key={p.key}
                  className="rounded-xl p-6 text-center glass-panel hover:border-cyan-500/30 transition-colors animate-fade-up"
                  style={{ animationDelay: `${i * 0.15}s` }}
                >
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-4"
                    style={{
                      background: `${PROVIDER_COLORS[p.key] ?? "#0F766E"}20`,
                      border: `1px solid ${PROVIDER_COLORS[p.key] ?? "#0F766E"}40`,
                    }}
                  >
                    <span className="text-lg font-bold" style={{ color: PROVIDER_COLORS[p.key] ?? "#0F766E" }}>
                      {p.label.charAt(0)}
                    </span>
                  </div>
                  <h3 className="font-semibold text-base mb-1 text-white">
                    {p.label}
                  </h3>
                  <p className="text-xs leading-relaxed" style={{ color: "rgba(148,163,184,0.8)" }}>
                    {p.description}
                  </p>
                </div>
              ))}
            </div>
            <div className="text-center mt-10">
              <Link href="/integrations" className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-400 hover:text-cyan-300 transition-colors">
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
        style={{ background: "var(--dark-bg)" }}
        aria-labelledby="plans-preview-heading"
      >
        <div className="absolute inset-0 cockpit-grid opacity-20" aria-hidden="true" />
        <div
          className="absolute inset-0 pointer-events-none"
          aria-hidden="true"
          style={{ background: "radial-gradient(ellipse 60% 50% at 50% 50%, rgba(34, 211, 238, 0.1) 0%, transparent 70%)" }}
        />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 animate-fade-up">
            <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "var(--neon-cyan)" }}>Deployment Options</p>
            <h2 id="plans-preview-heading" className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
              Start free. Scale when ready.
            </h2>
          </div>

          <div className={`grid grid-cols-1 ${plans.length === 3 ? "md:grid-cols-3" : "md:grid-cols-2"} gap-6 max-w-4xl mx-auto`}>
            {plans.map((plan, i) => {
              const pricing = PLAN_PRICING[plan.name] ?? { price: "Contact Us", priceNote: "", tagline: "", available: false };
              const featureLines = plan.entitlements
                .map((e) => entitlementToString(e.module_key, e.hard_limit))
                .filter((s): s is string => s !== null)
                .slice(0, 6);

              return (
                <div key={plan.id} className="animate-fade-up" style={{ animationDelay: `${i * 0.15}s` }}>
                  <PlanCard
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
                </div>
              );
            })}
          </div>

          {waitlistNames.length > 0 && (
            <p className="text-center mt-8 text-xs font-mono" style={{ color: "rgba(148,163,184,0.6)" }}>
               // AWAITING DEPLOYMENT FOR {waitlistNames.join(" AND ").toUpperCase()} —{" "}
              <Link href="/plans" className="hover:text-cyan-400 transition-colors" style={{ color: "var(--neon-cyan)" }}>
                INITIALIZE
              </Link>
            </p>
          )}
        </div>
      </section>

      {/* ─── FINAL CTA ────────────────────────────────────────────── */}
      <CTASection
        headline="Deploy your AI pipeline today."
        subheadline="LeadPilot automates lead capture, qualification, and routing so your team can focus on closing."
        primaryLabel="Deploy AI Agent"
        primaryHref="/contact"
        secondaryLabel="Start Free Tier"
        secondaryHref={`${APP_URL}/signup`}
      />
    </>
  );
}
