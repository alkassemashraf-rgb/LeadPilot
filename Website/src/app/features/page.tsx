import type { Metadata } from "next";
import { getModules } from "@/lib/api";
import { MODULE_MARKETING_MAP, FEATURE_CATEGORIES } from "@/lib/moduleMap";
import FeatureCard from "@/components/FeatureCard";
import CTASection from "@/components/CTASection";
import AnimateOnScroll from "@/components/AnimateOnScroll";
import * as Icons from "lucide-react";
import { type LucideIcon } from "lucide-react";

export const metadata: Metadata = {
  title: "Features — Everything LeadPilot Does",
  description:
    "AI qualification & scoring, multi-channel capture, smart routing, CRM sync, team inbox, analytics, playbooks, and more. The full LeadPilot feature set.",
};

function getIcon(iconName: string): LucideIcon {
  if (iconName in Icons) return (Icons as unknown as Record<string, LucideIcon>)[iconName];
  return Icons.Zap;
}

export default async function FeaturesPage() {
  const modules = await getModules();

  // Map DB modules to marketing features
  const allFeatures = modules
    .filter((m) => MODULE_MARKETING_MAP[m.key])
    .map((m) => ({
      ...MODULE_MARKETING_MAP[m.key],
      isEnabled: m.is_enabled,
      moduleKey: m.key,
    }));

  // Categories with their features
  const categoriesWithFeatures = FEATURE_CATEGORIES.map((cat) => ({
    ...cat,
    features: allFeatures.filter((f) => f.category === cat.key),
  })).filter((cat) => cat.features.length > 0);

  return (
    <>
      {/* ─── HERO ─────────────────────────────────────────────────── */}
      <section
        className="relative py-28 overflow-hidden"
        style={{ background: "#0B1320" }}
        aria-labelledby="features-hero-heading"
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
          <AnimateOnScroll animation="fadeIn">
            <p
              className="text-xs font-bold uppercase tracking-widest mb-4"
              style={{ color: "#14B8A6" }}
            >
              Platform Features
            </p>
          </AnimateOnScroll>
          <AnimateOnScroll animation="fadeUp" delay={80}>
            <h1
              id="features-hero-heading"
              className="text-4xl sm:text-5xl md:text-6xl font-bold text-white mb-6 tracking-tight"
            >
              The full feature set.
              <br />
              <span className="gradient-text">Nothing missing.</span>
            </h1>
          </AnimateOnScroll>
          <AnimateOnScroll animation="fadeUp" delay={160}>
            <p
              className="text-lg max-w-2xl mx-auto leading-relaxed"
              style={{ color: "rgba(148,163,184,0.9)" }}
            >
              Every feature in LeadPilot is built with one goal: turn inbound interest into
              qualified pipeline with less effort from your team.
            </p>
          </AnimateOnScroll>
        </div>
      </section>

      {/* ─── CATEGORY NAV ─────────────────────────────────────────── */}
      <section
        className="py-8 sticky top-16 z-40"
        style={{
          background: "rgba(11,19,32,0.95)",
          backdropFilter: "blur(16px)",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
        }}
        aria-label="Feature categories"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center gap-2 justify-center">
            {categoriesWithFeatures.map(({ label, iconName }) => {
              const CatIcon = getIcon(iconName);
              const anchorId = label.toLowerCase().replace(/ & /g, "-").replace(/ /g, "-");
              return (
                <a
                  key={label}
                  href={`#${anchorId}`}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium category-link"
                >
                  <CatIcon className="w-3.5 h-3.5" aria-hidden="true" />
                  {label}
                </a>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── FULL FEATURES GRID ───────────────────────────────────── */}
      <section
        className="py-24"
        style={{ background: "#0B1320" }}
        aria-labelledby="features-grid-heading"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 id="features-grid-heading" className="sr-only">All features</h2>
          <AnimateOnScroll animation="fadeUp">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {allFeatures.map((feat) => (
                <FeatureCard
                  key={feat.moduleKey}
                  iconName={feat.iconName}
                  benefit={feat.benefit}
                  title={feat.marketingTitle}
                  description={feat.description}
                  dark
                  comingSoon={!feat.isEnabled}
                />
              ))}
            </div>
          </AnimateOnScroll>
        </div>
      </section>

      {/* ─── CATEGORIES DEEP DIVE ─────────────────────────────────── */}
      {categoriesWithFeatures.map(({ label, iconName, features: catFeats }) => {
        const anchorId = label.toLowerCase().replace(/ & /g, "-").replace(/ /g, "-");
        const CatIcon = getIcon(iconName);
        return (
          <section
            key={label}
            id={anchorId}
            className="py-20 border-t"
            style={{ background: "#F8FAFC", borderColor: "#E2E8F0" }}
            aria-labelledby={`${anchorId}-heading`}
          >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <AnimateOnScroll animation="fadeRight">
                <div className="flex items-center gap-3 mb-10">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center"
                    style={{ background: "rgba(15,118,110,0.1)", border: "1px solid rgba(15,118,110,0.2)" }}
                  >
                    <CatIcon className="w-5 h-5" style={{ color: "#0F766E" }} aria-hidden="true" />
                  </div>
                  <h2
                    id={`${anchorId}-heading`}
                    className="text-xl font-bold tracking-tight"
                    style={{ color: "#0F172A" }}
                  >
                    {label}
                  </h2>
                </div>
              </AnimateOnScroll>
              <AnimateOnScroll animation="fadeUp" delay={80}>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                  {catFeats.map((feat) => (
                    <FeatureCard
                      key={feat.moduleKey}
                      iconName={feat.iconName}
                      benefit={feat.benefit}
                      title={feat.marketingTitle}
                      description={feat.description}
                      comingSoon={!feat.isEnabled}
                    />
                  ))}
                </div>
              </AnimateOnScroll>
            </div>
          </section>
        );
      })}

      {/* ─── CTA ──────────────────────────────────────────────────── */}
      <CTASection
        headline="Ready to put these features to work?"
        subheadline="Start with the Free plan today. No credit card. No setup fees."
        primaryLabel="Book a Demo"
        primaryHref="/contact"
        secondaryLabel="Sign Up Free"
      />
    </>
  );
}
