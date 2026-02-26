"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { Settings, Loader2, Save, Palette, SlidersHorizontal, Bell } from "lucide-react";

type SettingsData = Record<string, any>;

export default function AgencySettingsPage() {
    const [settings, setSettings] = useState<SettingsData | null>(null);
    const [version, setVersion] = useState(0);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [dirty, setDirty] = useState<SettingsData>({});
    const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);

    useEffect(() => {
        apiClient.get("/agency/settings").then((res) => {
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
        const res = await apiClient.patch("/agency/settings", { settings: dirty });
        setSaving(false);
        if (res.success && res.data) {
            setSettings(res.data.settings);
            setVersion(res.data.version);
            setDirty({});
            showToast("success", "Agency settings saved successfully");
        } else {
            showToast("error", res.error || "Failed to save settings");
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0F766E]" />
            </div>
        );
    }

    if (!settings) {
        return <p className="text-slate-500 p-8">No agency found or failed to load settings.</p>;
    }

    return (
        <div className="space-y-8 pb-10">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
                        <Settings className="w-6 h-6 text-teal-700" /> Agency Settings
                    </h1>
                    <p className="text-slate-500 text-sm mt-1">Configure your agency defaults and branding &middot; Version {version}</p>
                </div>
                <button
                    onClick={handleSave}
                    disabled={saving || Object.keys(dirty).length === 0}
                    className="flex items-center gap-2 px-5 py-2.5 bg-teal-700 text-white rounded-lg hover:bg-teal-800 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-bold transition-all"
                >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save
                </button>
            </div>

            {/* Toast */}
            {toast && (
                <div className={`px-4 py-3 rounded-xl text-sm font-medium ${
                    toast.type === "success"
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-100"
                        : "bg-red-50 text-red-700 border border-red-100"
                }`}>
                    {toast.msg}
                </div>
            )}

            <div className="space-y-6">
                {/* Branding */}
                <Section title="Branding" icon={Palette}>
                    <Field label="Logo URL" type="text" value={settings.branding?.logo_url ?? ""} onChange={(v) => updateField("branding", "logo_url", v || null)} placeholder="https://example.com/logo.png" />
                    <Field label="Primary Color" type="text" value={settings.branding?.primary_color ?? ""} onChange={(v) => updateField("branding", "primary_color", v || null)} placeholder="#6D28D9" />
                </Section>

                {/* Defaults */}
                <Section title="Defaults" icon={SlidersHorizontal}>
                    <SelectField label="Default Workspace Plan" value={settings.defaults?.default_workspace_plan ?? "starter"} options={["free", "starter", "growth", "enterprise"]} onChange={(v) => updateField("defaults", "default_workspace_plan", v)} />
                    <SelectField label="Default AI Model" value={settings.defaults?.default_ai_model ?? "gemini-1.5-pro"} options={["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]} onChange={(v) => updateField("defaults", "default_ai_model", v)} />
                </Section>

                {/* Limits Override */}
                <Section title="Limits Override" icon={SlidersHorizontal}>
                    <Field label="Max Workspaces Override" type="number" value={settings.limits_override?.max_workspaces_override ?? ""} onChange={(v) => updateField("limits_override", "max_workspaces_override", v ? Number(v) : null)} placeholder="Leave empty to use plan default" />
                </Section>

                {/* Notifications */}
                <Section title="Notifications" icon={Bell}>
                    <Field label="Agency Alert Email" type="email" value={settings.notifications?.agency_alert_email ?? ""} onChange={(v) => updateField("notifications", "agency_alert_email", v || null)} placeholder="alerts@agency.com" />
                </Section>
            </div>
        </div>
    );
}

function Section({ title, icon: Icon, children }: { title: string; icon: any; children: React.ReactNode }) {
    return (
        <div className="bg-white p-6 md:p-8 rounded-xl border border-slate-100 shadow-sm">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 flex items-center gap-2 mb-5">
                <Icon className="w-4 h-4 text-teal-600" /> {title}
            </h2>
            <div className="space-y-5">{children}</div>
        </div>
    );
}

function Field({ label, type, value, onChange, ...props }: { label: string; type: string; value: any; onChange: (v: string) => void; [k: string]: any }) {
    return (
        <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">{label}</label>
            <input
                type={type}
                value={value ?? ""}
                onChange={(e) => onChange(e.target.value)}
                className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 outline-none transition-all"
                {...props}
            />
        </div>
    );
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
    return (
        <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">{label}</label>
            <select
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 outline-none transition-all"
            >
                {options.map((o) => (
                    <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1)}</option>
                ))}
            </select>
        </div>
    );
}
