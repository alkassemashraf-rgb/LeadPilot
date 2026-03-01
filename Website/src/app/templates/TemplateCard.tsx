import type { CatalogTemplate } from "@/lib/api";
import type { LucideIcon } from "lucide-react";
import {
  Star,
  Copy,
  ArrowUpRight,
  Target,
  TrendingUp,
  Headphones,
  UserPlus,
} from "lucide-react";

const CATEGORY_META: Record<string, { color: string; Icon: LucideIcon }> = {
  lead_generation: { color: "#14B8A6", Icon: Target },
  sales: { color: "#60A5FA", Icon: TrendingUp },
  customer_support: { color: "#FBBF24", Icon: Headphones },
  onboarding: { color: "#C084FC", Icon: UserPlus },
};

interface Props {
  template: CatalogTemplate;
  featured?: boolean;
}

export default function TemplateCard({ template: t, featured = false }: Props) {
  const meta = CATEGORY_META[t.category] ?? { color: "#14B8A6", Icon: Target };
  const { color, Icon } = meta;

  return (
    <div
      className={`group relative flex flex-col ${featured ? "gradient-border p-7" : "catalog-card p-6"}`}
    >
      {/* Header: icon + hover arrow */}
      <div className="flex items-start justify-between mb-4">
        <div
          className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
          style={{
            background: `${color}15`,
            border: `1px solid ${color}30`,
          }}
        >
          <Icon className="w-5 h-5" style={{ color }} aria-hidden="true" />
        </div>
        <div className="flex items-center gap-2">
          {t.is_featured && (
            <Star
              className="w-3.5 h-3.5 fill-current"
              style={{ color: "#FBBF24" }}
              aria-hidden="true"
            />
          )}
          <ArrowUpRight
            className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
            style={{ color }}
            aria-hidden="true"
          />
        </div>
      </div>

      {/* Category badge */}
      <span className="badge-category self-start mb-3" data-category={t.category}>
        {t.category.replace(/_/g, " ")}
      </span>

      {/* Name */}
      <h3 className="text-white font-bold text-base mb-1.5">{t.name}</h3>

      {/* Description */}
      <p
        className={`text-sm leading-relaxed ${featured ? "line-clamp-3" : "line-clamp-2"} flex-1 mb-4`}
        style={{ color: "rgba(148,163,184,0.85)" }}
      >
        {t.description}
      </p>

      {/* Divider */}
      <div className="mb-3" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }} />

      {/* Footer: platforms + clone count */}
      <div className="flex items-center justify-between">
        <div className="flex flex-wrap gap-1.5">
          {t.platforms.map((p) => (
            <span key={p} className="badge-platform">{p}</span>
          ))}
        </div>
        {t.clone_count > 0 && (
          <span
            className="inline-flex items-center gap-1 text-[10px]"
            style={{ color: "#475569" }}
          >
            <Copy className="w-3 h-3" aria-hidden="true" />
            {t.clone_count.toLocaleString()}
          </span>
        )}
      </div>

      {/* Required integrations */}
      {t.required_integrations.length > 0 && (
        <p className="text-[10px] mt-2" style={{ color: "#475569" }}>
          Requires: {t.required_integrations.join(", ")}
        </p>
      )}
    </div>
  );
}
