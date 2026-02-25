import Link from "next/link";
import { Check, Clock } from "lucide-react";

interface PlanCardProps {
  name: string;
  tagline: string;
  price: string;
  priceNote?: string;
  features: string[];
  ctaLabel: string;
  ctaHref?: string;
  available: boolean;
  highlighted?: boolean;
}

export default function PlanCard({
  name,
  tagline,
  price,
  priceNote,
  features,
  ctaLabel,
  ctaHref = "/plans",
  available,
  highlighted = false,
}: PlanCardProps) {
  return (
    <div
      className="relative rounded-2xl p-8 flex flex-col transition-all duration-300"
      style={
        highlighted
          ? {
              background: "rgba(15,118,110,0.08)",
              border: "1px solid rgba(15,118,110,0.4)",
              boxShadow: "0 0 40px rgba(15,118,110,0.2)",
            }
          : available
          ? {
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.1)",
            }
          : {
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)",
              opacity: 0.7,
            }
      }
    >
      {/* Coming Soon badge */}
      {!available && (
        <div
          className="absolute top-4 right-4 flex items-center gap-1.5 px-2.5 py-1 rounded-full"
          style={{
            background: "rgba(255,255,255,0.06)",
            border: "1px solid rgba(255,255,255,0.1)",
          }}
        >
          <Clock className="w-3 h-3" style={{ color: "#94A3B8" }} aria-hidden="true" />
          <span className="text-xs font-medium" style={{ color: "#94A3B8" }}>
            Coming Soon
          </span>
        </div>
      )}

      {/* Highlighted badge */}
      {highlighted && available && (
        <div
          className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-xs font-semibold text-white"
          style={{ background: "linear-gradient(135deg, #0F766E, #14B8A6)" }}
        >
          Available Now
        </div>
      )}

      <div className="mb-6">
        <h3
          className="text-lg font-bold mb-1"
          style={{ color: available ? "#F1F5F9" : "#94A3B8" }}
        >
          {name}
        </h3>
        <p className="text-sm" style={{ color: available ? "#94A3B8" : "#64748B" }}>
          {tagline}
        </p>
      </div>

      <div className="mb-6">
        <span
          className="text-4xl font-bold"
          style={{ color: available ? "#FFFFFF" : "#64748B" }}
        >
          {price}
        </span>
        {priceNote && (
          <span className="text-sm ml-2" style={{ color: available ? "#94A3B8" : "#64748B" }}>
            {priceNote}
          </span>
        )}
      </div>

      <ul className="space-y-3 mb-8 flex-1" role="list">
        {features.map((feat) => (
          <li key={feat} className="flex items-start gap-2.5">
            <Check
              className="w-4 h-4 mt-0.5 shrink-0"
              style={{ color: available ? "#14B8A6" : "#475569" }}
              aria-hidden="true"
            />
            <span className="text-sm" style={{ color: available ? "#CBD5E1" : "#64748B" }}>
              {feat}
            </span>
          </li>
        ))}
      </ul>

      {available ? (
        <Link
          href={ctaHref}
          className="block text-center px-6 py-3 rounded-xl font-semibold text-sm btn-primary"
        >
          {ctaLabel}
        </Link>
      ) : (
        <button
          disabled
          aria-disabled="true"
          className="block w-full text-center px-6 py-3 rounded-xl font-semibold text-sm cursor-not-allowed"
          style={{
            background: "rgba(255,255,255,0.06)",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#475569",
          }}
        >
          {ctaLabel}
        </button>
      )}
    </div>
  );
}
