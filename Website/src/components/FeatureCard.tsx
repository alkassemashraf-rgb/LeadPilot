import { type LucideIcon } from "lucide-react";

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  benefit: string;
  description: string;
  dark?: boolean;
}

export default function FeatureCard({
  icon: Icon,
  title,
  benefit,
  description,
  dark = false,
}: FeatureCardProps) {
  if (dark) {
    return (
      <div className="rounded-xl p-6 feature-card-dark">
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center mb-4"
          style={{ background: "rgba(15,118,110,0.2)", border: "1px solid rgba(20,184,166,0.25)" }}
        >
          <Icon className="w-5 h-5" style={{ color: "#14B8A6" }} aria-hidden="true" />
        </div>
        <p
          className="text-xs font-bold uppercase tracking-widest mb-1"
          style={{ color: "#14B8A6" }}
        >
          {benefit}
        </p>
        <h3 className="text-white font-semibold text-base mb-2">{title}</h3>
        <p className="text-sm leading-relaxed" style={{ color: "rgba(148,163,184,0.85)" }}>
          {description}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl p-6 feature-card-light">
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center mb-4"
        style={{ background: "rgba(15,118,110,0.08)", border: "1px solid rgba(15,118,110,0.15)" }}
      >
        <Icon className="w-5 h-5" style={{ color: "#0F766E" }} aria-hidden="true" />
      </div>
      <p
        className="text-xs font-bold uppercase tracking-widest mb-1"
        style={{ color: "#0F766E" }}
      >
        {benefit}
      </p>
      <h3 className="font-semibold text-base mb-2" style={{ color: "#1E293B" }}>
        {title}
      </h3>
      <p className="text-sm leading-relaxed" style={{ color: "#64748B" }}>
        {description}
      </p>
    </div>
  );
}
