"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X, Zap } from "lucide-react";

const navLinks = [
  { label: "Product", href: "/product" },
  { label: "Features", href: "/features" },
  { label: "Use Cases", href: "/use-cases" },
  { label: "Plans", href: "/plans" },
  { label: "About", href: "/about" },
  { label: "Contact", href: "/contact" },
];

export default function Header() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header
      className="sticky top-0 z-50 w-full"
      style={{
        background: "rgba(11, 19, 32, 0.85)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderBottom: "1px solid rgba(255,255,255,0.07)",
      }}
    >
      <nav
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16"
        aria-label="Main navigation"
      >
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group" aria-label="LeadPilot home">
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

        {/* Desktop nav */}
        <ul className="hidden md:flex items-center gap-1" role="list">
          {navLinks.map((link) => {
            const active = pathname === link.href || pathname.startsWith(link.href + "/");
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className="px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200"
                  style={{
                    color: active ? "#14B8A6" : "rgba(241,245,249,0.75)",
                  }}
                  onMouseEnter={(e) => {
                    if (!active) e.currentTarget.style.color = "#F1F5F9";
                  }}
                  onMouseLeave={(e) => {
                    if (!active) e.currentTarget.style.color = "rgba(241,245,249,0.75)";
                  }}
                  aria-current={active ? "page" : undefined}
                >
                  {link.label}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Desktop CTAs */}
        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/login"
            className="text-sm font-medium transition-colors duration-200"
            style={{ color: "rgba(241,245,249,0.6)" }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "#F1F5F9"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "rgba(241,245,249,0.6)"; }}
          >
            Log in
          </Link>
          <Link
            href="/contact"
            className="px-4 py-2 rounded-lg text-sm font-semibold text-white transition-all duration-200"
            style={{ background: "linear-gradient(135deg, #0F766E, #14B8A6)" }}
            onMouseEnter={(e) => {
              e.currentTarget.style.boxShadow = "0 0 20px rgba(15,118,110,0.5)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            Book a Demo
          </Link>
        </div>

        {/* Mobile menu button */}
        <button
          className="md:hidden p-2 rounded-md text-slate-300 hover:text-white transition-colors"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileOpen}
          aria-controls="mobile-menu"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </nav>

      {/* Mobile menu */}
      {mobileOpen && (
        <div
          id="mobile-menu"
          className="md:hidden px-4 pb-4"
          style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}
        >
          <ul className="flex flex-col gap-1 mt-2" role="list">
            {navLinks.map((link) => {
              const active = pathname === link.href;
              return (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="block px-3 py-2 rounded-md text-sm font-medium"
                    style={{ color: active ? "#14B8A6" : "rgba(241,245,249,0.8)" }}
                    onClick={() => setMobileOpen(false)}
                    aria-current={active ? "page" : undefined}
                  >
                    {link.label}
                  </Link>
                </li>
              );
            })}
          </ul>
          <div className="flex flex-col gap-2 mt-4 pt-4" style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}>
            <Link
              href="/login"
              className="block px-3 py-2 rounded-md text-sm font-medium text-center"
              style={{ color: "rgba(241,245,249,0.7)" }}
              onClick={() => setMobileOpen(false)}
            >
              Log in
            </Link>
            <Link
              href="/contact"
              className="block px-4 py-2 rounded-lg text-sm font-semibold text-white text-center"
              style={{ background: "linear-gradient(135deg, #0F766E, #14B8A6)" }}
              onClick={() => setMobileOpen(false)}
            >
              Book a Demo
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
