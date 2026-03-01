import * as Icons from "lucide-react";
import { type LucideIcon, Clock } from "lucide-react";

interface FeatureCardProps {
  icon?: LucideIcon;
  iconName?: string;
  title: string;
  benefit: string;
  description: string;
  dark?: boolean;
  comingSoon?: boolean;
}

function resolveIcon(iconName?: string, icon?: LucideIcon): LucideIcon {
  if (icon) return icon;
  if (iconName && iconName in Icons) {
    return (Icons as unknown as Record<string, LucideIcon>)[iconName];
  }
  return Icons.Zap; // fallback
}

export default function FeatureCard({
  icon,
  iconName,
  title,
  benefit,
  description,
  dark = false,
  comingSoon = false,
}: FeatureCardProps) {
  const Icon = resolveIcon(iconName, icon);

  if (dark) {
    return (
      <div className={`relative rounded-xl p-6 ${comingSoon ? "catalog-card-muted" : "feature-card-dark"}`}>
        {comingSoon && (
          <div
            className="absolute top-4 right-4 flex items-center gap-1.5 px-2 py-0.5 rounded-full"
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.1)",
            }}
          >
            <Clock className="w-3 h-3" style={{ color: "#64748B" }} aria-hidden="true" />
            <span className="text-[10px] font-medium" style={{ color: "#64748B" }}>
              Coming Soon
            </span>
          </div>
        )}
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
    <div className={`relative rounded-xl p-6 ${comingSoon ? "opacity-50" : "feature-card-light"}`}>
      {comingSoon && (
        <div
          className="absolute top-4 right-4 flex items-center gap-1.5 px-2 py-0.5 rounded-full"
          style={{
            background: "rgba(15,118,110,0.08)",
            border: "1px solid rgba(15,118,110,0.2)",
          }}
        >
          <Clock className="w-3 h-3" style={{ color: "#64748B" }} aria-hidden="true" />
          <span className="text-[10px] font-medium" style={{ color: "#64748B" }}>
            Coming Soon
          </span>
        </div>
      )}
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
