"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { Settings, Loader2, Save, Palette, SlidersHorizontal } from "lucide-react";

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
            showToast("success", "Agency settings saved");
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
        return <p className="text-slate-400 p-8">No agency found or failed to load settings.</p>;
    }

    return (
        <div>
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                        <Settings className="w-6 h-6" /> Agency Settings
                    </h1>
                    <p className="text-slate-500 text-sm mt-1">Version {version}</p>
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
                {/* Branding */}
                <Section title="Branding" icon={Palette}>
                    <Field label="Logo URL" type="text" value={settings.branding?.logo_url ?? ""} onChange={(v) => updateField("branding", "logo_url", v || null)} />
                    <Field label="Primary Color" type="text" value={settings.branding?.primary_color ?? ""} onChange={(v) => updateField("branding", "primary_color", v || null)} placeholder="#6D28D9" />
                </Section>

                {/* Defaults */}
                <Section title="Defaults" icon={SlidersHorizontal}>
                    <SelectField label="Default Workspace Plan" value={settings.defaults?.default_workspace_plan ?? "starter"} options={["free", "starter", "growth", "enterprise"]} onChange={(v) => updateField("defaults", "default_workspace_plan", v)} />
                    <SelectField label="Default AI Model" value={settings.defaults?.default_ai_model ?? "gemini-1.5-pro"} options={["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]} onChange={(v) => updateField("defaults", "default_ai_model", v)} />
                </Section>

                {/* Limits Override */}
                <Section title="Limits Override" icon={SlidersHorizontal}>
                    <Field label="Max Workspaces Override (leave empty for plan default)" type="number" value={settings.limits_override?.max_workspaces_override ?? ""} onChange={(v) => updateField("limits_override", "max_workspaces_override", v ? Number(v) : null)} />
                </Section>

                {/* Notifications */}
                <Section title="Notifications" icon={Settings}>
                    <Field label="Agency Alert Email" type="email" value={settings.notifications?.agency_alert_email ?? ""} onChange={(v) => updateField("notifications", "agency_alert_email", v || null)} />
                </Section>
            </div>
        </div>
    );
}

function Section({ title, icon: Icon, children }: { title: string; icon: any; children: React.ReactNode }) {
    return (
        <div className="bg-white/5 rounded-xl border border-white/10 p-6">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                <Icon className="w-5 h-5 text-violet-400" /> {title}
            </h2>
            <div className="space-y-4">{children}</div>
        </div>
    );
}

function Field({ label, type, value, onChange, ...props }: { label: string; type: string; value: any; onChange: (v: string) => void; [k: string]: any }) {
    return (
        <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">{label}</label>
            <input type={type} value={value ?? ""} onChange={(e) => onChange(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-violet-500/50" {...props} />
        </div>
    );
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
    return (
        <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">{label}</label>
            <select value={value} onChange={(e) => onChange(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-violet-500/50">
                {options.map((o) => (<option key={o} value={o}>{o}</option>))}
            </select>
        </div>
    );
}
