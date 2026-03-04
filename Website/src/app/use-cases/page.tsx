import type { Metadata } from "next";
import { Building2, HeartPulse, Megaphone, Briefcase, Car, Store, ArrowRight, CheckCircle } from "lucide-react";
import CTASection from "@/components/CTASection";
import AnimateOnScroll from "@/components/AnimateOnScroll";
import FloatingOrb from "@/components/FloatingOrb";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Use Cases — LeadPilot Across Industries",
  description:
    "See how real estate agencies, clinics, marketing agencies, B2B services, automotive businesses, and SMBs use LeadPilot to capture more leads and close more deals.",
};

const useCases = [
  {
    icon: Building2, industry: "Real Estate Agencies", tagline: "Never let a buyer or seller wait again.",
    challenge: "High lead volume from portals and ads — but reps are stretched thin, and slow response means lost listings.",
    outcome: "Agencies using LeadPilot qualify and route every portal lead in under a minute, so the right agent calls back before the prospect contacts a competitor.",
    flow: ["Lead arrives from property portal or ad campaign", "AI asks budget, timeline, and property preference", "Scored lead is routed to the right agent by area or specialty", "Agent receives instant notification with full context", "Automated follow-up sends shortlist within the hour"],
    playbook: ["Build a qualification prompt around budget, location, and purchase timeline", "Route by suburb or listing type to matching agents", "Set a 5-minute response SLA alert for hot leads", "Use follow-up templates to send listings automatically"],
  },
  {
    icon: HeartPulse, industry: "Clinics & Health Practices", tagline: "Turn enquiries into booked appointments — faster.",
    challenge: "Clinic staff manually handle dozens of inbound calls and form submissions per day, with no triage system.",
    outcome: "LeadPilot captures enquiries 24/7, asks intake questions, and routes to the right clinician or coordinator — with zero manual sorting.",
    flow: ["Patient enquiry arrives via website form or chat", "AI gathers condition type, urgency, and preferred appointment time", "Lead is routed to the relevant clinician or booking coordinator", "Appointment confirmation sent automatically via email", "Follow-up reminder scheduled 24 hours before"],
    playbook: ["Capture enquiry type (new patient vs returning vs specialist referral)", "Route by specialty: GP, physio, dermatology, etc.", "Set urgent flag for keywords like 'acute', 'severe', 'emergency'", "Automate appointment confirmation messages"],
  },
  {
    icon: Megaphone, industry: "Marketing Agencies", tagline: "Qualify client leads as fast as you run campaigns.",
    challenge: "Agencies generate leads for clients — but their own new-business pipeline suffers from inconsistent qualification and slow internal follow-up.",
    outcome: "LeadPilot gives agencies a structured intake for new business: every prospect is qualified, scored, and handed to the right account manager.",
    flow: ["Prospect submits enquiry from website or ad", "AI qualifies by budget, service type, and project timeline", "High-intent leads routed to senior AMs; early-stage leads go to nurture", "CRM is updated with lead profile and score automatically", "Follow-up sequence kicks off within 5 minutes"],
    playbook: ["Build qualification around monthly budget and service type", "Route by service line: SEO, paid media, web, social", "Trigger nurture sequence for sub-threshold leads", "Set 'hot' threshold for leads with budget > target range"],
  },
  {
    icon: Briefcase, industry: "B2B Services", tagline: "Fill your sales pipeline without hiring more BDRs.",
    challenge: "B2B service firms get inbound from multiple channels but lack a repeatable qualification process. Good leads often go cold before a BDR reaches them.",
    outcome: "LeadPilot acts as an always-on BDR: qualifying intent, scoring fit, and booking discovery calls automatically.",
    flow: ["Inbound arrives from content, ads, or partner referral", "AI qualifies by company size, role, use case, and urgency", "Qualified leads offered a calendar link for a discovery call", "Unqualified leads enter a nurture track automatically", "Sales team receives leads with full qualification notes"],
    playbook: ["Qualify by ICP: company size, industry, role seniority", "Score by urgency signals: 'looking to start ASAP', 'in evaluation'", "Route enterprise leads to senior reps, SMB leads to junior team", "Auto-send case study relevant to their industry"],
  },
  {
    icon: Car, industry: "Automotive Services", tagline: "From test drive enquiry to showroom visit — automatically.",
    challenge: "Dealerships and service centres handle hundreds of enquiries per week. Manually matching buyer intent to available stock is slow and inconsistent.",
    outcome: "LeadPilot captures vehicle interest, qualifies budget and timeline, and routes to the right sales consultant — before the prospect visits a competitor.",
    flow: ["Enquiry arrives from website, ad, or OEM portal", "AI asks vehicle type, budget, and purchase timeline", "Lead routed to consultant with relevant stock expertise", "Consultant notified with buyer intent summary", "Follow-up with personalised brochure sent automatically"],
    playbook: ["Capture vehicle preference: new, used, EV, fleet", "Qualify by finance readiness and purchase window", "Route by brand expertise or current stock availability", "Auto-send relevant vehicle shortlist within minutes"],
  },
  {
    icon: Store, industry: "SMB Services & Retail", tagline: "Handle enquiry volume without adding staff.",
    challenge: "Small and medium businesses are overwhelmed by enquiry volume across email, social, and web — with no system to prioritise or respond consistently.",
    outcome: "LeadPilot gives SMBs an AI-powered front desk that qualifies, routes, and follows up — so the owner can focus on delivery, not admin.",
    flow: ["Customer enquiry arrives from any channel", "AI qualifies by service interest, location, and urgency", "Lead is tagged and routed to the right staff member", "Response sent automatically within minutes", "Owner notified daily with a digest of new leads"],
    playbook: ["Build a simple qualification prompt matching your service menu", "Route by location if you serve multiple areas", "Set priority flag for high-value service enquiries", "Use templates for quotes, availability confirmations, and follow-ups"],
  },
];

export default function UseCasesPage() {
  return (
    <>
      {/* ─── HERO ─────────────────────────────────────────────────── */}
      <section className="relative py-28 overflow-hidden" style={{ background: "#0B1320" }} aria-labelledby="usecases-heading">
        <div className="absolute inset-0 mk-grid opacity-40" aria-hidden="true" />
        <div className="absolute inset-0 pointer-events-none" aria-hidden="true"
          style={{ background: "radial-gradient(ellipse 60% 50% at 50% 0%, rgba(15,118,110,0.25) 0%, transparent 70%)" }}
        />
        <FloatingOrb size={400} color="mixed" top="60%" right="10%" opacity={0.10} blur={90} />

        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <AnimateOnScroll animation="fadeIn">
            <p className="text-xs font-bold uppercase tracking-widest mb-4" style={{ color: "#14B8A6" }}>Use Cases</p>
          </AnimateOnScroll>
          <AnimateOnScroll animation="fadeUp" delay={80}>
            <h1 id="usecases-heading" className="text-4xl sm:text-5xl md:text-6xl font-bold text-white mb-6 tracking-tight">
              Built for every
              <br />
              <span className="mk-gradient-text">revenue-driven team.</span>
            </h1>
          </AnimateOnScroll>
          <AnimateOnScroll animation="fadeUp" delay={160}>
            <p className="text-lg max-w-2xl mx-auto leading-relaxed" style={{ color: "rgba(148,163,184,0.9)" }}>
              LeadPilot adapts to your industry, your team structure, and your sales motion.
              Here&apos;s how different businesses use it to close more revenue with less effort.
            </p>
          </AnimateOnScroll>
        </div>
      </section>

      {/* ─── INDUSTRY NAV ─────────────────────────────────────────── */}
      <section
        className="py-6 sticky top-16 z-40"
        style={{ background: "rgba(11,19,32,0.95)", backdropFilter: "blur(16px)", borderBottom: "1px solid rgba(255,255,255,0.07)" }}
        aria-label="Industry navigation"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center gap-2 justify-center">
            {useCases.map(({ icon: Icon, industry }) => {
              const anchor = industry.toLowerCase().replace(/[^a-z0-9]+/g, "-");
              return (
                <a key={industry} href={`#${anchor}`} className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium mk-category-link">
                  <Icon className="w-3.5 h-3.5" aria-hidden="true" />
                  {industry}
                </a>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── USE CASE SECTIONS ────────────────────────────────────── */}
      {useCases.map((uc, i) => {
        const Icon = uc.icon;
        const anchor = uc.industry.toLowerCase().replace(/[^a-z0-9]+/g, "-");
        const dark = i % 2 === 1;

        return (
          <section
            key={uc.industry}
            id={anchor}
            className="py-24 border-t"
            style={{ background: dark ? "#0E1826" : "#F8FAFC", borderColor: dark ? "rgba(255,255,255,0.06)" : "#E2E8F0" }}
            aria-labelledby={`${anchor}-heading`}
          >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-14">
                {/* Left: context */}
                <AnimateOnScroll animation="fadeLeft">
                  <div>
                    <div className="flex items-center gap-3 mb-5">
                      <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                        style={{ background: dark ? "rgba(15,118,110,0.2)" : "rgba(15,118,110,0.08)", border: dark ? "1px solid rgba(20,184,166,0.3)" : "1px solid rgba(15,118,110,0.15)" }}
                      >
                        <Icon className="w-5 h-5" style={{ color: dark ? "#14B8A6" : "#0F766E" }} aria-hidden="true" />
                      </div>
                      <p className="text-xs font-bold uppercase tracking-widest" style={{ color: dark ? "#14B8A6" : "#0F766E" }}>{uc.industry}</p>
                    </div>

                    <h2 id={`${anchor}-heading`} className="text-2xl sm:text-3xl font-bold mb-3 tracking-tight" style={{ color: dark ? "#F1F5F9" : "#0F172A" }}>
                      {uc.tagline}
                    </h2>

                    <p className="text-sm mb-5 leading-relaxed" style={{ color: dark ? "#94A3B8" : "#64748B" }}>
                      <strong style={{ color: dark ? "#CBD5E1" : "#334155" }}>The challenge:</strong>{" "}{uc.challenge}
                    </p>

                    <div className="rounded-xl p-5 mb-8"
                      style={{ background: dark ? "rgba(15,118,110,0.08)" : "rgba(15,118,110,0.06)", border: dark ? "1px solid rgba(20,184,166,0.2)" : "1px solid rgba(15,118,110,0.15)" }}
                    >
                      <p className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: dark ? "#14B8A6" : "#0F766E" }}>The Outcome</p>
                      <p className="text-sm leading-relaxed" style={{ color: dark ? "#CBD5E1" : "#334155" }}>{uc.outcome}</p>
                    </div>

                    <div>
                      <p className="text-xs font-bold uppercase tracking-widest mb-4" style={{ color: dark ? "#475569" : "#94A3B8" }}>Recommended Playbook</p>
                      <ul className="space-y-2.5">
                        {uc.playbook.map((item) => (
                          <li key={item} className="flex items-start gap-2.5">
                            <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" style={{ color: dark ? "#14B8A6" : "#0F766E" }} aria-hidden="true" />
                            <span className="text-sm" style={{ color: dark ? "#94A3B8" : "#64748B" }}>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </AnimateOnScroll>

                {/* Right: flow */}
                <AnimateOnScroll animation="fadeRight" delay={120}>
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest mb-5" style={{ color: dark ? "#475569" : "#94A3B8" }}>Typical Flow</p>
                    <div className="space-y-3">
                      {uc.flow.map((step, si) => (
                        <div key={step} className="flex items-start gap-4">
                          <div className="flex flex-col items-center">
                            <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                              style={{ background: dark ? "rgba(15,118,110,0.25)" : "rgba(15,118,110,0.1)", color: dark ? "#14B8A6" : "#0F766E", border: dark ? "1px solid rgba(20,184,166,0.25)" : "1px solid rgba(15,118,110,0.2)" }}
                            >{si + 1}</div>
                            {si < uc.flow.length - 1 && (
                              <div className="w-px flex-1 mt-1 mb-1" style={{ background: dark ? "rgba(255,255,255,0.06)" : "#E2E8F0", minHeight: "16px" }} aria-hidden="true" />
                            )}
                          </div>
                          <div className="rounded-xl p-4 flex-1"
                            style={{ background: dark ? "rgba(255,255,255,0.03)" : "#FFFFFF", border: dark ? "1px solid rgba(255,255,255,0.06)" : "1px solid #E2E8F0" }}
                          >
                            <p className="text-sm leading-relaxed" style={{ color: dark ? "#CBD5E1" : "#334155" }}>{step}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </AnimateOnScroll>
              </div>
            </div>
          </section>
        );
      })}

      {/* ─── BOTTOM LINKS ─────────────────────────────────────────── */}
      <section className="py-16" style={{ background: "#F8FAFC", borderTop: "1px solid #E2E8F0" }} aria-label="Explore more">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <AnimateOnScroll animation="fadeUp">
            <h2 className="text-2xl font-bold mb-4" style={{ color: "#0F172A" }}>Don&apos;t see your industry?</h2>
            <p className="text-base mb-8" style={{ color: "#64748B" }}>
              LeadPilot adapts to any business that handles inbound leads. Get in touch and we&apos;ll show you how it maps to your workflow.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/contact" className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl font-semibold text-sm mk-btn-primary">
                Talk to us
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </Link>
              <Link href="/features" className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl font-semibold text-sm mk-btn-ghost-light">
                View all features
              </Link>
            </div>
          </AnimateOnScroll>
        </div>
      </section>

      {/* ─── CTA ──────────────────────────────────────────────────── */}
      <CTASection
        headline="Ready to try it in your business?"
        subheadline="Start with the Free plan — no credit card, no commitment."
        primaryLabel="Start for Free"
        primaryHref="/app/signup"
        secondaryLabel="See Plans"
        secondaryHref="/plans"
      />
    </>
  );
}
