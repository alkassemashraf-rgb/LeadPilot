"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
    ArrowLeft,
    Loader2,
    Plus,
    CheckCircle2,
    AlertTriangle,
    Rocket,
    Star,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
    patchAdminTemplate,
    createTemplateVersion,
    publishTemplateVersion,
    getTemplateVersions,
    type AdminTemplateItem,
    type AdminTemplateVersionItem,
} from "@/lib/admin-api";
import { getAdminTemplates } from "@/lib/admin-api";

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="rounded-xl border border-border bg-card p-5 space-y-4 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{title}</h2>
            {children}
        </div>
    );
}

export default function AdminTemplateDetailPage() {
    const params = useParams();
    const templateId = params.id as string;

    const [template, setTemplate] = useState<AdminTemplateItem | null>(null);
    const [versions, setVersions] = useState<AdminTemplateVersionItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [publishing, setPublishing] = useState(false);
    const [creatingVersion, setCreatingVersion] = useState(false);
    const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

    // Editable fields
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [isFeatured, setIsFeatured] = useState(false);
    const [isActive, setIsActive] = useState(true);

    // Version creation
    const [graphJson, setGraphJson] = useState("");
    const [changelog, setChangelog] = useState("");
    const [versionErrors, setVersionErrors] = useState<any[]>([]);

    const loadTemplate = async () => {
        const res = await getAdminTemplates();
        if (res.success && res.data) {
            const found = res.data.items.find((t) => t.id === templateId);
            if (found) {
                setTemplate(found);
                setName(found.name);
                setDescription(found.description ?? "");
                setIsFeatured(found.is_featured);
                setIsActive(found.is_active);
            }
        }
    };

    const loadVersions = async () => {
        const res = await getTemplateVersions(templateId);
        if (res.success && res.data) setVersions(res.data);
    };

    useEffect(() => {
        Promise.all([loadTemplate(), loadVersions()]).then(() => setLoading(false));
    }, [templateId]);

    const showFeedback = (type: "success" | "error", message: string) => {
        setFeedback({ type, message });
        setTimeout(() => setFeedback(null), 4000);
    };

    const handleSave = async () => {
        setSaving(true);
        const res = await patchAdminTemplate(templateId, {
            name,
            description,
            is_featured: isFeatured,
            is_active: isActive,
        });
        if (res.success) {
            showFeedback("success", "Template updated.");
            loadTemplate();
        } else {
            showFeedback("error", res.error ?? "Failed to save.");
        }
        setSaving(false);
    };

    const handleCreateVersion = async () => {
        setCreatingVersion(true);
        setVersionErrors([]);
        let parsed: Record<string, any>;
        try {
            parsed = JSON.parse(graphJson);
        } catch {
            showFeedback("error", "Invalid JSON in builder graph.");
            setCreatingVersion(false);
            return;
        }
        const res = await createTemplateVersion(templateId, {
            builder_graph_json: parsed,
            changelog,
        });
        if (res.success && res.data) {
            if (res.data.valid) {
                showFeedback("success", `Version ${res.data.version_number} created.`);
                setGraphJson("");
                setChangelog("");
                loadVersions();
            } else {
                setVersionErrors(res.data.errors ?? []);
                showFeedback("error", "Graph has validation errors — version not saved.");
            }
        } else {
            showFeedback("error", res.error ?? "Failed to create version.");
        }
        setCreatingVersion(false);
    };

    const handlePublish = async () => {
        setPublishing(true);
        const res = await publishTemplateVersion(templateId);
        if (res.success && res.data) {
            showFeedback("success", `Version ${res.data.version_number} published.`);
            loadVersions();
        } else {
            showFeedback("error", res.error ?? "Nothing to publish (all versions already published).");
        }
        setPublishing(false);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (!template) {
        return (
            <div className="p-8">
                <p className="text-muted-foreground">Template not found.</p>
            </div>
        );
    }

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8">
            {/* Back */}
            <Link
                href="/admin/templates"
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground text-sm w-fit"
            >
                <ArrowLeft className="w-4 h-4" />
                Back to Templates
            </Link>

            {/* Feedback banner */}
            {feedback && (
                <div
                    className={cn(
                        "flex items-center gap-2 p-3 rounded-xl border text-sm",
                        feedback.type === "success"
                            ? "bg-teal-50 dark:bg-teal-950/30 border-teal-200 dark:border-teal-800 text-teal-700 dark:text-teal-300"
                            : "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300"
                    )}
                >
                    {feedback.type === "success" ? (
                        <CheckCircle2 className="w-4 h-4 shrink-0" />
                    ) : (
                        <AlertTriangle className="w-4 h-4 shrink-0" />
                    )}
                    {feedback.message}
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left: Metadata */}
                <div className="lg:col-span-1 space-y-4">
                    <SectionCard title="Template Info">
                        <div className="space-y-1">
                            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                Slug
                            </label>
                            <p className="text-sm font-mono text-foreground">{template.slug}</p>
                        </div>

                        {[
                            { label: "Name", value: name, set: setName },
                        ].map(({ label, value, set }) => (
                            <div key={label} className="space-y-1">
                                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                    {label}
                                </label>
                                <input
                                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                                    value={value}
                                    onChange={(e) => set(e.target.value)}
                                />
                            </div>
                        ))}

                        <div className="space-y-1">
                            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                Description
                            </label>
                            <textarea
                                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-teal-500 min-h-[70px]"
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                            />
                        </div>

                        <div className="flex items-center gap-4 pt-1">
                            <label className="flex items-center gap-2 text-sm cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={isFeatured}
                                    onChange={(e) => setIsFeatured(e.target.checked)}
                                    className="accent-teal-600"
                                />
                                <Star className="w-3.5 h-3.5 text-amber-500 fill-current" />
                                Featured
                            </label>
                            <label className="flex items-center gap-2 text-sm cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={isActive}
                                    onChange={(e) => setIsActive(e.target.checked)}
                                    className="accent-teal-600"
                                />
                                Active
                            </label>
                        </div>

                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium disabled:opacity-50 transition-colors"
                        >
                            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                            Save Changes
                        </button>
                    </SectionCard>
                </div>

                {/* Right: Versions */}
                <div className="lg:col-span-2 space-y-4">
                    <SectionCard title="Versions">
                        {/* Publish latest */}
                        <button
                            onClick={handlePublish}
                            disabled={publishing}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium disabled:opacity-50 transition-colors"
                        >
                            {publishing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Rocket className="w-4 h-4" />}
                            Publish Latest Draft
                        </button>

                        {versions.length === 0 ? (
                            <p className="text-sm text-muted-foreground">No versions yet.</p>
                        ) : (
                            <div className="rounded-lg border border-border divide-y divide-border overflow-hidden">
                                {versions.map((v) => (
                                    <div key={v.id} className="flex items-center justify-between px-4 py-3">
                                        <div>
                                            <p className="text-sm font-medium">v{v.version_number}</p>
                                            {v.changelog && (
                                                <p className="text-xs text-muted-foreground">{v.changelog}</p>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-2">
                                            {v.is_published ? (
                                                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-teal-100 dark:bg-teal-900 text-teal-700 dark:text-teal-300 uppercase tracking-wide">
                                                    Published
                                                </span>
                                            ) : (
                                                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-muted text-muted-foreground uppercase tracking-wide">
                                                    Draft
                                                </span>
                                            )}
                                            <span className="text-xs text-muted-foreground">
                                                {new Date(v.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </SectionCard>

                    <SectionCard title="Create New Version">
                        <div className="space-y-3">
                            <div className="space-y-1">
                                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                    Builder Graph JSON
                                </label>
                                <textarea
                                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono resize-y focus:outline-none focus:ring-2 focus:ring-teal-500 min-h-[200px]"
                                    placeholder='{"nodes": [...], "edges": [...]}'
                                    value={graphJson}
                                    onChange={(e) => setGraphJson(e.target.value)}
                                />
                            </div>

                            {versionErrors.length > 0 && (
                                <div className="space-y-1 p-3 rounded-lg border border-red-200 bg-red-50 dark:bg-red-950/20 text-xs text-red-700 dark:text-red-300">
                                    <p className="font-semibold">Validation errors:</p>
                                    {versionErrors.map((e: any, i: number) => (
                                        <p key={i}>{e.node_id}: {e.message}</p>
                                    ))}
                                </div>
                            )}

                            <div className="space-y-1">
                                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                    Changelog (optional)
                                </label>
                                <input
                                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                                    placeholder="What changed in this version..."
                                    value={changelog}
                                    onChange={(e) => setChangelog(e.target.value)}
                                />
                            </div>

                            <button
                                onClick={handleCreateVersion}
                                disabled={creatingVersion || !graphJson.trim()}
                                className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border hover:border-teal-400 text-sm font-medium text-foreground disabled:opacity-50 transition-colors"
                            >
                                {creatingVersion ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                                Create Draft Version
                            </button>
                        </div>
                    </SectionCard>
                </div>
            </div>
        </div>
    );
}
