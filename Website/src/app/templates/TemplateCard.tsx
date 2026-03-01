import type { CatalogTemplate } from "@/lib/api";
import { Star } from "lucide-react";

interface Props {
  template: CatalogTemplate;
}

export default function TemplateCard({ template: t }: Props) {
  return (
    <div className="catalog-card p-6 flex flex-col">
      {/* Top row: category + featured */}
      <div className="flex items-center gap-2 mb-3">
        <span className="badge-category" data-category={t.category}>
          {t.category.replace(/_/g, " ")}
        </span>
        {t.is_featured && (
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold" style={{ color: "#FBBF24" }}>
            <Star className="w-3 h-3 fill-current" aria-hidden="true" />
            Featured
          </span>
        )}
      </div>

      {/* Name + description */}
      <h3 className="text-white font-semibold text-base mb-1">{t.name}</h3>
      <p
        className="text-sm leading-relaxed line-clamp-2 flex-1 mb-4"
        style={{ color: "rgba(148,163,184,0.85)" }}
      >
        {t.description}
      </p>

      {/* Platform + integration badges */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {t.platforms.map((p) => (
          <span key={p} className="badge-platform">{p}</span>
        ))}
      </div>

      {/* Required integrations */}
      {t.required_integrations.length > 0 && (
        <p className="text-[10px] mb-2" style={{ color: "#475569" }}>
          Requires: {t.required_integrations.join(", ")}
        </p>
      )}

      {/* Clone count */}
      {t.clone_count > 0 && (
        <p className="text-[10px]" style={{ color: "#475569" }}>
          {t.clone_count.toLocaleString()} clones
        </p>
      )}
    </div>
  );
}
