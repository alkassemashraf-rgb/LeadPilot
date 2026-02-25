import type { Metadata } from "next";
import { Mail, MessageSquare, Clock } from "lucide-react";
import ContactForm from "@/components/marketing/ContactForm";
import AnimateOnScroll from "@/components/marketing/AnimateOnScroll";
import FloatingOrb from "@/components/marketing/FloatingOrb";

export const metadata: Metadata = {
  title: "Contact — Book a Demo or Get in Touch",
  description:
    "Book a demo, ask a question, or tell us about your pipeline. We respond within one business day.",
};

export default function ContactPage() {
  return (
    <>
      {/* ─── HERO ─────────────────────────────────────────────────── */}
      <section className="relative py-28 overflow-hidden" style={{ background: "#0B1320" }} aria-labelledby="contact-heading">
        <div className="absolute inset-0 mk-grid opacity-40" aria-hidden="true" />
        <div className="absolute inset-0 pointer-events-none" aria-hidden="true"
          style={{ background: "radial-gradient(ellipse 60% 50% at 50% 0%, rgba(15,118,110,0.25) 0%, transparent 70%)" }}
        />
        <FloatingOrb size={350} color="primary" top="60%" left="15%" opacity={0.10} blur={90} />

        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <AnimateOnScroll animation="fadeIn">
            <p className="text-xs font-bold uppercase tracking-widest mb-4" style={{ color: "#14B8A6" }}>Contact</p>
          </AnimateOnScroll>
          <AnimateOnScroll animation="fadeUp" delay={80}>
            <h1 id="contact-heading" className="text-4xl sm:text-5xl md:text-6xl font-bold text-white mb-6 tracking-tight">
              Let&apos;s talk about
              <br />
              <span className="mk-gradient-text">your pipeline.</span>
            </h1>
          </AnimateOnScroll>
          <AnimateOnScroll animation="fadeUp" delay={160}>
            <p className="text-lg max-w-xl mx-auto leading-relaxed" style={{ color: "rgba(148,163,184,0.9)" }}>
              Book a demo, ask a question, or tell us about your current lead process.
              We respond within one business day.
            </p>
          </AnimateOnScroll>
        </div>
      </section>

      {/* ─── CONTACT BODY ─────────────────────────────────────────── */}
      <section className="py-24" style={{ background: "#0B1320" }} aria-label="Contact form and details">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
            {/* Sidebar */}
            <AnimateOnScroll animation="fadeLeft">
              <aside>
                <div className="space-y-6">
                  {/* Email */}
                  <div className="rounded-xl p-6" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <div className="w-9 h-9 rounded-lg flex items-center justify-center mb-4"
                      style={{ background: "rgba(15,118,110,0.2)", border: "1px solid rgba(20,184,166,0.25)" }}
                    >
                      <Mail className="w-4 h-4" style={{ color: "#14B8A6" }} aria-hidden="true" />
                    </div>
                    <h3 className="text-white font-semibold mb-1 text-sm">Email us directly</h3>
                    <p className="text-xs mb-3" style={{ color: "#64748B" }}>For general enquiries, partnerships, or support</p>
                    <a href="mailto:hello@leadpilot.io" className="text-sm font-medium mk-text-link-teal">hello@leadpilot.io</a>
                  </div>

                  {/* Demo */}
                  <div className="rounded-xl p-6" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <div className="w-9 h-9 rounded-lg flex items-center justify-center mb-4"
                      style={{ background: "rgba(15,118,110,0.2)", border: "1px solid rgba(20,184,166,0.25)" }}
                    >
                      <MessageSquare className="w-4 h-4" style={{ color: "#14B8A6" }} aria-hidden="true" />
                    </div>
                    <h3 className="text-white font-semibold mb-1 text-sm">Book a demo</h3>
                    <p className="text-xs" style={{ color: "#64748B" }}>
                      A 20-minute walkthrough of LeadPilot on your actual workflow. No slides. No generic decks.
                    </p>
                  </div>

                  {/* Response time */}
                  <div className="rounded-xl p-6" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <div className="w-9 h-9 rounded-lg flex items-center justify-center mb-4"
                      style={{ background: "rgba(15,118,110,0.2)", border: "1px solid rgba(20,184,166,0.25)" }}
                    >
                      <Clock className="w-4 h-4" style={{ color: "#14B8A6" }} aria-hidden="true" />
                    </div>
                    <h3 className="text-white font-semibold mb-1 text-sm">Response time</h3>
                    <p className="text-xs" style={{ color: "#64748B" }}>
                      We respond to all enquiries within one business day. Urgent? Email us directly.
                    </p>
                  </div>

                  {/* What to expect */}
                  <div className="rounded-xl p-6" style={{ background: "rgba(15,118,110,0.07)", border: "1px solid rgba(15,118,110,0.2)" }}>
                    <h3 className="font-semibold mb-3 text-sm" style={{ color: "#14B8A6" }}>What to expect in a demo</h3>
                    <ul className="space-y-2">
                      {["We map LeadPilot to your current inbound flow", "Live walkthrough — no recorded slides", "Q&A on your specific use case", "Access to Free plan immediately after"].map((item) => (
                        <li key={item} className="text-xs flex items-start gap-2" style={{ color: "#94A3B8" }}>
                          <span style={{ color: "#14B8A6" }} aria-hidden="true">›</span>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </aside>
            </AnimateOnScroll>

            {/* Main form */}
            <AnimateOnScroll animation="fadeRight" delay={120} className="lg:col-span-2">
              <div className="rounded-2xl p-8" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
                <h2 className="text-xl font-bold text-white mb-2">Send us a message</h2>
                <p className="text-sm mb-8" style={{ color: "#64748B" }}>
                  Fill in the form below and we&apos;ll get back to you within one business day.
                </p>
                <ContactForm dark />
              </div>
            </AnimateOnScroll>
          </div>
        </div>
      </section>

      {/* ─── REASSURANCE STRIP ────────────────────────────────────── */}
      <section className="py-12 border-t" style={{ background: "#0E1826", borderColor: "rgba(255,255,255,0.07)" }} aria-label="Contact reassurance">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <AnimateOnScroll animation="fadeUp">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 text-center">
              {[
                { title: "No pressure", body: "A demo is just a conversation. No hard sell." },
                { title: "No commitment", body: "Start free. Upgrade only when it makes sense." },
                { title: "No nonsense", body: "Direct answers, honest timelines, clear pricing." },
              ].map(({ title, body }) => (
                <div key={title}>
                  <p className="text-sm font-semibold mb-1" style={{ color: "#CBD5E1" }}>{title}</p>
                  <p className="text-xs" style={{ color: "#475569" }}>{body}</p>
                </div>
              ))}
            </div>
          </AnimateOnScroll>
        </div>
      </section>
    </>
  );
}
