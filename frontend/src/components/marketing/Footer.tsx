import Link from "next/link";
import { Zap, Twitter, Linkedin, Github } from "lucide-react";

const cols = {
  Product: [
    { label: "How it Works", href: "/product" },
    { label: "Features",     href: "/features" },
    { label: "Use Cases",    href: "/use-cases" },
    { label: "Plans",        href: "/plans" },
  ],
  Company: [
    { label: "About",      href: "/about" },
    { label: "Contact",    href: "/contact" },
    { label: "Start Free", href: "/signup" },
  ],
  Legal: [
    { label: "Privacy Policy",   href: "#" },
    { label: "Terms of Service", href: "#" },
    { label: "Cookie Policy",    href: "#" },
  ],
};

export default function MarketingFooter() {
  return (
    <footer
      style={{
        background: "#040A13",
        borderTop: "1px solid rgba(255,255,255,0.06)",
      }}
      aria-label="Site footer"
    >
      {/* Separator glow line */}
      <div
        className="h-px w-full"
        style={{
          background: "linear-gradient(90deg, transparent, rgba(15,118,110,0.4) 30%, rgba(20,184,166,0.5) 50%, rgba(15,118,110,0.4) 70%, transparent)",
        }}
        aria-hidden="true"
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-12">
          {/* Brand */}
          <div className="md:col-span-2">
            <Link href="/" className="flex items-center gap-2.5 mb-5">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center"
                style={{ background: "linear-gradient(135deg, #0F766E, #14B8A6)" }}
              >
                <Zap className="w-4 h-4 text-white" aria-hidden="true" />
              </div>
              <span className="text-white font-bold text-lg tracking-tight">
                Lead<span style={{ color: "#14B8A6" }}>Pilot</span>
              </span>
            </Link>
            <p
              className="text-sm leading-relaxed mb-6"
              style={{ color: "rgba(148,163,184,0.75)" }}
            >
              The AI-native platform that captures, qualifies, and routes every lead
              to the right rep — automatically. Built for revenue teams that move fast.
            </p>

            <div className="flex items-center gap-3 mb-8">
              {[
                { icon: Twitter, label: "Twitter / X" },
                { icon: Linkedin, label: "LinkedIn" },
                { icon: Github, label: "GitHub" },
              ].map(({ icon: Icon, label }) => (
                <a
                  key={label}
                  href="#"
                  aria-label={label}
                  className="w-9 h-9 rounded-lg flex items-center justify-center mk-social-icon"
                >
                  <Icon className="w-4 h-4" aria-hidden="true" />
                </a>
              ))}
            </div>

            {/* Mini CTA */}
            <Link
              href="/signup"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white mk-btn-primary"
            >
              Start for Free →
            </Link>
          </div>

          {/* Nav columns */}
          {Object.entries(cols).map(([section, links]) => (
            <div key={section}>
              <h3
                className="text-xs font-bold uppercase tracking-widest mb-4"
                style={{ color: "rgba(148,163,184,0.4)" }}
              >
                {section}
              </h3>
              <ul className="space-y-3" role="list">
                {links.map(({ label, href }) => (
                  <li key={label}>
                    <Link href={href} className="text-sm mk-footer-link">
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div
          className="mt-12 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4"
          style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}
        >
          <p className="text-xs" style={{ color: "rgba(148,163,184,0.35)" }}>
            © {new Date().getFullYear()} LeadPilot. All rights reserved.
          </p>
          <p className="text-xs" style={{ color: "rgba(148,163,184,0.35)" }}>
            Built for revenue teams who move fast.
          </p>
        </div>
      </div>
    </footer>
  );
}
