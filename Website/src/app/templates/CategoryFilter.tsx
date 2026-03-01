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

  return (
    <>
      {/* Filter tabs */}
      <div className="flex flex-wrap items-center gap-2 justify-center mb-12">
        <button
          onClick={() => setActive(null)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium ${
            active === null ? "category-link-active" : "category-link"
          }`}
        >
          All
        </button>
        {categories.map((cat) => (
          <button
            key={cat.key}
            onClick={() => setActive(cat.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium ${
              active === cat.key ? "category-link-active" : "category-link"
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Template grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {filtered.map((t) => (
          <TemplateCard key={t.id} template={t} />
        ))}
      </div>

      {filtered.length === 0 && (
        <p className="text-center text-sm py-12" style={{ color: "#64748B" }}>
          No templates in this category yet. Check back soon.
        </p>
      )}
    </>
  );
}
