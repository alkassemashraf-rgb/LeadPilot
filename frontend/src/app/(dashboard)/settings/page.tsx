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
    CreditCard,
    Puzzle,
    CheckCircle2,
    XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

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

type Section = "profile" | "workspace" | "subscription" | "modules";

interface EntitlementModule {
    module_key: string;
    label: string;
    enabled: boolean;
    source: string;
}

interface UsageEntry {
    module_key: string;
    plan_limit: number | null;
    effective_limit: number | null;
    has_override: boolean;
    used: number;
    plan_name: string;
}

interface SubscriptionData {
    plan: { id: string; code: string; display_name: string; description: string } | null;
    assigned_at: string | null;
    usage: UsageEntry[];
}

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

    // Subscription & modules state
    const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
    const [modules, setModules] = useState<EntitlementModule[]>([]);

    // Shared
    const [section, setSection] = useState<Section>("profile");
    const [loading, setLoading] = useState(true);
    const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);

    useEffect(() => {
        Promise.all([
            apiClient.get("/auth/me"),
            apiClient.get("/settings/workspace"),
            apiClient.get("/settings/subscription"),
            apiClient.get("/settings/modules"),
        ]).then(([meRes, wsRes, subRes, modRes]) => {
            if (meRes.success && meRes.data) {
                setProfile(meRes.data);
                setProfileName(meRes.data.full_name || "");
            }
            if (wsRes.success && wsRes.data) {
                setSettings(wsRes.data.settings);
                setVersion(wsRes.data.version);
            }
            if (subRes.success && subRes.data) {
                setSubscription(subRes.data);
            }
            if (modRes.success && modRes.data) {
                setModules(modRes.data);
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
                <button
                    onClick={() => setSection("subscription")}
                    className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${
                        section === "subscription"
                            ? "bg-teal-700 text-white shadow-sm"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                >
                    <CreditCard className="w-4 h-4" /> Subscription
                </button>
                <button
                    onClick={() => setSection("modules")}
                    className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${
                        section === "modules"
                            ? "bg-teal-700 text-white shadow-sm"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                >
                    <Puzzle className="w-4 h-4" /> Modules
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

            {/* Subscription Section */}
            {section === "subscription" && (
                <div className="bg-white p-6 md:p-8 rounded-xl border border-slate-100 shadow-sm space-y-6">
                    <div className="flex items-center gap-3 mb-2">
                        <CreditCard className="w-5 h-5 text-teal-700" />
                        <h2 className="text-lg font-bold text-slate-900">Current Plan</h2>
                    </div>
                    {subscription?.plan ? (
                        <div className="space-y-6">
                            <div className="flex items-center gap-3">
                                <span className="text-2xl font-bold text-teal-700">{subscription.plan.display_name}</span>
                                <span className="text-xs font-semibold uppercase tracking-wide px-2.5 py-1 rounded-full bg-teal-50 text-teal-600 border border-teal-100">
                                    Active
                                </span>
                            </div>
                            {subscription.plan.description && (
                                <p className="text-sm text-slate-500">{subscription.plan.description}</p>
                            )}
                            {subscription.assigned_at && (
                                <p className="text-xs text-slate-400">
                                    Active since {new Date(subscription.assigned_at).toLocaleDateString()}
                                </p>
                            )}

                            {subscription.usage.length > 0 && (
                                <div className="space-y-3">
                                    <h3 className="text-sm font-semibold text-slate-700">Usage This Month</h3>
                                    {subscription.usage.map((u) => {
                                        const limit = u.effective_limit;
                                        const used = u.used || 0;
                                        const pct = limit ? Math.min(100, Math.round((used / limit) * 100)) : 0;
                                        const isUnlimited = limit === null || limit === undefined;
                                        return (
                                            <div key={u.module_key} className="flex items-center gap-3">
                                                <div className="w-40 text-xs text-slate-500 truncate font-medium">
                                                    {u.plan_name !== "Unknown" ? u.module_key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) : u.module_key}
                                                </div>
                                                <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
                                                    {!isUnlimited && (
                                                        <div
                                                            className={cn(
                                                                "h-full rounded-full transition-all",
                                                                pct >= 100 ? "bg-red-500" : pct >= 80 ? "bg-amber-500" : "bg-teal-500"
                                                            )}
                                                            style={{ width: `${pct}%` }}
                                                        />
                                                    )}
                                                </div>
                                                <div className="w-24 text-xs text-slate-400 text-right">
                                                    {isUnlimited ? (
                                                        <span className="text-teal-600 font-medium">Unlimited</span>
                                                    ) : (
                                                        <span className={cn(pct >= 100 ? "text-red-500" : pct >= 80 ? "text-amber-500" : "text-slate-500")}>
                                                            {used} / {limit}
                                                        </span>
                                                    )}
                                                    {u.has_override && <span className="ml-1 text-amber-500">*</span>}
                                                </div>
                                            </div>
                                        );
                                    })}
                                    <p className="text-[10px] text-slate-400 mt-1">* = custom limit set by admin</p>
                                </div>
                            )}
                        </div>
                    ) : (
                        <p className="text-sm text-slate-400">No plan assigned. Contact your administrator.</p>
                    )}
                    <div className="pt-4 border-t border-slate-100">
                        <p className="text-xs text-slate-400">
                            To change your plan, contact your workspace administrator or system admin.
                        </p>
                    </div>
                </div>
            )}

            {/* Modules Section */}
            {section === "modules" && (
                <div className="bg-white p-6 md:p-8 rounded-xl border border-slate-100 shadow-sm space-y-4">
                    <div className="flex items-center gap-3 mb-2">
                        <Puzzle className="w-5 h-5 text-teal-700" />
                        <h2 className="text-lg font-bold text-slate-900">Available Modules</h2>
                    </div>
                    <p className="text-sm text-slate-500 mb-4">
                        Modules enabled for your workspace based on your plan and admin configuration.
                    </p>
                    <div className="divide-y divide-slate-50">
                        {modules.map((m) => (
                            <div key={m.module_key} className="flex items-center justify-between py-3">
                                <div className="flex items-center gap-3">
                                    {m.enabled ? (
                                        <CheckCircle2 className="w-4 h-4 text-teal-500 shrink-0" />
                                    ) : (
                                        <XCircle className="w-4 h-4 text-slate-300 shrink-0" />
                                    )}
                                    <div>
                                        <span className={cn("text-sm font-medium", m.enabled ? "text-slate-700" : "text-slate-400")}>{m.label}</span>
                                        <span className="ml-2 text-[10px] uppercase tracking-wide text-slate-400">
                                            {m.source === "override" ? "Admin override" : m.source === "global_disabled" ? "Globally disabled" : "Plan default"}
                                        </span>
                                    </div>
                                </div>
                                <span className={cn(
                                    "text-xs font-semibold px-2 py-0.5 rounded-full",
                                    m.enabled
                                        ? "bg-teal-50 text-teal-600 border border-teal-100"
                                        : "bg-slate-50 text-slate-400 border border-slate-100"
                                )}>
                                    {m.enabled ? "Enabled" : "Disabled"}
                                </span>
                            </div>
                        ))}
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
