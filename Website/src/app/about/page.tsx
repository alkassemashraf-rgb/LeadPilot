import type { Metadata } from "next";
import { Zap, Target, TrendingUp, Shield, ArrowRight } from "lucide-react";
import Link from "next/link";
import CTASection from "@/components/CTASection";
import AnimateOnScroll from "@/components/AnimateOnScroll";
import FloatingOrb from "@/components/FloatingOrb";

export const metadata: Metadata = {
  title: "About — Our Mission",
  description:
    "LeadPilot exists to give every revenue team operating leverage — not just the ones with massive headcount or big-company budgets.",
};

const values = [
  { icon: Zap, title: "Speed is revenue", description: "A lead that waits three hours is a lead that's already talking to your competitor. We obsess over time-to-response because that's where most pipeline is lost." },
  { icon: Target, title: "Precision over volume", description: "More leads aren't always better. Better qualification means your team spends time on prospects who will actually close. We're built for yield, not noise." },
  { icon: TrendingUp, title: "Revenue impact, not activity", description: "We don't measure success by features shipped. We measure it by the pipeline our customers close. That's the only metric that matters." },
  { icon: Shield, title: "Trust through transparency", description: "Full audit logs, clear data handling, honest pricing, and no surprise overages. We earn long-term trust by being straightforward from day one." },
];

export default function AboutPage() {
  return (
    <>
      {/* ─── HERO ─────────────────────────────────────────────────── */}
      <section className="relative py-28 overflow-hidden" style={{ background: "#0B1320" }} aria-labelledby="about-heading">
        <div className="absolute inset-0 mk-grid opacity-40" aria-hidden="true" />
        <div className="absolute inset-0 pointer-events-none" aria-hidden="true"
          style={{ background: "radial-gradient(ellipse 60% 50% at 50% 0%, rgba(15,118,110,0.25) 0%, transparent 70%)" }}
        />
        <FloatingOrb size={400} color="primary" top="50%" left="20%" opacity={0.10} blur={90} />

        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <AnimateOnScroll animation="fadeIn">
            <p className="text-xs font-bold uppercase tracking-widest mb-4" style={{ color: "#14B8A6" }}>About LeadPilot</p>
          </AnimateOnScroll>
          <AnimateOnScroll animation="fadeUp" delay={80}>
            <h1 id="about-heading" className="text-4xl sm:text-5xl md:text-6xl font-bold text-white mb-6 tracking-tight">
              We exist because
              <br />
              <span className="mk-gradient-text">leads deserve better.</span>
            </h1>
          </AnimateOnScroll>
          <AnimateOnScroll animation="fadeUp" delay={160}>
            <p className="text-lg max-w-2xl mx-auto leading-relaxed" style={{ color: "rgba(148,163,184,0.9)" }}>
              Too many revenue teams are losing deals not because they can&apos;t close,
              but because the process around capturing, qualifying, and routing leads
              is broken, manual, and slow.
            </p>
          </AnimateOnScroll>
        </div>
      </section>

      {/* ─── MISSION ──────────────────────────────────────────────── */}
      <section className="py-24" style={{ background: "#F8FAFC" }} aria-labelledby="mission-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <AnimateOnScroll animation="fadeLeft">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#0F766E" }}>Our Mission</p>
                <h2 id="mission-heading" className="text-3xl sm:text-4xl font-bold mb-6 tracking-tight" style={{ color: "#0F172A" }}>
                  Give every revenue team the operating leverage of a much larger organisation.
                </h2>
                <div className="space-y-5" style={{ color: "#64748B" }}>
                  <p className="text-base leading-relaxed">
                    We built LeadPilot because we saw the same problem everywhere: talented sales
                    teams spending hours on manual lead triage, qualification calls going to the
                    wrong rep, and follow-up depending on individual memory. Revenue left on the table
                    — not from lack of skill, but from lack of infrastructure.
                  </p>
                  <p className="text-base leading-relaxed">
                    AI has fundamentally changed what&apos;s possible for a small team. You no longer
                    need an army of BDRs to run a high-performance pipeline. You need the right
                    system — one that works 24/7, doesn&apos;t make hand-off mistakes, and gets smarter
                    over time.
                  </p>
                  <p className="text-base leading-relaxed">
                    That&apos;s what LeadPilot is. Not a chatbot. Not a CRM plugin. An AI-native
                    operating layer for your entire lead pipeline.
                  </p>
                </div>
              </div>
            </AnimateOnScroll>

            <AnimateOnScroll animation="fadeRight" delay={120}>
              <div className="rounded-2xl p-8" style={{ background: "#0E1826", border: "1px solid rgba(15,118,110,0.25)" }} aria-label="Trust statement">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-6"
                  style={{ background: "rgba(15,118,110,0.2)", border: "1px solid rgba(20,184,166,0.3)" }}
                >
                  <Zap className="w-6 h-6" style={{ color: "#14B8A6" }} aria-hidden="true" />
                </div>
                <blockquote>
                  <p className="text-xl font-semibold text-white leading-relaxed mb-6">
                    &ldquo;The quality of your pipeline depends on how fast and accurately
                    you respond to inbound interest. LeadPilot makes that instant, automatic,
                    and consistent — regardless of team size.&rdquo;
                  </p>
                </blockquote>
                <div className="pt-6" style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}>
                  <p className="text-sm font-semibold text-white">The LeadPilot Team</p>
                  <p className="text-xs mt-1" style={{ color: "#475569" }}>Built for revenue teams who move fast.</p>
                </div>
              </div>
            </AnimateOnScroll>
          </div>
        </div>
      </section>

      {/* ─── VALUES ───────────────────────────────────────────────── */}
      <section className="py-24" style={{ background: "#0B1320" }} aria-labelledby="values-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <AnimateOnScroll animation="fadeUp">
            <div className="text-center mb-16">
              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "#14B8A6" }}>What We Stand For</p>
              <h2 id="values-heading" className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
                Principles, not platitudes.
              </h2>
            </div>
          </AnimateOnScroll>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {values.map(({ icon: Icon, title, description }, i) => (
              <AnimateOnScroll key={title} animation="fadeUp" delay={i * 80}>
                <div className="rounded-xl p-8 mk-value-card">
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-5"
                    style={{ background: "rgba(15,118,110,0.2)", border: "1px solid rgba(20,184,166,0.25)" }}
                  >
                    <Icon className="w-5 h-5" style={{ color: "#14B8A6" }} aria-hidden="true" />
                  </div>
                  <h3 className="text-white font-semibold text-lg mb-3">{title}</h3>
                  <p className="text-sm leading-relaxed" style={{ color: "#94A3B8" }}>{description}</p>
                </div>
              </AnimateOnScroll>
            ))}
          </div>
        </div>
      </section>

      {/* ─── TRUST STATEMENT ──────────────────────────────────────── */}
      <section className="py-24" style={{ background: "#F8FAFC" }} aria-labelledby="trust-heading">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <AnimateOnScroll animation="fadeUp">
            <h2 id="trust-heading" className="text-3xl font-bold mb-6 tracking-tight" style={{ color: "#0F172A" }}>
              Built to earn your trust, not just your subscription.
            </h2>
          </AnimateOnScroll>
          <div className="space-y-5 text-left">
            {[
              { title: "No vendor lock-in", body: "Your lead data belongs to you. Export it at any time, in full. We don't make leaving artificially difficult." },
              { title: "Privacy by design", body: "Lead data is processed with strict access controls, encryption at rest and in transit, and full audit logging of every access event." },
              { title: "Honest communication", body: "We won't hide problems behind jargon or hide pricing in footnotes. If something breaks, we'll tell you. If pricing changes, you'll know in advance." },
            ].map(({ title, body }, i) => (
              <AnimateOnScroll key={title} animation="fadeUp" delay={i * 80}>
                <div className="rounded-xl p-6" style={{ background: "#FFFFFF", border: "1px solid #E2E8F0" }}>
                  <h3 className="font-semibold mb-2" style={{ color: "#0F172A" }}>{title}</h3>
                  <p className="text-sm leading-relaxed" style={{ color: "#64748B" }}>{body}</p>
                </div>
              </AnimateOnScroll>
            ))}
          </div>

          <AnimateOnScroll animation="zoomIn" delay={240}>
            <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/contact" className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl font-semibold text-sm mk-btn-primary">
                Get in Touch
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </Link>
              <Link href="/plans" className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl font-semibold text-sm mk-btn-ghost-light">
                View Plans
              </Link>
            </div>
          </AnimateOnScroll>
        </div>
      </section>

      {/* ─── CTA ──────────────────────────────────────────────────── */}
      <CTASection
        headline="Ready to work with us?"
        subheadline="Start with the Free plan or sign up to see LeadPilot in action."
        primaryLabel="Start for Free"
        primaryHref="/app/signup"
        secondaryLabel="Contact Us"
        secondaryHref="/contact"
      />
    </>
  );
}
