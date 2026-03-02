"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { Menu, X, Zap, ChevronDown } from "lucide-react";

type NavItem = {
  label: string;
  href?: string;
  dropdown?: { label: string; href: string }[];
};

const navLinks: NavItem[] = [
  {
    label: "Platform",
    dropdown: [
      { label: "Product Overview", href: "/product" },
      { label: "All Features", href: "/features" },
      { label: "Use Cases", href: "/use-cases" },
    ],
  },
  { label: "Pricing", href: "/plans" },
  {
    label: "Company",
    dropdown: [
      { label: "About Us", href: "/about" },
      { label: "Contact", href: "/contact" },
    ],
  },
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
        background: scrolled ? "rgba(4,9,20,0.85)" : "rgba(4,9,20,0.5)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        boxShadow: scrolled ? "0 4px 24px rgba(0,0,0,0.4)" : "none",
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
            style={{ background: "#0B1320", border: "1px solid rgba(255,255,255,0.1)" }}
          >
            <Zap className="w-4 h-4 text-white" aria-hidden="true" />
          </div>
          <span className="text-white font-bold text-lg tracking-tight">
            LeadPilot
          </span>
        </Link>

        {/* Desktop nav */}
        <ul className="hidden md:flex items-center gap-2" role="list">
          {navLinks.map((navItem) => {
            const hasActiveDropdown = navItem.dropdown?.some((sub) => pathname === sub.href || pathname.startsWith(sub.href + "/"));
            const active = navItem.href ? pathname === navItem.href || (navItem.href !== "/" && pathname.startsWith(navItem.href)) : hasActiveDropdown;

            return (
              <li key={navItem.label} className="relative group/nav">
                {navItem.dropdown ? (
                  <>
                    <button
                      className="flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 cursor-pointer"
                      style={{ color: active ? "#FFFFFF" : "rgba(241,245,249,0.7)" }}
                    >
                      <span className="group-hover/nav:text-white transition-colors duration-150">
                        {navItem.label}
                      </span>
                      <ChevronDown className="w-3.5 h-3.5 opacity-60 group-hover/nav:text-white transition-transform duration-200 group-hover/nav:rotate-180" />
                    </button>
                    {/* Dropdown Menu */}
                    <div className="absolute top-full left-0 pt-2 opacity-0 translate-y-2 pointer-events-none group-hover/nav:opacity-100 group-hover/nav:translate-y-0 group-hover/nav:pointer-events-auto transition-all duration-200 z-50">
                      <div className="w-48 p-2 rounded-xl border flex flex-col gap-1 shadow-2xl" style={{ background: "rgba(11,19,32,0.95)", backdropFilter: "blur(12px)", borderColor: "rgba(255,255,255,0.08)" }}>
                        {navItem.dropdown.map((sub) => (
                          <Link key={sub.href} href={sub.href} className="px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                            {sub.label}
                          </Link>
                        ))}
                      </div>
                    </div>
                  </>
                ) : (
                  <Link
                    href={navItem.href!}
                    className="relative px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200"
                    style={{ color: active ? "#FFFFFF" : "rgba(241,245,249,0.7)" }}
                    aria-current={active ? "page" : undefined}
                  >
                    <span className="relative hover:text-white transition-colors duration-150">
                      {navItem.label}
                    </span>
                  </Link>
                )}
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
            {navLinks.map((navItem) => (
              <li key={navItem.label}>
                {navItem.dropdown ? (
                  <div className="space-y-1">
                    <div className="px-3 py-2 text-xs font-bold uppercase tracking-widest text-slate-500 mt-2">
                      {navItem.label}
                    </div>
                    {navItem.dropdown.map((sub) => (
                      <Link
                        key={sub.href}
                        href={sub.href}
                        className="block px-3 py-2.5 ml-2 rounded-lg text-sm font-medium transition-colors duration-200"
                        style={{
                          color: pathname === sub.href ? "#FFFFFF" : "rgba(241,245,249,0.8)",
                          background: pathname === sub.href ? "rgba(255,255,255,0.06)" : "transparent",
                        }}
                        onClick={() => setOpen(false)}
                      >
                        {sub.label}
                      </Link>
                    ))}
                  </div>
                ) : (
                  <Link
                    href={navItem.href!}
                    className="block px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-200 mt-2"
                    style={{
                      color: pathname === navItem.href ? "#FFFFFF" : "rgba(241,245,249,0.8)",
                      background: pathname === navItem.href ? "rgba(255,255,255,0.06)" : "transparent",
                    }}
                    onClick={() => setOpen(false)}
                  >
                    {navItem.label}
                  </Link>
                )}
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
