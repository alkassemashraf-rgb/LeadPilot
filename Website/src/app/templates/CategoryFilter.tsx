"use client";

import { useState } from "react";
import type { CatalogTemplate, CatalogEnum } from "@/lib/api";
import TemplateCard from "./TemplateCard";

interface Props {
  templates: CatalogTemplate[];
  categories: CatalogEnum[];
}

export default function CategoryFilter({ templates, categories }: Props) {
  const [active, setActive] = useState<string | null>(null);

  const filtered = active
    ? templates.filter((t) => t.category === active)
    : templates;

  // Count per category
  const countMap: Record<string, number> = {};
  for (const t of templates) {
    countMap[t.category] = (countMap[t.category] ?? 0) + 1;
  }

  return (
    <>
      {/* Filter tabs */}
      <div className="flex flex-wrap items-center gap-2 justify-center mb-14">
        <button
          onClick={() => setActive(null)}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
            active === null ? "category-link-active" : "category-link"
          }`}
        >
          All
          <span
            className="text-[10px] font-bold px-1.5 py-0.5 rounded-md"
            style={{
              background: active === null ? "rgba(20,184,166,0.2)" : "rgba(255,255,255,0.06)",
              color: active === null ? "#14B8A6" : "#475569",
            }}
          >
            {templates.length}
          </span>
        </button>
        {categories.map((cat) => (
          <button
            key={cat.key}
            onClick={() => setActive(cat.key)}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
              active === cat.key ? "category-link-active" : "category-link"
            }`}
          >
            {cat.label}
            <span
              className="text-[10px] font-bold px-1.5 py-0.5 rounded-md"
              style={{
                background: active === cat.key ? "rgba(20,184,166,0.2)" : "rgba(255,255,255,0.06)",
                color: active === cat.key ? "#14B8A6" : "#475569",
              }}
            >
              {countMap[cat.key] ?? 0}
            </span>
          </button>
        ))}
      </div>

      {/* Template grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {filtered.map((t) => (
          <TemplateCard key={t.id} template={t} />
        ))}
      </div>

      {filtered.length === 0 && (
        <p className="text-center text-sm py-16" style={{ color: "#64748B" }}>
          No templates in this category yet. Check back soon.
        </p>
      )}
    </>
  );
}
