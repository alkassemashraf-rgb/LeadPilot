import Link from "next/link";
import { Check, Clock } from "lucide-react";

interface Props {
  name: string;
  tagline: string;
  price: string;
  priceNote?: string;
  features: string[];
  notIncluded?: string[];
  ctaLabel: string;
  ctaHref?: string;
  available: boolean;
  highlighted?: boolean;
}

export default function PlanCard({
  name, tagline, price, priceNote, features, notIncluded = [],
  ctaLabel, ctaHref = "/app/signup", available, highlighted = false,
}: Props) {
  return (
    <div
      className="relative rounded-2xl p-8 flex flex-col"
      style={
        highlighted
          ? { background: "rgba(15,118,110,0.09)", border: "1px solid rgba(15,118,110,0.45)", boxShadow: "0 0 50px rgba(15,118,110,0.2)" }
          : available
          ? { background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)" }
          : { background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", opacity: 0.65 }
      }
    >
      {!available && (
        <div
          className="absolute top-4 right-4 flex items-center gap-1.5 px-2.5 py-1 rounded-full"
          style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}
        >
          <Clock className="w-3 h-3" style={{ color: "#64748B" }} aria-hidden="true" />
          <span className="text-xs font-medium" style={{ color: "#64748B" }}>Coming Soon</span>
        </div>
      )}
      {highlighted && available && (
        <div
          className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-xs font-bold text-white whitespace-nowrap"
          style={{ background: "linear-gradient(135deg, #0F766E, #14B8A6)" }}
        >
          Available Now
        </div>
      )}

      <div className="mb-6">
        <h3 className="text-lg font-bold mb-1" style={{ color: available ? "#F1F5F9" : "#64748B" }}>
          {name}
        </h3>
        <p className="text-sm" style={{ color: available ? "#94A3B8" : "#475569" }}>{tagline}</p>
      </div>

      <div className="mb-8">
        <span className="text-3xl font-bold" style={{ color: available ? "#FFFFFF" : "#475569" }}>
          {price}
        </span>
        {priceNote && (
          <span className="text-sm ml-2" style={{ color: "#64748B" }}>{priceNote}</span>
        )}
      </div>

      <ul className="space-y-3 mb-8 flex-1" role="list">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2.5">
            <Check className="w-4 h-4 mt-0.5 shrink-0" style={{ color: available ? "#14B8A6" : "#334155" }} aria-hidden="true" />
            <span className="text-sm" style={{ color: available ? "#CBD5E1" : "#475569" }}>{f}</span>
          </li>
        ))}
        {notIncluded.map((f) => (
          <li key={f} className="flex items-start gap-2.5 opacity-35">
            <span className="w-4 h-4 mt-0.5 shrink-0 text-center text-xs" style={{ color: "#475569" }} aria-hidden="true">—</span>
            <span className="text-sm line-through" style={{ color: "#475569" }}>{f}</span>
          </li>
        ))}
      </ul>

      {available ? (
        <a href={ctaHref} className="block text-center px-6 py-3 rounded-xl font-semibold text-sm mk-btn-primary">
          {ctaLabel}
        </a>
      ) : (
        <a href="#waitlist" className="block text-center px-6 py-3 rounded-xl font-semibold text-sm mk-coming-soon-btn">
          Join Waitlist
        </a>
      )}
    </div>
  );
}
