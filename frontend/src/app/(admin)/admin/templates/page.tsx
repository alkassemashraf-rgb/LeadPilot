"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Plus, Loader2, Star, CheckCircle2, XCircle, LayoutTemplate } from "lucide-react";
import { cn } from "@/lib/utils";
import {
    getAdminTemplates,
    createAdminTemplate,
    type AdminTemplateItem,
} from "@/lib/admin-api";

function StatusBadge({ active }: { active: boolean }) {
    return (
        <span
            className={cn(
                "inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide",
                active
                    ? "bg-teal-100 dark:bg-teal-900 text-teal-700 dark:text-teal-300"
                    : "bg-muted text-muted-foreground"
            )}
        >
            {active ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
            {active ? "Active" : "Inactive"}
        </span>
    );
}

export default function AdminTemplatesPage() {
    const [templates, setTemplates] = useState<AdminTemplateItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [creating, setCreating] = useState(false);

    // Create form state
    const [slug, setSlug] = useState("");
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [category, setCategory] = useState("general");
    const [platforms, setPlatforms] = useState("");
    const [createError, setCreateError] = useState("");

    const load = () => {
        setLoading(true);
        getAdminTemplates().then((res) => {
            if (res.success && res.data) setTemplates(res.data.items);
            setLoading(false);
        });
    };

    useEffect(() => { load(); }, []);

    const handleCreate = async () => {
        setCreating(true);
        setCreateError("");
        const res = await createAdminTemplate({
            slug,
            name,
            description,
            category,
            platforms: platforms.split(",").map((p) => p.trim()).filter(Boolean),
        });
        if (res.success) {
            setShowCreate(false);
            setSlug(""); setName(""); setDescription(""); setCategory("general"); setPlatforms("");
            load();
        } else {
            setCreateError(res.error ?? "Failed to create template.");
        }
        setCreating(false);
    };

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <LayoutTemplate className="w-6 h-6 text-teal-600" />
                    <div>
                        <h1 className="text-2xl font-bold">Templates</h1>
                        <p className="text-sm text-muted-foreground">Manage the automation template catalog.</p>
                    </div>
                </div>
                <button
                    onClick={() => setShowCreate(true)}
                    className="flex items-center gap-2 bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-sm"
                >
                    <Plus className="w-4 h-4" />
                    New Template
                </button>
            </div>

            {/* Create modal */}
            {showCreate && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div className="bg-background rounded-2xl border border-border shadow-xl w-full max-w-md p-6 space-y-4">
                        <h2 className="text-lg font-bold">Create Template</h2>

                        {[
                            { label: "Slug", value: slug, set: setSlug, placeholder: "welcome-bot", required: true },
                            { label: "Name", value: name, set: setName, placeholder: "Welcome Bot", required: true },
                        ].map(({ label, value, set, placeholder, required }) => (
                            <div key={label} className="space-y-1">
                                <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                    {label}{required && <span className="text-red-500 ml-0.5">*</span>}
                                </label>
                                <input
                                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                                    placeholder={placeholder}
                                    value={value}
                                    onChange={(e) => set(e.target.value)}
                                />
                            </div>
                        ))}

                        <div className="space-y-1">
                            <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                Description
                            </label>
                            <textarea
                                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-teal-500 min-h-[60px]"
                                placeholder="Describe what this template does..."
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1">
                                <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                    Category
                                </label>
                                <select
                                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                                    value={category}
                                    onChange={(e) => setCategory(e.target.value)}
                                >
                                    {["general", "lead_generation", "customer_support", "sales", "onboarding"].map((c) => (
                                        <option key={c} value={c}>{c}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                    Platforms (comma-sep)
                                </label>
                                <input
                                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                                    placeholder="whatsapp, meta"
                                    value={platforms}
                                    onChange={(e) => setPlatforms(e.target.value)}
                                />
                            </div>
                        </div>

                        {createError && (
                            <p className="text-xs text-red-600">{createError}</p>
                        )}

                        <div className="flex gap-2 pt-2">
                            <button
                                onClick={() => { setShowCreate(false); setCreateError(""); }}
                                className="flex-1 py-2 rounded-lg border border-border text-sm font-medium hover:bg-muted transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleCreate}
                                disabled={creating || !slug || !name}
                                className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium disabled:opacity-50 transition-colors"
                            >
                                {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                                Create
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Templates table */}
            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
                </div>
            ) : templates.length === 0 ? (
                <div className="text-center py-20 border-2 border-dashed border-border rounded-2xl text-muted-foreground">
                    No templates yet. Create one to get started.
                </div>
            ) : (
                <div className="rounded-xl border border-border overflow-hidden">
                    <table className="w-full text-sm">
                        <thead className="bg-muted/50 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                            <tr>
                                <th className="px-4 py-3 text-left">Name</th>
                                <th className="px-4 py-3 text-left">Slug</th>
                                <th className="px-4 py-3 text-left">Category</th>
                                <th className="px-4 py-3 text-left">Status</th>
                                <th className="px-4 py-3 text-left">Featured</th>
                                <th className="px-4 py-3 text-left">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {templates.map((t) => (
                                <tr key={t.id} className="hover:bg-muted/30 transition-colors">
                                    <td className="px-4 py-3 font-medium">{t.name}</td>
                                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{t.slug}</td>
                                    <td className="px-4 py-3 text-muted-foreground">{t.category}</td>
                                    <td className="px-4 py-3"><StatusBadge active={t.is_active} /></td>
                                    <td className="px-4 py-3">
                                        {t.is_featured && <Star className="w-4 h-4 text-amber-500 fill-current" />}
                                    </td>
                                    <td className="px-4 py-3">
                                        <Link
                                            href={`/admin/templates/${t.id}`}
                                            className="text-teal-600 hover:text-teal-700 font-medium"
                                        >
                                            Manage →
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
