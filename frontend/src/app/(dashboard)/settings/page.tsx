"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { useLookups } from "@/lib/lookups";
import {
    Settings,
    Globe,
    MessageSquare,
    Cpu,
    Zap,
    Bell,
    Loader2,
    Save,
    User,
    ShieldCheck,
} from "lucide-react";

type SettingsData = Record<string, any>;

interface UserProfile {
    id: string;
    email: string;
    full_name: string | null;
    is_active: boolean;
    is_superuser: boolean;
    email_verified_at: string | null;
    requires_email_verification: boolean;
}

type Section = "profile" | "workspace";

const TABS = [
    { key: "general", label: "General", icon: Globe },
    { key: "messaging", label: "Messaging", icon: MessageSquare },
    { key: "ai", label: "AI", icon: Cpu },
    { key: "automation", label: "Automation", icon: Zap },
    { key: "notifications", label: "Notifications", icon: Bell },
] as const;

export default function SettingsPage() {
    const lookups = useLookups();

    // Profile state
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [profileName, setProfileName] = useState("");
    const [savingProfile, setSavingProfile] = useState(false);

    // Workspace state
    const [settings, setSettings] = useState<SettingsData | null>(null);
    const [version, setVersion] = useState(0);
    const [activeTab, setActiveTab] = useState<string>("general");
    const [saving, setSaving] = useState(false);
    const [dirty, setDirty] = useState<SettingsData>({});

    // Shared
    const [section, setSection] = useState<Section>("profile");
    const [loading, setLoading] = useState(true);
    const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);

    useEffect(() => {
        Promise.all([
            apiClient.get("/auth/me"),
            apiClient.get("/settings/workspace"),
        ]).then(([meRes, wsRes]) => {
            if (meRes.success && meRes.data) {
                setProfile(meRes.data);
                setProfileName(meRes.data.full_name || "");
            }
            if (wsRes.success && wsRes.data) {
                setSettings(wsRes.data.settings);
                setVersion(wsRes.data.version);
            }
            setLoading(false);
        });
    }, []);

    const showToast = (type: "success" | "error", msg: string) => {
        setToast({ type, msg });
        setTimeout(() => setToast(null), 3000);
    };

    // Profile save
    const handleSaveProfile = async () => {
        setSavingProfile(true);
        const res = await apiClient.patch("/auth/me", { full_name: profileName.trim() || null });
        setSavingProfile(false);
        if (res.success && res.data) {
            setProfile(res.data);
            setProfileName(res.data.full_name || "");
            showToast("success", "Profile updated successfully");
        } else {
            showToast("error", res.error || "Failed to update profile");
        }
    };

    // Workspace settings
    const updateField = (sec: string, key: string, value: any) => {
        setSettings((prev) => {
            if (!prev) return prev;
            return { ...prev, [sec]: { ...prev[sec], [key]: value } };
        });
        setDirty((prev) => ({
            ...prev,
            [sec]: { ...(prev[sec] || {}), [key]: value },
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
            showToast("success", "Settings saved successfully");
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

    const s = settings ? (settings[activeTab] || {}) : {};
    const profileDirty = profileName.trim() !== (profile?.full_name || "");

    return (
        <div className="space-y-8 pb-10">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
                        <Settings className="w-6 h-6 text-teal-700" /> Settings
                    </h1>
                    <p className="text-slate-500 text-sm mt-1">Manage your profile and workspace configuration</p>
                </div>
                {section === "workspace" && (
                    <button
                        onClick={handleSave}
                        disabled={saving || Object.keys(dirty).length === 0}
                        className="flex items-center gap-2 px-5 py-2.5 bg-teal-700 text-white rounded-lg hover:bg-teal-800 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-bold transition-all"
                    >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        Save Changes
                    </button>
                )}
                {section === "profile" && (
                    <button
                        onClick={handleSaveProfile}
                        disabled={savingProfile || !profileDirty}
                        className="flex items-center gap-2 px-5 py-2.5 bg-teal-700 text-white rounded-lg hover:bg-teal-800 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-bold transition-all"
                    >
                        {savingProfile ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        Save Profile
                    </button>
                )}
            </div>

            {/* Toast */}
            {toast && (
                <div className={`px-4 py-3 rounded-xl text-sm font-medium flex items-center gap-2 ${
                    toast.type === "success"
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-100"
                        : "bg-red-50 text-red-700 border border-red-100"
                }`}>
                    {toast.msg}
                </div>
            )}

            {/* Section Toggle */}
            <div className="flex gap-2">
                <button
                    onClick={() => setSection("profile")}
                    className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${
                        section === "profile"
                            ? "bg-teal-700 text-white shadow-sm"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                >
                    <User className="w-4 h-4" /> Profile
                </button>
                <button
                    onClick={() => setSection("workspace")}
                    className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${
                        section === "workspace"
                            ? "bg-teal-700 text-white shadow-sm"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                >
                    <ShieldCheck className="w-4 h-4" /> Workspace
                    {version > 0 && <span className="text-xs opacity-70">v{version}</span>}
                </button>
            </div>

            {/* Profile Section */}
            {section === "profile" && profile && (
                <div className="bg-white p-6 md:p-8 rounded-xl border border-slate-100 shadow-sm space-y-6">
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Email</label>
                        <input
                            type="text"
                            value={profile.email}
                            disabled
                            className="w-full p-2.5 bg-slate-100 border border-slate-200 rounded-lg text-sm text-slate-500 cursor-not-allowed"
                        />
                    </div>
                    <Field label="Full Name" type="text" value={profileName} onChange={setProfileName} placeholder="Enter your full name" />
                    <div className="flex items-center gap-3">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Email Verification</span>
                        {profile.email_verified_at ? (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">Verified</span>
                        ) : (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">Unverified</span>
                        )}
                    </div>
                </div>
            )}

            {/* Workspace Section */}
            {section === "workspace" && settings && (
                <>
                    {/* Tabs */}
                    <div className="flex border-b border-slate-100 bg-slate-50/50 rounded-t-xl">
                        {TABS.map((tab) => (
                            <button
                                key={tab.key}
                                onClick={() => setActiveTab(tab.key)}
                                className={`flex items-center gap-2 px-6 py-3.5 text-sm font-bold border-b-2 transition-all ${
                                    activeTab === tab.key
                                        ? "border-teal-600 text-teal-700 bg-white"
                                        : "border-transparent text-slate-400 hover:text-slate-600"
                                }`}
                            >
                                <tab.icon className="w-4 h-4" />
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    {/* Fields */}
                    <div className="bg-white p-6 md:p-8 rounded-xl border border-slate-100 shadow-sm space-y-6">
                        {activeTab === "general" && (
                            <>
                                <Field label="Name Override" type="text" value={s.name_override ?? ""} onChange={(v) => updateField("general", "name_override", v || null)} placeholder="Leave empty to use workspace name" />
                                <Field label="Logo URL" type="text" value={s.logo_url ?? ""} onChange={(v) => updateField("general", "logo_url", v || null)} placeholder="https://example.com/logo.png" />
                                <CatalogSelectField label="Timezone" value={s.timezone} items={lookups.timezones} onChange={(v) => updateField("general", "timezone", v)} />
                                <CatalogSelectField label="Default Language" value={s.default_language} items={lookups.languages} onChange={(v) => updateField("general", "default_language", v)} />
                            </>
                        )}
                        {activeTab === "messaging" && (
                            <>
                                <Field label="Default Reply Delay (seconds)" type="number" value={s.default_reply_delay_seconds} onChange={(v) => updateField("messaging", "default_reply_delay_seconds", Number(v))} />
                                <Toggle label="Fallback Message Enabled" description="Send a fallback message when AI cannot generate a response" value={s.fallback_message_enabled} onChange={(v) => updateField("messaging", "fallback_message_enabled", v)} />
                                <Toggle label="Auto-Retry Failed Dispatch" description="Automatically retry failed message deliveries with exponential backoff" value={s.auto_retry_failed_dispatch} onChange={(v) => updateField("messaging", "auto_retry_failed_dispatch", v)} />
                            </>
                        )}
                        {activeTab === "ai" && (
                            <>
                                <CatalogSelectField label="Default Model" value={s.default_model} items={lookups.aiModels} onChange={(v) => updateField("ai", "default_model", v)} />
                                <Field label="Temperature" type="number" value={s.temperature} step="0.1" min="0" max="2" onChange={(v) => updateField("ai", "temperature", Number(v))} />
                                <Field label="Max Tokens" type="number" value={s.max_tokens} onChange={(v) => updateField("ai", "max_tokens", Number(v))} />
                                <Toggle label="Guardrails Enabled" description="Enforce safety guardrails on AI-generated responses" value={s.guardrails_enabled} onChange={(v) => updateField("ai", "guardrails_enabled", v)} />
                            </>
                        )}
                        {activeTab === "automation" && (
                            <>
                                <Toggle label="Auto-Publish" description="Automatically publish new automation flows" value={s.auto_publish} onChange={(v) => updateField("automation", "auto_publish", v)} />
                                <Field label="Draft Expiry (days)" type="number" value={s.draft_expiry_days} onChange={(v) => updateField("automation", "draft_expiry_days", Number(v))} />
                            </>
                        )}
                        {activeTab === "notifications" && (
                            <>
                                <Toggle label="Email Notifications Enabled" description="Receive email notifications for important workspace events" value={s.email_notifications_enabled} onChange={(v) => updateField("notifications", "email_notifications_enabled", v)} />
                                <Field label="Webhook URL" type="text" value={s.webhook_url ?? ""} onChange={(v) => updateField("notifications", "webhook_url", v || null)} placeholder="https://example.com/webhook" />
                            </>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}

/* ─── Shared form components ─────────────────────────────────────────────── */

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

function CatalogSelectField({ label, value, items, onChange }: { label: string; value: string; items: { key: string; label: string }[]; onChange: (v: string) => void }) {
    return (
        <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">{label}</label>
            <select
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 outline-none transition-all"
            >
                {items.map((item) => (
                    <option key={item.key} value={item.key}>{item.label}</option>
                ))}
            </select>
        </div>
    );
}

function Toggle({ label, description, value, onChange }: { label: string; description?: string; value: boolean; onChange: (v: boolean) => void }) {
    return (
        <div className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0">
            <div>
                <span className="text-sm font-medium text-slate-700">{label}</span>
                {description && <p className="text-xs text-slate-400 mt-0.5">{description}</p>}
            </div>
            <button
                type="button"
                onClick={() => onChange(!value)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${value ? "bg-teal-600" : "bg-slate-200"}`}
            >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform ${value ? "translate-x-6" : "translate-x-1"}`} />
            </button>
        </div>
    );
}
