"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import {
    Settings,
    Globe,
    MessageSquare,
    Cpu,
    Zap,
    Bell,
    Loader2,
    Save,
} from "lucide-react";

type SettingsData = Record<string, any>;

const TABS = [
    { key: "general", label: "General", icon: Globe },
    { key: "messaging", label: "Messaging", icon: MessageSquare },
    { key: "ai", label: "AI", icon: Cpu },
    { key: "automation", label: "Automation", icon: Zap },
    { key: "notifications", label: "Notifications", icon: Bell },
] as const;

export default function WorkspaceSettingsPage() {
    const [settings, setSettings] = useState<SettingsData | null>(null);
    const [version, setVersion] = useState(0);
    const [activeTab, setActiveTab] = useState<string>("general");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [dirty, setDirty] = useState<SettingsData>({});
    const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);

    useEffect(() => {
        apiClient.get("/settings/workspace").then((res) => {
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

    const updateField = (section: string, key: string, value: any) => {
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
        const res = await apiClient.patch("/settings/workspace", { settings: dirty });
        setSaving(false);
        if (res.success && res.data) {
            setSettings(res.data.settings);
            setVersion(res.data.version);
            setDirty({});
            showToast("success", "Settings saved");
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
        return <p className="text-slate-400 p-8">Failed to load settings.</p>;
    }

    const s = settings[activeTab] || {};

    return (
        <div>
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                        <Settings className="w-6 h-6" /> Workspace Settings
                    </h1>
                    <p className="text-slate-500 text-sm mt-1">Version {version}</p>
                </div>
                <button
                    onClick={handleSave}
                    disabled={saving || Object.keys(dirty).length === 0}
                    className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save Changes
                </button>
            </div>

            {toast && (
                <div className={`mb-4 px-4 py-2 rounded-lg text-sm font-medium ${toast.type === "success" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`}>
                    {toast.msg}
                </div>
            )}

            {/* Tabs */}
            <div className="flex gap-1 border-b border-white/10 mb-6">
                {TABS.map((tab) => (
                    <button
                        key={tab.key}
                        onClick={() => setActiveTab(tab.key)}
                        className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${activeTab === tab.key ? "border-violet-500 text-violet-300" : "border-transparent text-slate-400 hover:text-white"}`}
                    >
                        <tab.icon className="w-4 h-4" />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Fields */}
            <div className="bg-white/5 rounded-xl border border-white/10 p-6 space-y-5">
                {activeTab === "general" && (
                    <>
                        <Field label="Name Override" type="text" value={s.name_override ?? ""} onChange={(v) => updateField("general", "name_override", v || null)} />
                        <Field label="Logo URL" type="text" value={s.logo_url ?? ""} onChange={(v) => updateField("general", "logo_url", v || null)} />
                        <SelectField label="Timezone" value={s.timezone} options={["UTC", "US/Eastern", "US/Pacific", "Europe/London", "Asia/Dubai", "Asia/Tokyo"]} onChange={(v) => updateField("general", "timezone", v)} />
                        <SelectField label="Default Language" value={s.default_language} options={["en", "ar", "es", "fr", "de", "zh"]} onChange={(v) => updateField("general", "default_language", v)} />
                    </>
                )}
                {activeTab === "messaging" && (
                    <>
                        <Field label="Default Reply Delay (seconds)" type="number" value={s.default_reply_delay_seconds} onChange={(v) => updateField("messaging", "default_reply_delay_seconds", Number(v))} />
                        <Toggle label="Fallback Message Enabled" value={s.fallback_message_enabled} onChange={(v) => updateField("messaging", "fallback_message_enabled", v)} />
                        <Toggle label="Auto-Retry Failed Dispatch" value={s.auto_retry_failed_dispatch} onChange={(v) => updateField("messaging", "auto_retry_failed_dispatch", v)} />
                    </>
                )}
                {activeTab === "ai" && (
                    <>
                        <SelectField label="Default Model" value={s.default_model} options={["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]} onChange={(v) => updateField("ai", "default_model", v)} />
                        <Field label="Temperature" type="number" value={s.temperature} step="0.1" min="0" max="2" onChange={(v) => updateField("ai", "temperature", Number(v))} />
                        <Field label="Max Tokens" type="number" value={s.max_tokens} onChange={(v) => updateField("ai", "max_tokens", Number(v))} />
                        <Toggle label="Guardrails Enabled" value={s.guardrails_enabled} onChange={(v) => updateField("ai", "guardrails_enabled", v)} />
                    </>
                )}
                {activeTab === "automation" && (
                    <>
                        <Toggle label="Auto-Publish" value={s.auto_publish} onChange={(v) => updateField("automation", "auto_publish", v)} />
                        <Field label="Draft Expiry (days)" type="number" value={s.draft_expiry_days} onChange={(v) => updateField("automation", "draft_expiry_days", Number(v))} />
                    </>
                )}
                {activeTab === "notifications" && (
                    <>
                        <Toggle label="Email Notifications Enabled" value={s.email_notifications_enabled} onChange={(v) => updateField("notifications", "email_notifications_enabled", v)} />
                        <Field label="Webhook URL" type="text" value={s.webhook_url ?? ""} onChange={(v) => updateField("notifications", "webhook_url", v || null)} />
                    </>
                )}
            </div>
        </div>
    );
}

/* ─── Shared form components ─────────────────────────────────────────────── */

function Field({ label, type, value, onChange, ...props }: { label: string; type: string; value: any; onChange: (v: string) => void; [k: string]: any }) {
    return (
        <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">{label}</label>
            <input
                type={type}
                value={value ?? ""}
                onChange={(e) => onChange(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                {...props}
            />
        </div>
    );
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
    return (
        <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">{label}</label>
            <select
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            >
                {options.map((o) => (
                    <option key={o} value={o}>{o}</option>
                ))}
            </select>
        </div>
    );
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
    return (
        <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-300">{label}</span>
            <button
                type="button"
                onClick={() => onChange(!value)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${value ? "bg-violet-600" : "bg-white/10"}`}
            >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${value ? "translate-x-6" : "translate-x-1"}`} />
            </button>
        </div>
    );
}
