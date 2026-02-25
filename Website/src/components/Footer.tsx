import Link from "next/link";
import { Zap, Twitter, Linkedin, Github } from "lucide-react";

const footerNav = {
  Product: [
    { label: "How it Works", href: "/product" },
    { label: "Features", href: "/features" },
    { label: "Use Cases", href: "/use-cases" },
    { label: "Plans", href: "/plans" },
  ],
  Company: [
    { label: "About", href: "/about" },
    { label: "Contact", href: "/contact" },
    { label: "Book a Demo", href: "/contact" },
  ],
  Legal: [
    { label: "Privacy Policy", href: "#" },
    { label: "Terms of Service", href: "#" },
    { label: "Cookie Policy", href: "#" },
  ],
};

export default function Footer() {
  return (
    <footer
      style={{ background: "#070E1A", borderTop: "1px solid rgba(255,255,255,0.07)" }}
      aria-label="Site footer"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-12">
          {/* Brand */}
          <div className="md:col-span-2">
            <Link href="/" className="flex items-center gap-2 mb-4">
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
            <p className="text-sm leading-relaxed mb-6" style={{ color: "rgba(148,163,184,0.9)" }}>
              The AI-native lead platform that captures, qualifies, and routes prospects
              to the right rep — automatically. Built for revenue teams that can&apos;t afford to waste leads.
            </p>
            <div className="flex items-center gap-3">
              {[
                { icon: Twitter, label: "Twitter / X", href: "#" },
                { icon: Linkedin, label: "LinkedIn", href: "#" },
                { icon: Github, label: "GitHub", href: "#" },
              ].map(({ icon: Icon, label, href }) => (
                <a
                  key={label}
                  href={href}
                  aria-label={label}
                  className="w-9 h-9 rounded-lg flex items-center justify-center social-icon"
                >
                  <Icon className="w-4 h-4" aria-hidden="true" />
                </a>
              ))}
            </div>
          </div>

          {/* Nav columns */}
          {Object.entries(footerNav).map(([section, links]) => (
            <div key={section}>
              <h3
                className="text-xs font-bold uppercase tracking-widest mb-4"
                style={{ color: "rgba(148,163,184,0.5)" }}
              >
                {section}
              </h3>
              <ul className="space-y-3" role="list">
                {links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm footer-link"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div
          className="mt-12 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4"
          style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}
        >
          <p className="text-xs" style={{ color: "rgba(148,163,184,0.4)" }}>
            © {new Date().getFullYear()} LeadPilot. All rights reserved.
          </p>
          <p className="text-xs" style={{ color: "rgba(148,163,184,0.4)" }}>
            Built for revenue teams who move fast.
          </p>
        </div>
      </div>
    </footer>
  );
}
