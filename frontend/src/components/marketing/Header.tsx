"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { Menu, X, Zap } from "lucide-react";

const navLinks = [
  { label: "Product",   href: "/product" },
  { label: "Features",  href: "/features" },
  { label: "Use Cases", href: "/use-cases" },
  { label: "Plans",     href: "/plans" },
  { label: "About",     href: "/about" },
  { label: "Contact",   href: "/contact" },
];

export default function MarketingHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  return (
    <header
      className="sticky top-0 z-50 w-full transition-all duration-300"
      style={{
        background: scrolled ? "rgba(7,14,28,0.92)" : "rgba(7,14,28,0.6)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderBottom: scrolled
          ? "1px solid rgba(20,184,166,0.12)"
          : "1px solid rgba(255,255,255,0.05)",
        boxShadow: scrolled ? "0 8px 32px rgba(0,0,0,0.3)" : "none",
      }}
    >
      <nav
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16"
        aria-label="Main navigation"
      >
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group" aria-label="LeadPilot home">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center relative"
            style={{ background: "linear-gradient(135deg, #0F766E, #14B8A6)" }}
          >
            <Zap className="w-4 h-4 text-white" aria-hidden="true" />
            {/* pulse ring */}
            <span
              className="absolute inset-0 rounded-lg"
              style={{
                border: "1px solid rgba(20,184,166,0.6)",
                animation: "mk-pulse-ring 2.5s cubic-bezier(0.25,0.5,0.5,1) infinite",
              }}
              aria-hidden="true"
            />
          </div>
          <span className="text-white font-bold text-lg tracking-tight">
            Lead<span style={{ color: "#14B8A6" }}>Pilot</span>
          </span>
        </Link>

        {/* Desktop nav */}
        <ul className="hidden md:flex items-center gap-0.5" role="list">
          {navLinks.map(({ label, href }) => {
            const active = pathname === href || (href !== "/" && pathname.startsWith(href));
            return (
              <li key={href}>
                <Link
                  href={href}
                  className="relative px-3.5 py-2 rounded-md text-sm font-medium transition-colors duration-200"
                  style={{ color: active ? "#14B8A6" : "rgba(241,245,249,0.7)" }}
                  aria-current={active ? "page" : undefined}
                >
                  {active && (
                    <span
                      className="absolute bottom-1 left-1/2 -translate-x-1/2 h-0.5 w-4 rounded-full"
                      style={{ background: "#14B8A6" }}
                      aria-hidden="true"
                    />
                  )}
                  <span className="relative hover:text-white transition-colors duration-150">
                    {label}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Desktop CTAs */}
        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/login"
            className="text-sm font-medium transition-colors duration-200 mk-footer-link px-2 py-1"
          >
            Log in
          </Link>
          <Link
            href="/signup"
            className="px-4 py-2 rounded-lg text-sm font-semibold text-white mk-btn-primary"
          >
            Start for Free
          </Link>
        </div>

        {/* Mobile toggle */}
        <button
          className="md:hidden p-2 rounded-md transition-colors"
          style={{ color: "rgba(241,245,249,0.8)" }}
          onClick={() => setOpen(!open)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="mk-mobile-menu"
        >
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </nav>

      {/* Mobile menu */}
      <div
        id="mk-mobile-menu"
        style={{
          maxHeight: open ? "480px" : "0",
          overflow: "hidden",
          transition: "max-height 0.35s cubic-bezier(0.16,1,0.3,1)",
          borderTop: open ? "1px solid rgba(255,255,255,0.06)" : "none",
        }}
      >
        <div className="px-4 pb-5 pt-3">
          <ul className="space-y-1" role="list">
            {navLinks.map(({ label, href }) => (
              <li key={href}>
                <Link
                  href={href}
                  className="block px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-200"
                  style={{
                    color: pathname === href ? "#14B8A6" : "rgba(241,245,249,0.8)",
                    background: pathname === href ? "rgba(20,184,166,0.08)" : "transparent",
                  }}
                  onClick={() => setOpen(false)}
                >
                  {label}
                </Link>
              </li>
            ))}
          </ul>
          <div
            className="flex flex-col gap-2.5 mt-4 pt-4"
            style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}
          >
            <Link
              href="/login"
              className="block py-2.5 rounded-lg text-sm font-medium text-center mk-footer-link"
              onClick={() => setOpen(false)}
            >
              Log in
            </Link>
            <Link
              href="/signup"
              className="block py-2.5 rounded-xl text-sm font-semibold text-white text-center mk-btn-primary"
              onClick={() => setOpen(false)}
            >
              Start for Free
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}
