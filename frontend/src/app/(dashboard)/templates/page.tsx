"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
    LayoutTemplate,
    Loader2,
    Search,
    Star,
    ArrowRight,
    Zap,
    CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { listTemplates, cloneTemplate, type TemplateListItem } from "@/lib/templates-api";

const CATEGORY_LABELS: Record<string, string> = {
    lead_generation: "Lead Generation",
    customer_support: "Customer Support",
    sales: "Sales",
    onboarding: "Onboarding",
    general: "General",
};

const PLATFORM_LABELS: Record<string, string> = {
    whatsapp: "WhatsApp",
    meta: "Meta",
};

function TemplateBadge({ text, color = "default" }: { text: string; color?: "teal" | "blue" | "default" }) {
    return (
        <span
            className={cn(
                "text-[11px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full",
                color === "teal" && "bg-teal-100 dark:bg-teal-900 text-teal-700 dark:text-teal-300",
                color === "blue" && "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300",
                color === "default" && "bg-muted text-muted-foreground"
            )}
        >
            {text}
        </span>
    );
}

function TemplateCard({ template }: { template: TemplateListItem }) {
    const router = useRouter();
    const [cloning, setCloning] = useState(false);
    const [cloned, setCloned] = useState(false);

    const handleUse = async () => {
        setCloning(true);
        const res = await cloneTemplate(template.slug);
        if (res.success && res.data) {
            setCloned(true);
            setTimeout(() => router.push(res.data!.redirect_path), 800);
        }
        setCloning(false);
    };

    return (
        <div className="flex flex-col rounded-2xl border border-border bg-card shadow-sm hover:shadow-md hover:border-teal-200 transition-all overflow-hidden group">
            {/* Featured badge */}
            {template.is_featured && (
                <div className="flex items-center gap-1 px-4 py-2 bg-amber-50 dark:bg-amber-950/30 border-b border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-300 text-xs font-semibold">
                    <Star className="w-3 h-3 fill-current" />
                    Featured
                </div>
            )}

            <div className="flex flex-col flex-1 p-5 space-y-3">
                {/* Header */}
                <div className="space-y-1.5">
                    <div className="flex items-start justify-between gap-2">
                        <h3 className="font-semibold text-foreground leading-tight">{template.name}</h3>
                    </div>
                    {template.description && (
                        <p className="text-sm text-muted-foreground line-clamp-2">{template.description}</p>
                    )}
                </div>

                {/* Tags */}
                <div className="flex flex-wrap gap-1.5">
                    {template.category && (
                        <TemplateBadge
                            text={CATEGORY_LABELS[template.category] ?? template.category}
                            color="teal"
                        />
                    )}
                    {template.platforms.map((p) => (
                        <TemplateBadge key={p} text={PLATFORM_LABELS[p] ?? p} color="blue" />
                    ))}
                    {template.industry_tags.slice(0, 2).map((tag) => (
                        <TemplateBadge key={tag} text={tag} />
                    ))}
                </div>

                {template.required_integrations.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                        Requires: {template.required_integrations.join(", ")}
                    </p>
                )}
            </div>

            {/* Footer */}
            <div className="flex items-center gap-2 px-5 py-3 border-t border-border bg-muted/30">
                <Link
                    href={`/templates/${template.slug}`}
                    className="flex-1 text-center text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                    Preview
                </Link>
                <button
                    onClick={handleUse}
                    disabled={cloning || cloned}
                    className={cn(
                        "flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-sm font-medium transition-colors",
                        cloned
                            ? "bg-teal-100 dark:bg-teal-900 text-teal-700 dark:text-teal-300"
                            : "bg-teal-600 hover:bg-teal-700 text-white disabled:opacity-50"
                    )}
                >
                    {cloning ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : cloned ? (
                        <CheckCircle2 className="w-3.5 h-3.5" />
                    ) : (
                        <ArrowRight className="w-3.5 h-3.5" />
                    )}
                    {cloned ? "Opening…" : "Use Template"}
                </button>
            </div>
        </div>
    );
}

export default function TemplatesPage() {
    const [templates, setTemplates] = useState<TemplateListItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [categoryFilter, setCategoryFilter] = useState("");

    useEffect(() => {
        listTemplates().then((res) => {
            if (res.success && res.data) setTemplates(res.data);
            setLoading(false);
        });
    }, []);

    const featured = templates.filter((t) => t.is_featured);
    const filtered = templates.filter((t) => {
        const matchSearch =
            !search ||
            t.name.toLowerCase().includes(search.toLowerCase()) ||
            (t.description ?? "").toLowerCase().includes(search.toLowerCase());
        const matchCat = !categoryFilter || t.category === categoryFilter;
        return matchSearch && matchCat;
    });

    const categories = Array.from(new Set(templates.map((t) => t.category).filter(Boolean)));

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8">
            {/* Header */}
            <div className="space-y-1">
                <div className="flex items-center gap-2">
                    <LayoutTemplate className="w-6 h-6 text-teal-600" />
                    <h1 className="text-3xl font-bold tracking-tight">Templates</h1>
                </div>
                <p className="text-muted-foreground">
                    Pre-built automation flows. Clone one to get started instantly.
                </p>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-3 flex-wrap">
                <div className="relative flex-1 max-w-xs">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search templates…"
                        className="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                    <button
                        onClick={() => setCategoryFilter("")}
                        className={cn(
                            "px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors",
                            !categoryFilter
                                ? "bg-teal-600 text-white border-teal-600"
                                : "border-border hover:border-teal-400 text-foreground"
                        )}
                    >
                        All
                    </button>
                    {categories.map((cat) => (
                        <button
                            key={cat}
                            onClick={() => setCategoryFilter(cat === categoryFilter ? "" : cat)}
                            className={cn(
                                "px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors",
                                categoryFilter === cat
                                    ? "bg-teal-600 text-white border-teal-600"
                                    : "border-border hover:border-teal-400 text-foreground"
                            )}
                        >
                            {CATEGORY_LABELS[cat] ?? cat}
                        </button>
                    ))}
                </div>
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
                </div>
            ) : templates.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 border-2 border-dashed border-border rounded-2xl text-center space-y-3">
                    <Zap className="w-12 h-12 text-muted-foreground/30" />
                    <div>
                        <p className="font-semibold">No templates yet</p>
                        <p className="text-sm text-muted-foreground">
                            Check back soon — templates are published by your account admin.
                        </p>
                    </div>
                </div>
            ) : (
                <div className="space-y-8">
                    {/* Featured section */}
                    {featured.length > 0 && !search && !categoryFilter && (
                        <div className="space-y-4">
                            <h2 className="text-lg font-semibold flex items-center gap-2">
                                <Star className="w-4 h-4 text-amber-500 fill-current" />
                                Featured
                            </h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {featured.map((t) => (
                                    <TemplateCard key={t.id} template={t} />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* All templates */}
                    <div className="space-y-4">
                        {(search || categoryFilter) ? null : (
                            <h2 className="text-lg font-semibold">All Templates</h2>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {filtered.map((t) => (
                                <TemplateCard key={t.id} template={t} />
                            ))}
                        </div>
                        {filtered.length === 0 && (
                            <div className="text-center py-12 text-muted-foreground">
                                No templates match your search.
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
