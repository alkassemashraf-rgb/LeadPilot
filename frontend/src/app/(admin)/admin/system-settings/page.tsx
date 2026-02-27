"use client";

import { useEffect, useState } from "react";
import { getSystemSettings, patchSystemSettings } from "@/lib/admin-api";
import { useCatalog, type CatalogEntry, type PlanCatalogEntry } from "@/lib/catalog";
import {
    Settings,
    Loader2,
    Save,
    AlertTriangle,
    ToggleLeft,
    Globe,
} from "lucide-react";

type SettingsData = Record<string, any>;

export default function SystemSettingsPage() {
    const { data: plans } = useCatalog<PlanCatalogEntry[]>("plans");
    const [settings, setSettings] = useState<SettingsData | null>(null);
    const [version, setVersion] = useState(0);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [dirty, setDirty] = useState<SettingsData>({});
    const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);

    useEffect(() => {
        getSystemSettings().then((res) => {
            if (res.success && res.data) {
                setSettings(res.data.settings);
                setVersion(res.data.version);
            }
            setLoading(false);
        });
    }, []);

    const showToast = (type: "success" | "error", msg: string) => {
        setToast({ type, msg });
        setTimeout(() => setToast(null), 3000);
    };

    const updateField = (key: string, value: any) => {
        setSettings((prev) => (prev ? { ...prev, [key]: value } : prev));
        setDirty((prev) => ({ ...prev, [key]: value }));
    };

    const updateNested = (section: string, key: string, value: any) => {
        setSettings((prev) => {
            if (!prev) return prev;
            return { ...prev, [section]: { ...prev[section], [key]: value } };
        });
        setDirty((prev) => ({
            ...prev,
            [section]: { ...(prev[section] || {}), [key]: value },
        }));
    };

    const handleSave = async () => {
        if (Object.keys(dirty).length === 0) return;
        setSaving(true);
        const res = await patchSystemSettings(dirty);
        setSaving(false);
        if (res.success && res.data) {
            setSettings(res.data.settings);
            setVersion(res.data.version);
            setDirty({});
            showToast("success", "System settings saved");
        } else {
            showToast("error", res.error || "Failed to save");
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
            </div>
        );
    }

    if (!settings) {
        return <p className="text-slate-400 p-8">Failed to load system settings.</p>;
    }

    const modules = settings.global_modules || {};

    return (
        <div className="max-w-3xl">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                        <Settings className="w-6 h-6" /> System Settings
                    </h1>
                    <p className="text-slate-500 text-sm mt-1">Global configuration &middot; Version {version}</p>
                </div>
                <button
                    onClick={handleSave}
                    disabled={saving || Object.keys(dirty).length === 0}
                    className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save
                </button>
            </div>

            {toast && (
                <div className={`mb-4 px-4 py-2 rounded-lg text-sm font-medium ${toast.type === "success" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`}>
                    {toast.msg}
                </div>
            )}

            <div className="space-y-6">
                {/* Maintenance Mode */}
                <div className={`rounded-xl border p-6 ${settings.maintenance_mode ? "bg-red-500/5 border-red-500/30" : "bg-white/5 border-white/10"}`}>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <AlertTriangle className={`w-5 h-5 ${settings.maintenance_mode ? "text-red-400" : "text-slate-400"}`} />
                            <div>
                                <h2 className="text-lg font-semibold text-white">Maintenance Mode</h2>
                                <p className="text-sm text-slate-400">Blocks all non-admin API requests when enabled</p>
                            </div>
                        </div>
                        <Toggle value={settings.maintenance_mode} onChange={(v) => updateField("maintenance_mode", v)} />
                    </div>
                    {settings.maintenance_mode && (
                        <div className="mt-3 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-300">
                            Maintenance mode is ACTIVE. All product API endpoints are returning 503.
                        </div>
                    )}
                </div>

                {/* Global Modules */}
                <div className="bg-white/5 rounded-xl border border-white/10 p-6">
                    <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                        <ToggleLeft className="w-5 h-5 text-violet-400" /> Global Modules
                    </h2>
                    <div className="space-y-3">
                        {Object.entries(modules).map(([key, enabled]) => (
                            <div key={key} className="flex items-center justify-between py-1">
                                <span className="text-sm text-slate-300 font-medium">{formatModuleName(key)}</span>
                                <Toggle value={enabled as boolean} onChange={(v) => updateNested("global_modules", key, v)} />
                            </div>
                        ))}
                    </div>
                </div>

                {/* Defaults */}
                <div className="bg-white/5 rounded-xl border border-white/10 p-6">
                    <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                        <Globe className="w-5 h-5 text-violet-400" /> Defaults
                    </h2>
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">Default Workspace Plan</label>
                            <select
                                value={settings.defaults?.default_workspace_plan ?? "starter"}
                                onChange={(e) => updateNested("defaults", "default_workspace_plan", e.target.value)}
                                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                            >
                                {(plans || []).map((p) => (
                                    <option key={p.name} value={p.name}>{p.display_name}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                </div>

                {/* AI Provider Priority */}
                <div className="bg-white/5 rounded-xl border border-white/10 p-6">
                    <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                        <Settings className="w-5 h-5 text-violet-400" /> AI Provider Priority
                    </h2>
                    <p className="text-sm text-slate-400 mb-3">Comma-separated list of AI providers in priority order</p>
                    <input
                        type="text"
                        value={(settings.ai_provider_priority || []).join(", ")}
                        onChange={(e) => updateField("ai_provider_priority", e.target.value.split(",").map((s: string) => s.trim()).filter(Boolean))}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                        placeholder="gemini, openai"
                    />
                </div>
            </div>
        </div>
    );
}

function formatModuleName(key: string): string {
    return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
    return (
        <button
            type="button"
            onClick={() => onChange(!value)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${value ? "bg-violet-600" : "bg-white/10"}`}
        >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${value ? "translate-x-6" : "translate-x-1"}`} />
        </button>
    );
}
