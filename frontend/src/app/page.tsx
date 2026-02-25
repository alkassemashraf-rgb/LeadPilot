import type { Metadata } from "next";
import Link from "next/link";
import {
  Zap, Target, GitMerge, BarChart3, MessageSquare, Shield,
  ArrowRight, CheckCircle, Users, TrendingUp, Clock,
} from "lucide-react";
import MarketingHeader from "@/components/marketing/Header";
import MarketingFooter from "@/components/marketing/Footer";
import CTASection from "@/components/marketing/CTASection";
import FeatureCard from "@/components/marketing/FeatureCard";
import PlanCard from "@/components/marketing/PlanCard";
import AnimateOnScroll from "@/components/marketing/AnimateOnScroll";
import FloatingOrb from "@/components/marketing/FloatingOrb";

export const metadata: Metadata = {
  title: "LeadPilot — AI-Native Lead Capture, Qualification & Routing",
  description:
    "LeadPilot is the AI-native platform that captures, qualifies, and routes leads to the right rep automatically. Close more deals without growing headcount.",
};

const features = [
  { icon: Zap, benefit: "Convert faster", title: "AI Lead Qualification", description: "Custom AI prompts score and qualify every inbound lead in seconds. No manual filtering, no missed opportunities." },
  { icon: Target, benefit: "Zero leakage", title: "Multi-Channel Capture", description: "Capture leads from web forms, chat widgets, WhatsApp, and more — all routed into one unified pipeline." },
  { icon: GitMerge, benefit: "Right rep, right time", title: "Smart Routing Rules", description: "Route leads by territory, product line, availability, or any custom logic you define. Instant assignment." },
  { icon: BarChart3, benefit: "Improve decisions", title: "Conversion Analytics", description: "Track lead-to-close conversion rates, response times, and team performance across the full funnel." },
  { icon: MessageSquare, benefit: "Stay human", title: "Team Inbox & Handover", description: "AI handles first touch and qualification; your team steps in exactly when a human connection matters." },
  { icon: Shield, benefit: "Audit-ready", title: "Activity Log & Access Control", description: "Role-based permissions and full audit trail. Know who touched what, and when." },
];

const steps = [
  { number: "01", title: "Capture", description: "Leads arrive from any channel — your forms, chat, or integrations. LeadPilot ingests them all instantly." },
  { number: "02", title: "Qualify", description: "Our AI engages, asks the right questions, and scores every lead based on your ideal customer profile." },
  { number: "03", title: "Route", description: "Qualified leads are dispatched to the right rep or team — automatically, with zero manual hand-off." },
  { number: "04", title: "Follow Up", description: "Automated follow-up sequences keep leads warm while your team focuses on closing." },
  { number: "05", title: "Report", description: "Real-time dashboards show conversion rates, pipeline velocity, and where you're losing leads." },
];

const plans = [
  {
    name: "Free", tagline: "Start capturing leads today", price: "$0", priceNote: "/ month",
    features: ["Basic lead capture (up to a limited number of leads)", "AI qualification prompts", "Manual routing", "Email notifications", "Basic analytics dashboard", "1 team seat"],
    ctaLabel: "Get Started Free", ctaHref: "/signup", available: true, highlighted: true,
  },
  {
    name: "Growth", tagline: "For growing sales teams", price: "Coming Soon",
    features: ["Everything in Free", "Unlimited lead capture", "Advanced AI qualification", "Automated routing rules", "CRM integrations", "Up to 5 team seats"],
    ctaLabel: "Coming Soon", available: false,
  },
  {
    name: "Pro", tagline: "For high-volume pipelines", price: "Coming Soon",
    features: ["Everything in Growth", "Multi-channel capture", "Custom AI playbooks", "Team inbox & handover", "Priority support", "Unlimited seats"],
    ctaLabel: "Coming Soon", available: false,
  },
];

export default function HomePage() {
  return (
    <div className="flex flex-col min-h-screen">
      <MarketingHeader />
      <main className="flex-1">

        {/* ─── HERO ─────────────────────────────────────────────────── */}
        <section
          className="relative min-h-screen flex items-center overflow-hidden"
          style={{ background: "var(--mk-dark-bg)" }}
          aria-labelledby="hero-heading"
        >
          {/* Animated grid */}
          <div className="absolute inset-0 mk-grid opacity-60" aria-hidden="true" />

          {/* Radial glow */}
          <div
            className="absolute inset-0 pointer-events-none"
            aria-hidden="true"
            style={{ background: "radial-gradient(ellipse 70% 60% at 50% 0%, rgba(15,118,110,0.3) 0%, transparent 65%)" }}
          />

          {/* Floating orbs */}
          <FloatingOrb size={480} color="primary" top="30%" left="10%" opacity={0.12} blur={100} />
          <FloatingOrb size={360} color="secondary" top="40%" right="5%" opacity={0.10} blur={80} />

          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-32 text-center">
            {/* Badge */}
            <AnimateOnScroll animation="fadeIn" duration={600}>
              <div
                className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-8"
                style={{ background: "rgba(15,118,110,0.15)", border: "1px solid rgba(20,184,166,0.3)" }}
              >
                <span className="w-2 h-2 rounded-full" style={{ background: "#14B8A6", animation: "mk-pulse-ring 2s ease-out infinite" }} aria-hidden="true" />
                <span className="text-xs font-semibold tracking-wider" style={{ color: "#14B8A6" }}>AI-NATIVE LEAD PLATFORM</span>
              </div>
            </AnimateOnScroll>

            {/* Headline */}
            <AnimateOnScroll animation="fadeUp" delay={80} duration={800}>
              <h1
                id="hero-heading"
                className="text-5xl sm:text-6xl md:text-7xl font-bold text-white mb-6 tracking-tight leading-none"
              >
                Close More Leads.
                <br />
                <span className="mk-gradient-text">Waste Zero Hours.</span>
              </h1>
            </AnimateOnScroll>

            <AnimateOnScroll animation="fadeUp" delay={160}>
              <p className="text-lg sm:text-xl max-w-2xl mx-auto mb-10 leading-relaxed" style={{ color: "rgba(148,163,184,0.9)" }}>
                LeadPilot captures, qualifies, and routes every inbound lead to the right rep —
                automatically. Turn raw traffic into closed revenue without adding headcount.
              </p>
            </AnimateOnScroll>

            <AnimateOnScroll animation="zoomIn" delay={240}>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link href="/signup" className="px-8 py-4 rounded-xl font-semibold text-base mk-btn-primary">
                  Start for Free
                </Link>
                <Link href="/product" className="inline-flex items-center gap-2 px-8 py-4 rounded-xl font-semibold text-sm mk-btn-ghost-dark">
                  See Product
                  <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </Link>
              </div>
            </AnimateOnScroll>

            {/* Trust stats */}
            <AnimateOnScroll animation="fadeUp" delay={360}>
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
            </AnimateOnScroll>
          </div>

          {/* Scroll indicator */}
          <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1" aria-hidden="true">
            <span className="text-xs" style={{ color: "#475569" }}>scroll</span>
            <div className="w-px h-8 animate-pulse" style={{ background: "linear-gradient(to bottom, #0F766E, transparent)" }} />
          </div>
        </section>

        {/* ─── SOCIAL PROOF STRIP ───────────────────────────────────── */}
        <section className="py-12 border-y" style={{ background: "#0E1826", borderColor: "rgba(255,255,255,0.06)" }} aria-label="Trusted by teams across industries">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <AnimateOnScroll animation="fadeIn">
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
            </AnimateOnScroll>
          </div>
        </section>

        {/* ─── PROBLEM → SOLUTION ───────────────────────────────────── */}
        <section className="py-24" style={{ background: "#F8FAFC" }} aria-labelledby="problem-heading">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
              <AnimateOnScroll animation="fadeLeft">
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
              </AnimateOnScroll>

              <AnimateOnScroll animation="fadeRight" delay={120}>
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
                  <Link href="/product" className="inline-flex items-center gap-2 mt-8 text-sm font-semibold mk-text-link">
                    See how it works
                    <ArrowRight className="w-4 h-4" aria-hidden="true" />
                  </Link>
                </div>
              </AnimateOnScroll>
            </div>
          </div>
        </section>

        {/* ─── HOW IT WORKS ─────────────────────────────────────────── */}
        <section className="py-24 relative overflow-hidden" style={{ background: "#0B1320" }} aria-labelledby="how-it-works-heading">
          <div className="absolute inset-0 pointer-events-none" aria-hidden="true"
            style={{ background: "radial-gradient(ellipse 50% 60% at 50% 100%, rgba(15,118,110,0.2) 0%, transparent 70%)" }}
          />
          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <AnimateOnScroll animation="fadeUp">
              <div className="text-center mb-16">
                <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#14B8A6" }}>How It Works</p>
                <h2 id="how-it-works-heading" className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
                  Five steps from lead to revenue
                </h2>
              </div>
            </AnimateOnScroll>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
              {steps.map((step, i) => (
                <AnimateOnScroll key={step.number} animation="fadeUp" delay={i * 80}>
                  <div
                    className="relative rounded-xl p-6 h-full"
                    style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}
                  >
                    {i < steps.length - 1 && (
                      <div className="hidden lg:block absolute top-10 -right-3 w-6 h-px" aria-hidden="true"
                        style={{ background: "rgba(15,118,110,0.4)" }}
                      />
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
                </AnimateOnScroll>
              ))}
            </div>
          </div>
        </section>

        {/* ─── FEATURE HIGHLIGHTS ───────────────────────────────────── */}
        <section className="py-24" style={{ background: "#F8FAFC" }} aria-labelledby="features-heading">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <AnimateOnScroll animation="fadeUp">
              <div className="text-center mb-16">
                <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#0F766E" }}>Platform Features</p>
                <h2 id="features-heading" className="text-3xl sm:text-4xl font-bold tracking-tight" style={{ color: "#0F172A" }}>
                  Everything your revenue team needs
                </h2>
                <p className="mt-4 text-base max-w-xl mx-auto" style={{ color: "#64748B" }}>
                  One platform for the entire lead lifecycle — from first touch to closed deal.
                </p>
              </div>
            </AnimateOnScroll>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {features.map((feat, i) => (
                <AnimateOnScroll key={feat.title} animation="fadeUp" delay={i * 60}>
                  <FeatureCard {...feat} />
                </AnimateOnScroll>
              ))}
            </div>

            <AnimateOnScroll animation="fadeIn" delay={400}>
              <div className="text-center mt-10">
                <Link href="/features" className="inline-flex items-center gap-2 text-sm font-semibold mk-text-link">
                  View all features
                  <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </Link>
              </div>
            </AnimateOnScroll>
          </div>
        </section>

        {/* ─── MINI PLANS PREVIEW ───────────────────────────────────── */}
        <section className="py-24 relative overflow-hidden" style={{ background: "#0B1320" }} aria-labelledby="plans-preview-heading">
          <div className="absolute inset-0 pointer-events-none" aria-hidden="true"
            style={{ background: "radial-gradient(ellipse 60% 50% at 50% 50%, rgba(15,118,110,0.15) 0%, transparent 70%)" }}
          />
          <FloatingOrb size={300} color="mixed" top="50%" left="50%" opacity={0.08} blur={120} drift={false} />

          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <AnimateOnScroll animation="fadeUp">
              <div className="text-center mb-16">
                <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#14B8A6" }}>Plans</p>
                <h2 id="plans-preview-heading" className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
                  Start free. Scale when ready.
                </h2>
              </div>
            </AnimateOnScroll>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {plans.map((plan, i) => (
                <AnimateOnScroll key={plan.name} animation="zoomIn" delay={i * 80}>
                  <PlanCard {...plan} />
                </AnimateOnScroll>
              ))}
            </div>

            <AnimateOnScroll animation="fadeIn" delay={300}>
              <p className="text-center mt-8 text-sm" style={{ color: "#475569" }}>
                Join the waitlist for Growth and Pro —{" "}
                <Link href="/plans" className="underline underline-offset-2 mk-text-link-teal">see Plans page</Link>
              </p>
            </AnimateOnScroll>
          </div>
        </section>

        {/* ─── FINAL CTA ────────────────────────────────────────────── */}
        <CTASection
          headline="Your pipeline shouldn't depend on manual work."
          subheadline="LeadPilot automates lead capture, qualification, and routing so your team can focus on closing."
          primaryLabel="Start for Free"
          primaryHref="/signup"
          secondaryLabel="See Plans"
          secondaryHref="/plans"
        />

      </main>
      <MarketingFooter />
    </div>
  );
}
