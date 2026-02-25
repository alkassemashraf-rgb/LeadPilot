"use client";

import { useEffect, useState, useCallback } from "react";
import { adminApi, ModuleConfig, MODULE_LABELS, LOCKED_MODULES } from "@/lib/admin-api";
import { Lock, Loader2, ToggleLeft, ToggleRight, AlertCircle } from "lucide-react";

function ModuleRow({
    module,
    onToggle,
    toggling,
}: {
    module: ModuleConfig;
    onToggle: (name: string, enabled: boolean) => void;
    toggling: string | null;
}) {
    const isLocked = LOCKED_MODULES.has(module.module_name);
    const isBusy = toggling === module.module_name;
    const label = MODULE_LABELS[module.module_name] || module.module_name;

    const descMap: Record<string, string> = {
        auth: "JWT authentication, login & signup flows",
        email_engine: "Transactional email delivery via SMTP/SendGrid",
        email_verification: "Email address verification gate on sign-up",
        prompt_studio: "AI prompt configuration and version history",
        knowledge_files: "Upload and manage RAG knowledge documents",
        integrations_hub: "Integration management hub",
        integrations_connect: "CRM and messaging platform OAuth connect",
        webhooks_ingestion: "Inbound webhook handling (WhatsApp, Meta)",
        runtime_engine: "Conversational AI reply generation engine",
        dispatch_engine: "Outbound message scheduling and dispatch",
        inbox: "Conversation inbox and message threading",
        zoho_sync: "Zoho CRM lead sync and field mapping",
        analytics: "Analytics dashboards and time-series charts",
        diagnostics: "Internal diagnostic endpoints",
        admin_portal: "SuperAdmin control panel — always active",
    };

    return (
        <div
            className={`flex items-center gap-4 p-4 rounded-xl border transition-all ${module.is_enabled
                    ? "bg-white/5 border-white/10"
                    : "bg-red-500/5 border-red-500/20 opacity-75"
                }`}
        >
            {/* Status indicator */}
            <div
                className={`w-2 h-2 rounded-full flex-shrink-0 ${module.is_enabled ? "bg-emerald-400" : "bg-red-400"
                    }`}
            />

            {/* Module info */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-white">{label}</p>
                    {isLocked && (
                        <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-amber-400 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded">
                            <Lock className="w-2.5 h-2.5" />
                            locked
                        </span>
                    )}
                </div>
                <p className="text-xs text-slate-500 mt-0.5 truncate">
                    {descMap[module.module_name]}
                </p>
                <p className="text-[10px] text-slate-600 font-mono mt-1">{module.module_name}</p>
            </div>

            {/* Toggle */}
            <button
                onClick={() => !isLocked && !isBusy && onToggle(module.module_name, !module.is_enabled)}
                disabled={isLocked || isBusy}
                className={`flex-shrink-0 p-1 rounded-lg transition-all ${isLocked
                        ? "cursor-not-allowed opacity-40"
                        : isBusy
                            ? "cursor-wait opacity-60"
                            : "cursor-pointer hover:bg-white/10"
                    }`}
                title={isLocked ? "This module cannot be disabled" : module.is_enabled ? "Disable module" : "Enable module"}
            >
                {isBusy ? (
                    <Loader2 className="w-6 h-6 text-violet-400 animate-spin" />
                ) : module.is_enabled ? (
                    <ToggleRight className="w-8 h-8 text-emerald-400" />
                ) : (
                    <ToggleLeft className="w-8 h-8 text-slate-500" />
                )}
            </button>
        </div>
    );
}

export default function ModulesPage() {
    const [modules, setModules] = useState<ModuleConfig[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [toggling, setToggling] = useState<string | null>(null);
    const [toast, setToast] = useState<{ text: string; ok: boolean } | null>(null);

    const showToast = useCallback((text: string, ok: boolean) => {
        setToast({ text, ok });
        setTimeout(() => setToast(null), 3500);
    }, []);

    const loadModules = useCallback(async () => {
        const res = await adminApi.getModules();
        if (res.success && res.data) {
            setModules(res.data);
        } else {
            setError(res.error || "Failed to load modules");
        }
        setLoading(false);
    }, []);

    useEffect(() => {
        loadModules();
    }, [loadModules]);

    const handleToggle = async (name: string, enabled: boolean) => {
        setToggling(name);
        const res = await adminApi.toggleModule(name, enabled);
        if (res.success && res.data) {
            setModules((prev) =>
                prev.map((m) =>
                    m.module_name === name ? { ...m, is_enabled: res.data!.is_enabled } : m
                )
            );
            showToast(
                `${MODULE_LABELS[name] || name} ${enabled ? "enabled" : "disabled"}`,
                true
            );
        } else {
            showToast(res.error || "Toggle failed", false);
        }
        setToggling(null);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-6 h-6 text-violet-400 animate-spin" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-400 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
            </div>
        );
    }

    const enabledCount = modules.filter((m) => m.is_enabled).length;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Module Toggles</h1>
                    <p className="text-slate-400 text-sm mt-1">
                        {enabledCount} of {modules.length} modules enabled. Changes take effect within 15 seconds (cache TTL).
                    </p>
                </div>
            </div>

            {/* Warning banner */}
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex gap-3">
                <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-amber-300">
                    Disabling a module will return <strong>403 MODULE_DISABLED</strong> on all related API endpoints. This affects all users and workspaces immediately.
                </p>
            </div>

            {/* Module list */}
            <div className="space-y-2">
                {modules.map((mod) => (
                    <ModuleRow
                        key={mod.module_name}
                        module={mod}
                        onToggle={handleToggle}
                        toggling={toggling}
                    />
                ))}
            </div>

            {/* Toast */}
            {toast && (
                <div
                    className={`fixed bottom-6 right-6 px-4 py-3 rounded-xl shadow-xl text-sm font-medium transition-all z-50 ${toast.ok
                            ? "bg-emerald-500 text-white"
                            : "bg-red-500 text-white"
                        }`}
                >
                    {toast.text}
                </div>
            )}
        </div>
    );
}
