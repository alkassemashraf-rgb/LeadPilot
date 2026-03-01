"use client";

import { useState } from "react";
import {
  Check,
  Clock,
  ChevronDown,
  ChevronUp,
  Loader2,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import Link from "next/link";
import type { CatalogPlan } from "@/lib/api";
import { APP_URL } from "@/lib/api";
import { MODULE_MARKETING_MAP } from "@/lib/moduleMap";

// ── Pricing config (not in DB — marketing copy) ─────────────────────

const PLAN_PRICING: Record<string, { price: string; priceNote: string; tagline: string; available: boolean }> = {
  free: {
    price: "$0",
    priceNote: "/ month, forever",
    tagline: "Start capturing and qualifying leads today",
    available: true,
  },
  growth: {
    price: "Coming Soon",
    priceNote: "",
    tagline: "For growing sales teams with higher volume",
    available: false,
  },
  enterprise: {
    price: "Contact Us",
    priceNote: "",
    tagline: "Custom deployment for large organisations",
    available: false,
  },
};

function entitlementToString(moduleKey: string, hardLimit: number | null): string | null {
  const info = MODULE_MARKETING_MAP[moduleKey];
  if (!info) return null;
  if (hardLimit === null) return `${info.marketingTitle} (Unlimited)`;
  if (hardLimit > 0) return `${info.marketingTitle} (up to ${hardLimit.toLocaleString()})`;
  return info.marketingTitle;
}

// ── FAQs (marketing copy, not feature claims) ───────────────────────

const faqs = [
  {
    question: "Is the Free plan actually free? No hidden fees?",
    answer:
      "Yes. The Free plan is genuinely free with no credit card required. You get full access to core capture and qualification features up to the plan limits. We will always have a free tier.",
  },
  {
    question: "When will Growth and Enterprise plans be available?",
    answer:
      "We're in active development. Join the waitlist below and you'll be among the first to know — and receive early-access pricing when we launch.",
  },
  {
    question: "Can I upgrade from Free to a paid plan later?",
    answer:
      "Absolutely. Your data and configuration will carry over. Upgrading will unlock higher limits and additional features without any migration needed.",
  },
  {
    question: "How does lead volume work on the Free plan?",
    answer:
      "The Free plan includes a reasonable monthly lead capture limit suitable for small teams getting started. We'll always be transparent about limits — no surprise overages.",
  },
  {
    question: "Do you offer refunds?",
    answer:
      "Paid plans (when available) will include a 14-day money-back guarantee. We'd rather earn your business on value than lock you in.",
  },
];

// ── Sub-components ──────────────────────────────────────────────────

function WaitlistForm({ planNames }: { planNames: string[] }) {
  const [email, setEmail] = useState("");
  const [plan, setPlan] = useState(planNames[0] ?? "Growth");
  const [state, setState] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }
    setError("");
    setState("loading");
    // TODO: wire to real waitlist API
    await new Promise((r) => setTimeout(r, 1200));
    setState("success");
  }

  if (state === "success") {
    return (
      <div className="flex flex-col items-center gap-3 py-8 text-center" role="alert">
        <CheckCircle className="w-10 h-10" style={{ color: "#14B8A6" }} aria-hidden="true" />
        <p className="text-base font-semibold text-white">You&apos;re on the list.</p>
        <p className="text-sm" style={{ color: "#94A3B8" }}>
          We&apos;ll notify you as soon as {plan} launches — including early-access pricing.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Waitlist signup form">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1">
          <label htmlFor="waitlist-email" className="sr-only">Work email</label>
          <input
            id="waitlist-email"
            type="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); setError(""); }}
            placeholder="your@company.com"
            required
            aria-required="true"
            aria-describedby={error ? "waitlist-error" : undefined}
            className="w-full px-4 py-3 rounded-xl text-sm placeholder:text-slate-600"
            style={{
              background: "rgba(255,255,255,0.06)",
              border: error ? "1px solid rgba(239,68,68,0.5)" : "1px solid rgba(255,255,255,0.1)",
              color: "#F1F5F9",
              outline: "none",
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = "#0F766E";
              e.currentTarget.style.boxShadow = "0 0 0 3px rgba(15,118,110,0.2)";
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = error ? "rgba(239,68,68,0.5)" : "rgba(255,255,255,0.1)";
              e.currentTarget.style.boxShadow = "none";
            }}
          />
        </div>
        <div>
          <label htmlFor="waitlist-plan" className="sr-only">Plan interest</label>
          <select
            id="waitlist-plan"
            value={plan}
            onChange={(e) => setPlan(e.target.value)}
            className="w-full sm:w-36 px-4 py-3 rounded-xl text-sm"
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.1)",
              color: "#F1F5F9",
              outline: "none",
            }}
          >
            {planNames.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={state === "loading"}
          className="px-6 py-3 rounded-xl font-semibold text-white text-sm flex items-center justify-center gap-2 transition-all duration-200"
          style={{
            background: state === "loading"
              ? "rgba(15,118,110,0.5)"
              : "linear-gradient(135deg, #0F766E, #14B8A6)",
            cursor: state === "loading" ? "not-allowed" : "pointer",
          }}
          onMouseEnter={(e) => {
            if (state !== "loading") e.currentTarget.style.boxShadow = "0 0 20px rgba(15,118,110,0.4)";
          }}
          onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "none"; }}
        >
          {state === "loading" && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />}
          {state === "loading" ? "Joining…" : "Join Waitlist"}
        </button>
      </div>
      {error && (
        <p id="waitlist-error" className="mt-2 text-xs flex items-center gap-1.5" style={{ color: "#FCA5A5" }} role="alert">
          <AlertCircle className="w-3.5 h-3.5" aria-hidden="true" /> {error}
        </p>
      )}
    </form>
  );
}

function FAQItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.08)" }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-6 py-5 text-left"
        aria-expanded={open}
        style={{ background: "rgba(255,255,255,0.03)" }}
        onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(15,118,110,0.06)"; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.03)"; }}
      >
        <span className="text-sm font-semibold text-white pr-4">{question}</span>
        {open
          ? <ChevronUp className="w-4 h-4 shrink-0" style={{ color: "#14B8A6" }} aria-hidden="true" />
          : <ChevronDown className="w-4 h-4 shrink-0" style={{ color: "#475569" }} aria-hidden="true" />
        }
      </button>
      {open && (
        <div
          className="px-6 pb-5 pt-2"
          style={{ background: "rgba(255,255,255,0.02)", borderTop: "1px solid rgba(255,255,255,0.06)" }}
        >
          <p className="text-sm leading-relaxed" style={{ color: "#94A3B8" }}>{answer}</p>
        </div>
      )}
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────

export default function PlansClientContent({ plans }: { plans: CatalogPlan[] }) {
  // Unavailable plan names for waitlist selector (exclude free)
  const waitlistPlanNames = plans
    .filter((p) => !PLAN_PRICING[p.name]?.available)
    .map((p) => p.display_name);

  return (
    <>
      {/* ─── HERO ─────────────────────────────────────────────────── */}
      <section
        className="relative py-28 overflow-hidden"
        style={{ background: "#0B1320" }}
        aria-labelledby="plans-hero-heading"
      >
        <div className="absolute inset-0 cockpit-grid opacity-40" aria-hidden="true" />
        <div
          className="absolute inset-0 pointer-events-none"
          aria-hidden="true"
          style={{
            background: "radial-gradient(ellipse 60% 50% at 50% 0%, rgba(15,118,110,0.25) 0%, transparent 70%)",
          }}
        />
        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-xs font-bold uppercase tracking-widest mb-4" style={{ color: "#14B8A6" }}>
            Pricing
          </p>
          <h1
            id="plans-hero-heading"
            className="text-4xl sm:text-5xl md:text-6xl font-bold text-white mb-6 tracking-tight"
          >
            Start free.
            <br />
            <span className="gradient-text">Scale when you&apos;re ready.</span>
          </h1>
          <p className="text-lg max-w-xl mx-auto leading-relaxed" style={{ color: "rgba(148,163,184,0.9)" }}>
            The Free plan is available now with no credit card required.
            {waitlistPlanNames.length > 0 && (
              <> {waitlistPlanNames.join(" and ")} plans are coming soon — join the waitlist for early access.</>
            )}
          </p>
        </div>
      </section>

      {/* ─── PLANS GRID ───────────────────────────────────────────── */}
      <section
        className="py-24"
        style={{ background: "#0B1320" }}
        aria-labelledby="plans-grid-heading"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 id="plans-grid-heading" className="sr-only">Available plans</h2>

          {plans.length === 0 ? (
            <p className="text-center text-lg" style={{ color: "#64748B" }}>
              Plans are loading. Check back soon.
            </p>
          ) : (
            <div className={`grid grid-cols-1 ${plans.length === 3 ? "md:grid-cols-3" : "md:grid-cols-2 xl:grid-cols-4"} gap-6 max-w-5xl mx-auto`}>
              {plans.map((plan) => {
                const pricing = PLAN_PRICING[plan.name] ?? { price: "Contact Us", priceNote: "", tagline: plan.description ?? "", available: false };
                const highlighted = plan.name === "free";

                // Convert entitlements to marketing strings
                const featureLines = plan.entitlements
                  .map((e) => entitlementToString(e.module_key, e.hard_limit))
                  .filter((s): s is string => s !== null);

                return (
                  <div
                    key={plan.id}
                    className="relative rounded-2xl p-8 flex flex-col transition-all duration-300"
                    style={
                      highlighted
                        ? {
                            background: "rgba(15,118,110,0.08)",
                            border: "1px solid rgba(15,118,110,0.4)",
                            boxShadow: "0 0 50px rgba(15,118,110,0.2)",
                          }
                        : pricing.available
                        ? {
                            background: "rgba(255,255,255,0.04)",
                            border: "1px solid rgba(255,255,255,0.1)",
                          }
                        : {
                            background: "rgba(255,255,255,0.02)",
                            border: "1px solid rgba(255,255,255,0.06)",
                          }
                    }
                  >
                    {/* Badges */}
                    {highlighted && (
                      <div
                        className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-xs font-bold text-white whitespace-nowrap"
                        style={{ background: "linear-gradient(135deg, #0F766E, #14B8A6)" }}
                      >
                        Available Now
                      </div>
                    )}
                    {!pricing.available && (
                      <div
                        className="absolute top-4 right-4 flex items-center gap-1.5 px-2.5 py-1 rounded-full"
                        style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}
                      >
                        <Clock className="w-3 h-3" style={{ color: "#64748B" }} aria-hidden="true" />
                        <span className="text-xs font-medium" style={{ color: "#64748B" }}>Coming Soon</span>
                      </div>
                    )}

                    {/* Header */}
                    <div className="mb-6">
                      <h3
                        className="text-lg font-bold mb-1"
                        style={{ color: pricing.available ? "#F1F5F9" : "#64748B" }}
                      >
                        {plan.display_name}
                      </h3>
                      <p className="text-sm" style={{ color: pricing.available ? "#94A3B8" : "#475569" }}>
                        {pricing.tagline}
                      </p>
                    </div>

                    {/* Price */}
                    <div className="mb-8">
                      <span
                        className="text-3xl font-bold"
                        style={{ color: pricing.available ? "#FFFFFF" : "#475569" }}
                      >
                        {pricing.price}
                      </span>
                      {pricing.priceNote && (
                        <span className="text-sm ml-2" style={{ color: "#64748B" }}>{pricing.priceNote}</span>
                      )}
                    </div>

                    {/* Features from DB entitlements */}
                    <ul className="space-y-3 mb-8 flex-1" role="list">
                      {featureLines.map((feat) => (
                        <li key={feat} className="flex items-start gap-2.5">
                          <Check
                            className="w-4 h-4 mt-0.5 shrink-0"
                            style={{ color: pricing.available ? "#14B8A6" : "#334155" }}
                            aria-hidden="true"
                          />
                          <span className="text-sm" style={{ color: pricing.available ? "#CBD5E1" : "#475569" }}>
                            {feat}
                          </span>
                        </li>
                      ))}
                    </ul>

                    {/* CTA */}
                    {pricing.available ? (
                      <a
                        href={`${APP_URL}/signup`}
                        className="block text-center px-6 py-3 rounded-xl font-semibold text-white text-sm transition-all duration-200"
                        style={{ background: "linear-gradient(135deg, #0F766E, #14B8A6)" }}
                        onMouseEnter={(e) => { e.currentTarget.style.boxShadow = "0 0 25px rgba(15,118,110,0.45)"; }}
                        onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "none"; }}
                      >
                        Get Started Free
                      </a>
                    ) : (
                      <a
                        href="#waitlist"
                        className="block text-center px-6 py-3 rounded-xl font-semibold text-sm transition-all duration-200"
                        style={{
                          background: "rgba(255,255,255,0.05)",
                          border: "1px solid rgba(255,255,255,0.08)",
                          color: "#475569",
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.color = "#94A3B8";
                          e.currentTarget.style.borderColor = "rgba(255,255,255,0.15)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.color = "#475569";
                          e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                        }}
                      >
                        Join Waitlist
                      </a>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <p className="text-center mt-10 text-sm" style={{ color: "#475569" }}>
            All plans include SSL, data privacy, and a secure hosting environment.{" "}
            <Link href="/contact" className="underline underline-offset-2" style={{ color: "#14B8A6" }}>
              Contact us
            </Link>{" "}
            with questions about pricing or custom arrangements.
          </p>
        </div>
      </section>

      {/* ─── WAITLIST ─────────────────────────────────────────────── */}
      {waitlistPlanNames.length > 0 && (
        <section
          id="waitlist"
          className="py-24 border-t"
          style={{ background: "#0E1826", borderColor: "rgba(255,255,255,0.07)" }}
          aria-labelledby="waitlist-heading"
        >
          <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#14B8A6" }}>
              Early Access
            </p>
            <h2 id="waitlist-heading" className="text-3xl font-bold text-white mb-4 tracking-tight">
              Join the waitlist for paid plans.
            </h2>
            <p className="text-base mb-8" style={{ color: "#94A3B8" }}>
              Be first in line when {waitlistPlanNames.join(" and ")} launch — with early-access pricing.
            </p>
            <WaitlistForm planNames={waitlistPlanNames} />
          </div>
        </section>
      )}

      {/* ─── FAQ ──────────────────────────────────────────────────── */}
      <section
        className="py-24 border-t"
        style={{ background: "#0B1320", borderColor: "rgba(255,255,255,0.06)" }}
        aria-labelledby="faq-heading"
      >
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 id="faq-heading" className="text-3xl font-bold text-white mb-10 tracking-tight text-center">
            Pricing FAQ
          </h2>
          <div className="space-y-3">
            {faqs.map((faq) => (
              <FAQItem key={faq.question} {...faq} />
            ))}
          </div>
          <p className="mt-10 text-center text-sm" style={{ color: "#475569" }}>
            Still have questions?{" "}
            <Link href="/contact" className="underline underline-offset-2" style={{ color: "#14B8A6" }}>
              Contact us
            </Link>
          </p>
        </div>
      </section>
    </>
  );
}
