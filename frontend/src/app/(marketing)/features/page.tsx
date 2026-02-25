import type { Metadata } from "next";
import { Brain, Globe, GitMerge, Inbox, BarChart3, BookOpen, Shield, Database, FileText, Zap, Bell, Settings } from "lucide-react";
import FeatureCard from "@/components/marketing/FeatureCard";
import CTASection from "@/components/marketing/CTASection";
import AnimateOnScroll from "@/components/marketing/AnimateOnScroll";
import FloatingOrb from "@/components/marketing/FloatingOrb";

export const metadata: Metadata = {
  title: "Features — Everything LeadPilot Does",
  description:
    "AI qualification & scoring, multi-channel capture, smart routing, CRM sync, team inbox, analytics, playbooks, and more. The full LeadPilot feature set.",
};

const features = [
  { icon: Brain, benefit: "Qualify at scale", title: "AI Qualification & Scoring", description: "Custom AI prompts engage every lead the moment they arrive. Scores are assigned based on intent, fit, and urgency — so your reps only work leads worth their time." },
  { icon: Globe, benefit: "Zero leakage", title: "Multi-Channel Lead Capture", description: "Embed capture forms, integrate your existing chat widget, accept webhook payloads, and connect partner referral links — everything flows into one structured pipeline." },
  { icon: Database, benefit: "Stay connected", title: "CRM Sync & Integrations", description: "Push qualified leads directly to your CRM of choice. Map fields, set sync rules, and keep your sales stack in perfect alignment without manual exports." },
  { icon: GitMerge, benefit: "Right rep, right time", title: "Smart Routing Rules", description: "Route by territory, vertical, product line, rep availability, or any custom attribute. Rules compose like building blocks — no code required." },
  { icon: Inbox, benefit: "Stay in the loop", title: "Team Inbox & Human Handover", description: "All conversations flow into a shared team inbox. Reps can pick up context instantly, send messages, and mark leads without switching tools." },
  { icon: BarChart3, benefit: "Measure what matters", title: "Analytics & Conversion Tracking", description: "Track lead volume, qualification rate, response time, conversion by channel and rep, and pipeline velocity — all in real time from a single dashboard." },
  { icon: BookOpen, benefit: "Start fast", title: "Playbooks & Templates", description: "Pre-built qualification playbooks for common industries and use cases. Start with a template, customise the prompts, and go live in minutes." },
  { icon: Shield, benefit: "Stay in control", title: "Role-Based Access Control", description: "Assign owner, manager, and viewer roles. Control who can see which leads, edit routing rules, or access reporting — down to workspace level." },
  { icon: FileText, benefit: "Full transparency", title: "Audit Trail & Activity Log", description: "Every action on every lead is logged: capture, score change, routing event, message sent, rep assigned. Immutable, exportable, always available." },
  { icon: Database, benefit: "Richer profiles", title: "Custom Fields & Lead Enrichment", description: "Extend the lead model with custom fields that match your business. Enrich profiles with company data, source metadata, and conversation history automatically." },
  { icon: Bell, benefit: "Never miss a beat", title: "Real-Time Notifications", description: "Email and in-app alerts the moment a lead is assigned, qualified, or hits a threshold. Configure notification rules per rep, per team, or per lead stage." },
  { icon: Settings, benefit: "Your rules", title: "Workflow Automation", description: "Build trigger-based workflows that act on lead status changes, score thresholds, or time-based events. Automate follow-ups, escalations, and re-routing without code." },
];

const categories = [
  { label: "Capture & Intake", icon: Zap, features: ["Multi-Channel Lead Capture", "Custom Fields & Lead Enrichment"] },
  { label: "Intelligence", icon: Brain, features: ["AI Qualification & Scoring", "Playbooks & Templates", "Workflow Automation"] },
  { label: "Operations", icon: GitMerge, features: ["Smart Routing Rules", "Team Inbox & Human Handover", "Real-Time Notifications"] },
  { label: "Visibility", icon: BarChart3, features: ["Analytics & Conversion Tracking", "Audit Trail & Activity Log"] },
  { label: "Platform", icon: Shield, features: ["CRM Sync & Integrations", "Role-Based Access Control"] },
];

export default function FeaturesPage() {
  return (
    <>
      {/* ─── HERO ─────────────────────────────────────────────────── */}
      <section className="relative py-28 overflow-hidden" style={{ background: "#0B1320" }} aria-labelledby="features-hero-heading">
        <div className="absolute inset-0 mk-grid opacity-40" aria-hidden="true" />
        <div className="absolute inset-0 pointer-events-none" aria-hidden="true"
          style={{ background: "radial-gradient(ellipse 60% 50% at 50% 0%, rgba(15,118,110,0.25) 0%, transparent 70%)" }}
        />
        <FloatingOrb size={350} color="secondary" top="70%" right="10%" opacity={0.10} blur={80} />

        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <AnimateOnScroll animation="fadeIn">
            <p className="text-xs font-bold uppercase tracking-widest mb-4" style={{ color: "#14B8A6" }}>Platform Features</p>
          </AnimateOnScroll>
          <AnimateOnScroll animation="fadeUp" delay={80}>
            <h1 id="features-hero-heading" className="text-4xl sm:text-5xl md:text-6xl font-bold text-white mb-6 tracking-tight">
              The full feature set.
              <br />
              <span className="mk-gradient-text">Nothing missing.</span>
            </h1>
          </AnimateOnScroll>
          <AnimateOnScroll animation="fadeUp" delay={160}>
            <p className="text-lg max-w-2xl mx-auto leading-relaxed" style={{ color: "rgba(148,163,184,0.9)" }}>
              Every feature in LeadPilot is built with one goal: turn inbound interest into
              qualified pipeline with less effort from your team.
            </p>
          </AnimateOnScroll>
        </div>
      </section>

      {/* ─── CATEGORY NAV ─────────────────────────────────────────── */}
      <section
        className="py-8 sticky top-16 z-40"
        style={{ background: "rgba(11,19,32,0.95)", backdropFilter: "blur(16px)", borderBottom: "1px solid rgba(255,255,255,0.07)" }}
        aria-label="Feature categories"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center gap-2 justify-center">
            {categories.map(({ label, icon: Icon }) => (
              <a key={label} href={`#${label.toLowerCase().replace(/ & /g, "-").replace(/ /g, "-")}`}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium mk-category-link"
              >
                <Icon className="w-3.5 h-3.5" aria-hidden="true" />
                {label}
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FULL FEATURES GRID ───────────────────────────────────── */}
      <section className="py-24" style={{ background: "#0B1320" }} aria-labelledby="features-grid-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 id="features-grid-heading" className="sr-only">All features</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((feat, i) => (
              <AnimateOnScroll key={feat.title} animation="fadeUp" delay={i * 50}>
                <FeatureCard {...feat} dark />
              </AnimateOnScroll>
            ))}
          </div>
        </div>
      </section>

      {/* ─── CATEGORIES DEEP DIVE ─────────────────────────────────── */}
      {categories.map(({ label, icon: Icon, features: catFeats }) => {
        const anchorId = label.toLowerCase().replace(/ & /g, "-").replace(/ /g, "-");
        return (
          <section key={label} id={anchorId} className="py-20 border-t" style={{ background: "#F8FAFC", borderColor: "#E2E8F0" }} aria-labelledby={`${anchorId}-heading`}>
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <AnimateOnScroll animation="fadeLeft">
                <div className="flex items-center gap-3 mb-10">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: "rgba(15,118,110,0.1)", border: "1px solid rgba(15,118,110,0.2)" }}>
                    <Icon className="w-5 h-5" style={{ color: "#0F766E" }} aria-hidden="true" />
                  </div>
                  <h2 id={`${anchorId}-heading`} className="text-xl font-bold tracking-tight" style={{ color: "#0F172A" }}>{label}</h2>
                </div>
              </AnimateOnScroll>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                {features.filter((f) => catFeats.includes(f.title)).map((feat, i) => (
                  <AnimateOnScroll key={feat.title} animation="fadeUp" delay={i * 80}>
                    <FeatureCard {...feat} />
                  </AnimateOnScroll>
                ))}
              </div>
            </div>
          </section>
        );
      })}

      {/* ─── CTA ──────────────────────────────────────────────────── */}
      <CTASection
        headline="Ready to put these features to work?"
        subheadline="Start with the Free plan today. No credit card. No setup fees."
        primaryLabel="Start for Free"
        primaryHref="/signup"
        secondaryLabel="See Plans"
        secondaryHref="/plans"
      />
    </>
  );
}
