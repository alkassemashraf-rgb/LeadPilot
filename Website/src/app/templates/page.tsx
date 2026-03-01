import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Copy, Sliders, Rocket } from "lucide-react";
import { getPublicTemplates, getTemplateCategories } from "@/lib/api";
import CTASection from "@/components/CTASection";
import CategoryFilter from "./CategoryFilter";
import TemplateCard from "./TemplateCard";

export const metadata: Metadata = {
  title: "Templates — Ready-Made Automation Flows",
  description:
    "Browse LeadPilot's library of pre-built automation templates for WhatsApp, Instagram, Messenger, and more. Clone and customise in minutes.",
};

const howItWorks = [
  {
    Icon: Copy,
    step: "01",
    title: "Clone",
    description:
      "Pick a template that matches your use case. One click copies the entire flow — nodes, logic, and AI prompts — into your workspace.",
  },
  {
    Icon: Sliders,
    step: "02",
    title: "Customise",
    description:
      "Swap in your brand voice, tweak qualification questions, and wire up your integrations. The visual builder makes it drag-and-drop simple.",
  },
  {
    Icon: Rocket,
    step: "03",
    title: "Launch",
    description:
      "Publish your flow and start capturing leads immediately. Monitor performance in real time and iterate whenever you need.",
  },
];

export default async function TemplatesPage() {
  const [templates, categories] = await Promise.all([
    getPublicTemplates(),
    getTemplateCategories(),
  ]);

  const featuredTemplates = templates.filter((t) => t.is_featured).slice(0, 3);
  const totalClones = templates.reduce((sum, t) => sum + t.clone_count, 0);

  return (
    <>
      {/* ─── HERO ─────────────────────────────────────────────────── */}
      <section
        className="relative py-28 overflow-hidden"
        style={{ background: "#0B1320" }}
        aria-labelledby="templates-hero-heading"
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
          <div
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-8"
            style={{
              background: "rgba(15,118,110,0.15)",
              border: "1px solid rgba(20,184,166,0.3)",
            }}
          >
            <span
              className="w-2 h-2 rounded-full animate-pulse-glow"
              style={{ background: "#14B8A6" }}
              aria-hidden="true"
            />
            <span
              className="text-xs font-semibold tracking-wider"
              style={{ color: "#14B8A6" }}
            >
              TEMPLATE CATALOG
            </span>
          </div>
          <h1
            id="templates-hero-heading"
            className="text-4xl sm:text-5xl md:text-6xl font-bold text-white mb-6 tracking-tight"
          >
            Ready-made automation flows.
            <br />
            <span className="gradient-text">Clone. Customise. Launch.</span>
          </h1>
          <p
            className="text-lg max-w-2xl mx-auto leading-relaxed"
            style={{ color: "rgba(148,163,184,0.9)" }}
          >
            Pre-built workflows for lead qualification, appointment booking, support intake,
            and more. Each template includes AI-powered nodes that you can tailor to your business.
          </p>
        </div>
      </section>

      {/* ─── STATS STRIP ─────────────────────────────────────────── */}
      <section
        className="py-10 border-y"
        style={{ background: "#0E1826", borderColor: "rgba(255,255,255,0.06)" }}
        aria-label="Template catalog stats"
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-3 gap-8 text-center">
            <div>
              <p className="text-2xl sm:text-3xl font-bold text-white">
                {templates.length}
              </p>
              <p
                className="text-xs font-medium uppercase tracking-wider mt-1"
                style={{ color: "#475569" }}
              >
                Templates
              </p>
            </div>
            <div>
              <p className="text-2xl sm:text-3xl font-bold text-white">
                {categories.length}
              </p>
              <p
                className="text-xs font-medium uppercase tracking-wider mt-1"
                style={{ color: "#475569" }}
              >
                Categories
              </p>
            </div>
            <div>
              <p className="text-2xl sm:text-3xl font-bold text-white">
                {totalClones > 0 ? totalClones.toLocaleString() : "—"}
              </p>
              <p
                className="text-xs font-medium uppercase tracking-wider mt-1"
                style={{ color: "#475569" }}
              >
                Total Clones
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─── FEATURED TEMPLATES ───────────────────────────────────── */}
      {featuredTemplates.length > 0 && (
        <section
          className="py-24 relative overflow-hidden"
          style={{ background: "#0B1320" }}
          aria-labelledby="featured-heading"
        >
          <div
            className="absolute inset-0 pointer-events-none"
            aria-hidden="true"
            style={{
              background:
                "radial-gradient(ellipse 50% 60% at 50% 100%, rgba(15,118,110,0.15) 0%, transparent 70%)",
            }}
          />
          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-14">
              <p
                className="text-xs font-bold uppercase tracking-widest mb-3"
                style={{ color: "#14B8A6" }}
              >
                Staff Picks
              </p>
              <h2
                id="featured-heading"
                className="text-3xl sm:text-4xl font-bold text-white tracking-tight"
              >
                Featured templates
              </h2>
              <p
                className="mt-4 text-base max-w-xl mx-auto"
                style={{ color: "#64748B" }}
              >
                Our most popular and battle-tested automation flows, ready to deploy.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {featuredTemplates.map((t) => (
                <TemplateCard key={t.id} template={t} featured />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ─── HOW TEMPLATES WORK ──────────────────────────────────── */}
      <section
        className="py-24"
        style={{ background: "#F8FAFC" }}
        aria-labelledby="how-templates-work"
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <p
              className="text-xs font-bold uppercase tracking-widest mb-3"
              style={{ color: "#0F766E" }}
            >
              How It Works
            </p>
            <h2
              id="how-templates-work"
              className="text-3xl sm:text-4xl font-bold tracking-tight"
              style={{ color: "#0F172A" }}
            >
              From template to live flow in three steps
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {howItWorks.map(({ Icon, step, title, description }) => (
              <div key={step} className="text-center">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-5"
                  style={{
                    background: "rgba(15,118,110,0.08)",
                    border: "1px solid rgba(15,118,110,0.15)",
                  }}
                >
                  <Icon
                    className="w-5 h-5"
                    style={{ color: "#0F766E" }}
                    aria-hidden="true"
                  />
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
                <h3
                  className="font-semibold text-base mb-2"
                  style={{ color: "#1E293B" }}
                >
                  {title}
                </h3>
                <p
                  className="text-sm leading-relaxed"
                  style={{ color: "#64748B" }}
                >
                  {description}
                </p>
              </div>
            ))}
          </div>

          <div className="text-center mt-12">
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 text-sm font-semibold text-link-primary"
            >
              Need help getting started? Contact us
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>

      {/* ─── ALL TEMPLATES (filterable) ───────────────────────────── */}
      <section
        className="py-24 relative overflow-hidden"
        style={{ background: "#0B1320" }}
        aria-labelledby="all-templates-heading"
      >
        <div
          className="absolute inset-0 cockpit-grid opacity-20"
          aria-hidden="true"
        />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10">
            <p
              className="text-xs font-bold uppercase tracking-widest mb-3"
              style={{ color: "#14B8A6" }}
            >
              Browse All
            </p>
            <h2
              id="all-templates-heading"
              className="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-2"
            >
              Explore the full catalog
            </h2>
            <p className="text-sm" style={{ color: "#64748B" }}>
              {templates.length} templates across {categories.length} categories
            </p>
          </div>

          <CategoryFilter templates={templates} categories={categories} />
        </div>
      </section>

      {/* ─── CTA ──────────────────────────────────────────────────── */}
      <CTASection
        headline="Ready to automate your pipeline?"
        subheadline="Clone a template, customise it for your business, and go live in minutes."
        primaryLabel="Book a Demo"
        primaryHref="/contact"
        secondaryLabel="Sign Up Free"
      />
    </>
  );
}
