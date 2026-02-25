import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Globe, Brain, GitMerge, Bell, BarChart3, Users, CheckCircle } from "lucide-react";
import CTASection from "@/components/marketing/CTASection";
import AnimateOnScroll from "@/components/marketing/AnimateOnScroll";
import FloatingOrb from "@/components/marketing/FloatingOrb";

export const metadata: Metadata = {
  title: "Product — How LeadPilot Works",
  description:
    "Discover how LeadPilot's AI-native platform transforms raw inbound traffic into qualified, routed pipeline. Capture → Qualify → Route → Follow Up → Report.",
};

const stages = [
  {
    icon: Globe, step: "01", title: "Capture", headline: "Every lead. Every channel. Zero leakage.",
    body: "LeadPilot connects to your web forms, chat widgets, inbound email, and partner integrations. Every lead enters a single, structured pipeline — no spreadsheets, no manual imports.",
    bullets: ["Form-native capture with no-code embed", "Chat widget integration", "Webhook-based capture from any source", "Deduplication on arrival"],
  },
  {
    icon: Brain, step: "02", title: "Qualify", headline: "AI that asks the right questions and scores every lead.",
    body: "LeadPilot's AI qualification engine runs custom prompts against every inbound lead. It scores intent, fit, and urgency — then flags or filters based on your criteria, in real time.",
    bullets: ["Custom AI qualification prompts", "Lead scoring by fit, intent, and urgency", "Automatic disqualification of junk leads", "Human-in-the-loop override at any point"],
  },
  {
    icon: GitMerge, step: "03", title: "Route", headline: "Right rep. Right moment. Every time.",
    body: "Smart routing rules dispatch qualified leads based on territory, product line, team capacity, or any logic you define. No more round-robin confusion or leads falling on a silent inbox.",
    bullets: ["Rules-based and AI-assisted routing", "Territory and specialty routing", "Load balancing across team members", "Fallback routing for unavailable reps"],
  },
  {
    icon: Bell, step: "04", title: "Follow Up", headline: "Keep prospects warm between touchpoints.",
    body: "Automated follow-up sequences ensure no lead goes cold. Send timely, context-aware messages that keep prospects engaged while your team focuses on high-value conversations.",
    bullets: ["Automated email follow-up sequences", "Configurable delay and trigger rules", "Template library for common scenarios", "AI-drafted personalised messages"],
  },
  {
    icon: BarChart3, step: "05", title: "Report", headline: "See exactly where revenue is being left behind.",
    body: "Real-time dashboards give you full-funnel visibility: lead volume, qualification rate, response time, conversion by rep, and pipeline velocity — all in one place.",
    bullets: ["Lead-to-close conversion tracking", "Response time and SLA monitoring", "Rep and team performance views", "Exportable reports for leadership"],
  },
];

export default function ProductPage() {
  return (
    <>
      {/* ─── HERO ─────────────────────────────────────────────────── */}
      <section className="relative py-28 overflow-hidden" style={{ background: "#0B1320" }} aria-labelledby="product-heading">
        <div className="absolute inset-0 mk-grid opacity-40" aria-hidden="true" />
        <div className="absolute inset-0 pointer-events-none" aria-hidden="true"
          style={{ background: "radial-gradient(ellipse 60% 50% at 50% 0%, rgba(15,118,110,0.25) 0%, transparent 70%)" }}
        />
        <FloatingOrb size={400} color="primary" top="60%" left="15%" opacity={0.10} blur={90} />

        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <AnimateOnScroll animation="fadeIn">
            <p className="text-xs font-bold uppercase tracking-widest mb-4" style={{ color: "#14B8A6" }}>The Product</p>
          </AnimateOnScroll>
          <AnimateOnScroll animation="fadeUp" delay={80}>
            <h1 id="product-heading" className="text-4xl sm:text-5xl md:text-6xl font-bold text-white mb-6 tracking-tight">
              The AI cockpit for
              <br />
              <span className="mk-gradient-text">your entire lead pipeline.</span>
            </h1>
          </AnimateOnScroll>
          <AnimateOnScroll animation="fadeUp" delay={160}>
            <p className="text-lg max-w-2xl mx-auto leading-relaxed" style={{ color: "rgba(148,163,184,0.9)" }}>
              LeadPilot is not another CRM add-on or chatbot. It&apos;s a purpose-built
              AI layer that handles the full lead lifecycle — from the moment a prospect
              fills out a form to the second your rep picks up the phone.
            </p>
          </AnimateOnScroll>
        </div>
      </section>

      {/* ─── WHO IT'S FOR ─────────────────────────────────────────── */}
      <section className="py-20" style={{ background: "#F8FAFC" }} aria-labelledby="who-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-14 items-center">
            <AnimateOnScroll animation="fadeLeft">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#0F766E" }}>Who It&apos;s For</p>
                <h2 id="who-heading" className="text-3xl sm:text-4xl font-bold mb-6 tracking-tight" style={{ color: "#0F172A" }}>
                  Built for revenue teams that can&apos;t afford to waste a lead.
                </h2>
                <p className="text-base mb-8 leading-relaxed" style={{ color: "#64748B" }}>
                  Whether you run a five-person sales team or a 50-seat call centre,
                  LeadPilot gives you the operating leverage of a much larger team.
                  You define the rules — the AI does the work.
                </p>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { icon: Users, label: "Sales teams of 1–50+" },
                    { icon: Globe, label: "Multi-channel businesses" },
                    { icon: Brain, label: "AI-forward operators" },
                    { icon: BarChart3, label: "Data-driven leaders" },
                  ].map(({ icon: Icon, label }) => (
                    <div key={label} className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: "rgba(15,118,110,0.08)" }}>
                        <Icon className="w-4 h-4" style={{ color: "#0F766E" }} aria-hidden="true" />
                      </div>
                      <span className="text-sm font-medium" style={{ color: "#334155" }}>{label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </AnimateOnScroll>

            {/* AI Cockpit Visual */}
            <AnimateOnScroll animation="fadeRight" delay={120}>
              <div
                className="rounded-2xl p-6 relative overflow-hidden mk-scan-container"
                style={{ background: "#0E1826", border: "1px solid rgba(15,118,110,0.25)", boxShadow: "0 0 60px rgba(15,118,110,0.15)" }}
                aria-label="LeadPilot AI cockpit interface preview"
              >
                <div className="mk-scan-line" aria-hidden="true" />
                {/* Header bar */}
                <div className="flex items-center gap-2 mb-5 pb-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                  <div className="w-2 h-2 rounded-full" style={{ background: "#0F766E" }} aria-hidden="true" />
                  <div className="w-2 h-2 rounded-full" style={{ background: "#14B8A6" }} aria-hidden="true" />
                  <div className="w-2 h-2 rounded-full" style={{ background: "rgba(255,255,255,0.15)" }} aria-hidden="true" />
                  <span className="text-xs ml-2 font-mono" style={{ color: "#475569" }}>leadpilot — ai cockpit</span>
                </div>
                {/* Metrics row */}
                <div className="grid grid-cols-3 gap-3 mb-5">
                  {[
                    { label: "Leads Today", val: "48", trend: "+12%" },
                    { label: "Qualified", val: "31", trend: "64.5%" },
                    { label: "Routed", val: "28", trend: "90.3%" },
                  ].map(({ label, val, trend }) => (
                    <div key={label} className="rounded-lg p-3" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)" }}>
                      <p className="text-xs mb-1" style={{ color: "#475569" }}>{label}</p>
                      <p className="text-xl font-bold text-white mk-number-up">{val}</p>
                      <p className="text-xs mt-1" style={{ color: "#14B8A6" }}>{trend}</p>
                    </div>
                  ))}
                </div>
                {/* Lead feed */}
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "#475569" }}>Live Lead Feed</p>
                  {[
                    { name: "Sarah M.", source: "Web Form", score: 92, status: "Routed", color: "#10B981" },
                    { name: "David K.", source: "Chat", score: 78, status: "Qualifying", color: "#F59E0B" },
                    { name: "Priya L.", source: "Partner", score: 55, status: "Reviewing", color: "#94A3B8" },
                  ].map((lead) => (
                    <div key={lead.name} className="flex items-center justify-between rounded-lg px-3 py-2.5"
                      style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)" }}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                          style={{ background: "rgba(15,118,110,0.25)", color: "#14B8A6" }} aria-hidden="true"
                        >{lead.name[0]}</div>
                        <div>
                          <p className="text-xs font-medium text-white">{lead.name}</p>
                          <p className="text-xs" style={{ color: "#475569" }}>{lead.source}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="text-xs px-2 py-0.5 rounded font-mono" style={{ background: "rgba(15,118,110,0.2)", color: "#14B8A6" }}>{lead.score}</div>
                        <span className="text-xs" style={{ color: lead.color }}>{lead.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="absolute bottom-0 left-0 right-0 h-24 pointer-events-none" aria-hidden="true"
                  style={{ background: "linear-gradient(to top, rgba(15,118,110,0.15), transparent)" }}
                />
              </div>
            </AnimateOnScroll>
          </div>
        </div>
      </section>

      {/* ─── BEFORE vs AFTER ──────────────────────────────────────── */}
      <section className="py-20" style={{ background: "#0B1320" }} aria-labelledby="change-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <AnimateOnScroll animation="fadeUp">
            <div className="text-center mb-16">
              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#14B8A6" }}>Before vs After</p>
              <h2 id="change-heading" className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
                What changes when you adopt LeadPilot
              </h2>
            </div>
          </AnimateOnScroll>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <AnimateOnScroll animation="fadeLeft">
              <div className="rounded-2xl p-8" style={{ background: "rgba(239,68,68,0.05)", border: "1px solid rgba(239,68,68,0.15)" }}>
                <p className="text-xs font-bold uppercase tracking-widest mb-6" style={{ color: "#F87171" }}>Before</p>
                <ul className="space-y-4">
                  {["Reps spend 2–3 hours per day manually sorting leads", "Hot leads wait hours for a response", "No visibility into which rep owns which lead", "Follow-up depends on individual memory and discipline", "Leadership guesses at conversion rates"].map((item) => (
                    <li key={item} className="flex items-start gap-3">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0" style={{ background: "#EF4444" }} aria-hidden="true" />
                      <p className="text-sm" style={{ color: "#94A3B8" }}>{item}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </AnimateOnScroll>

            <AnimateOnScroll animation="fadeRight" delay={120}>
              <div className="rounded-2xl p-8" style={{ background: "rgba(15,118,110,0.06)", border: "1px solid rgba(15,118,110,0.25)" }}>
                <p className="text-xs font-bold uppercase tracking-widest mb-6" style={{ color: "#14B8A6" }}>After LeadPilot</p>
                <ul className="space-y-4">
                  {["AI qualifies every lead instantly — reps only touch hot opportunities", "Leads are routed and notified within seconds of arrival", "Full routing history and ownership log for every lead", "Automated sequences handle follow-up on schedule, every time", "Real-time dashboards give leadership full-funnel visibility"].map((item) => (
                    <li key={item} className="flex items-start gap-3">
                      <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" style={{ color: "#14B8A6" }} aria-hidden="true" />
                      <p className="text-sm" style={{ color: "#CBD5E1" }}>{item}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </AnimateOnScroll>
          </div>
        </div>
      </section>

      {/* ─── FULL HOW IT WORKS ────────────────────────────────────── */}
      <section className="py-24" style={{ background: "#F8FAFC" }} aria-labelledby="stages-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <AnimateOnScroll animation="fadeUp">
            <div className="text-center mb-16">
              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#0F766E" }}>The Platform in Depth</p>
              <h2 id="stages-heading" className="text-3xl sm:text-4xl font-bold tracking-tight" style={{ color: "#0F172A" }}>
                Every stage of the lead lifecycle — automated
              </h2>
            </div>
          </AnimateOnScroll>

          <div className="space-y-16">
            {stages.map((stage, i) => {
              const Icon = stage.icon;
              const reversed = i % 2 === 1;
              return (
                <AnimateOnScroll key={stage.step} animation={reversed ? "fadeRight" : "fadeLeft"} delay={60}>
                  <div className={`grid grid-cols-1 lg:grid-cols-2 gap-12 items-center`}>
                    <div className={reversed ? "lg:order-2" : ""}>
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                          style={{ background: "rgba(15,118,110,0.1)", border: "1px solid rgba(15,118,110,0.2)" }}
                        >
                          <Icon className="w-5 h-5" style={{ color: "#0F766E" }} aria-hidden="true" />
                        </div>
                        <span className="text-xs font-bold uppercase tracking-widest" style={{ color: "#0F766E" }}>
                          Step {stage.step} — {stage.title}
                        </span>
                      </div>
                      <h3 className="text-2xl font-bold mb-4 tracking-tight" style={{ color: "#0F172A" }}>{stage.headline}</h3>
                      <p className="text-base mb-6 leading-relaxed" style={{ color: "#64748B" }}>{stage.body}</p>
                      <ul className="space-y-2">
                        {stage.bullets.map((b) => (
                          <li key={b} className="flex items-center gap-2.5">
                            <CheckCircle className="w-4 h-4 shrink-0" style={{ color: "#0F766E" }} aria-hidden="true" />
                            <span className="text-sm" style={{ color: "#334155" }}>{b}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div
                      className={`rounded-2xl p-8 ${reversed ? "lg:order-1" : ""}`}
                      style={{ background: "#0E1826", border: "1px solid rgba(15,118,110,0.2)" }}
                      aria-hidden="true"
                    >
                      <div className="flex items-center gap-3 mb-5 pb-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "rgba(15,118,110,0.2)" }}>
                          <Icon className="w-4 h-4" style={{ color: "#14B8A6" }} />
                        </div>
                        <span className="text-sm font-semibold text-white">{stage.title}</span>
                        <span className="ml-auto text-xs px-2 py-0.5 rounded-full" style={{ background: "rgba(15,118,110,0.2)", color: "#14B8A6" }}>Live</span>
                      </div>
                      <div className="space-y-2">
                        {[...Array(3)].map((_, j) => (
                          <div key={j} className="h-8 rounded-lg" style={{ background: `rgba(255,255,255,${0.03 + j * 0.01})`, width: `${90 - j * 10}%` }} />
                        ))}
                      </div>
                      <div className="mt-5 pt-4" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                        <div className="flex justify-between text-xs" style={{ color: "#475569" }}>
                          <span>Processing...</span>
                          <span style={{ color: "#14B8A6" }}>✓ Complete</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </AnimateOnScroll>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── CTA ──────────────────────────────────────────────────── */}
      <CTASection
        headline="See LeadPilot working on your pipeline."
        subheadline="Sign up free and we'll show you exactly how it maps to your current workflow."
        primaryLabel="Start for Free"
        primaryHref="/signup"
        secondaryLabel="View Features"
        secondaryHref="/features"
      />

      {/* ─── NEXT STEPS ───────────────────────────────────────────── */}
      <section className="py-12" style={{ background: "#F8FAFC", borderTop: "1px solid #E2E8F0" }} aria-label="Next steps">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { label: "See all features", href: "/features", sub: "Full feature reference" },
              { label: "Explore use cases", href: "/use-cases", sub: "Industry-specific flows" },
              { label: "View plans", href: "/plans", sub: "Start free today" },
            ].map(({ label, href, sub }) => (
              <Link key={href} href={href} className="flex items-center justify-between p-5 rounded-xl mk-nav-card">
                <div>
                  <p className="font-semibold text-sm" style={{ color: "#0F172A" }}>{label}</p>
                  <p className="text-xs mt-0.5" style={{ color: "#94A3B8" }}>{sub}</p>
                </div>
                <ArrowRight className="w-4 h-4 shrink-0 mk-nav-arrow" style={{ color: "#0F766E" }} aria-hidden="true" />
              </Link>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
