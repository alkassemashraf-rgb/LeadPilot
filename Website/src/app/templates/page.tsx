import type { Metadata } from "next";
import { getPublicTemplates, getTemplateCategories } from "@/lib/api";
import CTASection from "@/components/CTASection";
import CategoryFilter from "./CategoryFilter";
import TemplateCard from "./TemplateCard";

export const metadata: Metadata = {
  title: "Templates — Ready-Made Automation Flows",
  description:
    "Browse LeadPilot's library of pre-built automation templates for WhatsApp, Instagram, Messenger, and more. Clone and customise in minutes.",
};

export default async function TemplatesPage() {
  const [templates, categories] = await Promise.all([
    getPublicTemplates(),
    getTemplateCategories(),
  ]);

  const featuredTemplates = templates.filter((t) => t.is_featured);

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
          <p
            className="text-xs font-bold uppercase tracking-widest mb-4"
            style={{ color: "#14B8A6" }}
          >
            Template Catalog
          </p>
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

      {/* ─── FEATURED TEMPLATES ───────────────────────────────────── */}
      {featuredTemplates.length > 0 && (
        <section
          className="py-16 border-b"
          style={{ background: "#0E1826", borderColor: "rgba(255,255,255,0.06)" }}
          aria-labelledby="featured-heading"
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2
              id="featured-heading"
              className="text-xs font-bold uppercase tracking-widest mb-8 text-center"
              style={{ color: "#14B8A6" }}
            >
              Featured Templates
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
              {featuredTemplates.map((t) => (
                <TemplateCard key={t.id} template={t} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ─── ALL TEMPLATES (filterable) ───────────────────────────── */}
      <section
        className="py-24"
        style={{ background: "#0B1320" }}
        aria-labelledby="all-templates-heading"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10">
            <h2
              id="all-templates-heading"
              className="text-2xl font-bold text-white tracking-tight mb-2"
            >
              All Templates
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
        secondaryLabel="Start Free"
        secondaryHref="/plans"
      />
    </>
  );
}
