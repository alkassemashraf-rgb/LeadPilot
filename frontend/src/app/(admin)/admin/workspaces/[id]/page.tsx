"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { adminApi, MODULE_LABELS } from "@/lib/admin-api";
import {
    Building2, Users, Loader2, ChevronLeft, RefreshCw,
    ToggleLeft, ToggleRight, AlertCircle, CreditCard, Save,
    Pencil, X, Check
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export default function WorkspaceDetailPage() {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();

    const [workspace, setWorkspace] = useState<any>(null);
    const [modules, setModules] = useState<any[]>([]);
    const [planData, setPlanData] = useState<any>(null);
    const [plans, setPlans] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [toggling, setToggling] = useState<string | null>(null);
    const [assigningPlan, setAssigningPlan] = useState(false);
    const [editingLimit, setEditingLimit] = useState<string | null>(null);
    const [editLimitValue, setEditLimitValue] = useState<string>("");
    const [savingLimit, setSavingLimit] = useState(false);

    const load = async () => {
        setLoading(true);
        const [wsRes, modRes, planRes, plansRes] = await Promise.all([
            adminApi.getWorkspaceDetail(id),
            adminApi.getWorkspaceModules(id),
            adminApi.getWorkspacePlan(id),
            adminApi.getPlans(),
        ]);

        if (wsRes.success && wsRes.data) {
            setWorkspace(wsRes.data);
        } else {
            toast.error(wsRes.error || "Failed to load workspace");
        }

        if (modRes.success && modRes.data) {
            setModules(Array.isArray(modRes.data) ? modRes.data : []);
        }

        if (planRes.success && planRes.data) {
            setPlanData(planRes.data);
        }

        if (plansRes.success && plansRes.data) {
            setPlans(plansRes.data.items || []);
        }

        setLoading(false);
    };

    const handleAssignPlan = async (planId: string) => {
        setAssigningPlan(true);
        const res = await adminApi.assignWorkspacePlan(id, planId);
        if (res.success) {
            toast.success("Plan assigned successfully");
            const planRes = await adminApi.getWorkspacePlan(id);
            if (planRes.success && planRes.data) setPlanData(planRes.data);
        } else {
            toast.error(res.error || "Failed to assign plan");
        }
        setAssigningPlan(false);
    };

    const handleSaveLimit = async (moduleKey: string) => {
        setSavingLimit(true);
        const parsedValue = editLimitValue.trim() === "" ? null : parseInt(editLimitValue, 10);
        if (editLimitValue.trim() !== "" && (isNaN(parsedValue!) || parsedValue! < 0)) {
            toast.error("Please enter a valid number or leave blank for no override");
            setSavingLimit(false);
            return;
        }
        const res = await adminApi.setWorkspaceOverrides(id, [{ module_key: moduleKey, hard_limit: parsedValue }]);
        if (res.success) {
            toast.success(`Usage limit override for "${MODULE_LABELS[moduleKey] || moduleKey}" saved`);
            setEditingLimit(null);
            // Reload plan data to reflect changes
            const planRes = await adminApi.getWorkspacePlan(id);
            if (planRes.success && planRes.data) setPlanData(planRes.data);
        } else {
            toast.error(res.error || "Failed to save override");
        }
        setSavingLimit(false);
    };

    useEffect(() => { load(); }, [id]);

    const handleToggleModule = async (moduleName: string, currentEffective: boolean) => {
        setToggling(moduleName);
        const res = await adminApi.setWorkspaceModule(id, moduleName, !currentEffective);
        if (res.success) {
            toast.success(`Module "${MODULE_LABELS[moduleName] || moduleName}" override set`);
            // Reload modules list
            const modRes = await adminApi.getWorkspaceModules(id);
            if (modRes.success && modRes.data) {
                setModules(Array.isArray(modRes.data) ? modRes.data : []);
            }
        } else {
            toast.error(res.error || "Failed to set module override");
        }
        setToggling(null);
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-64 gap-4">
                <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
                <p className="text-sm text-slate-500">Loading workspace...</p>
            </div>
        );
    }

    if (!workspace) {
        return (
            <div className="text-center py-20 text-slate-500">
                Workspace not found.
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4">
                <button
                    onClick={() => router.push("/admin/workspaces")}
                    className="text-slate-400 hover:text-white transition-colors"
                >
                    <ChevronLeft className="w-5 h-5" />
                </button>
                <div className="flex-1">
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Building2 className="w-6 h-6 text-amber-400" />
                        {workspace.name}
                    </h1>
                    <p className="text-slate-400 text-sm mt-0.5 font-mono">{workspace.id}</p>
                </div>
                <button
                    onClick={load}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-sm transition-colors"
                >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                </button>
            </div>

            {/* Info grid */}
            <div className="grid grid-cols-2 gap-4">
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                    <div className="text-xs text-slate-500 mb-1">Subscription</div>
                    <div className="text-white font-medium capitalize">{workspace.subscription_tier || "free"}</div>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                    <div className="text-xs text-slate-500 mb-1">Created</div>
                    <div className="text-white font-medium">
                        {workspace.created_at ? new Date(workspace.created_at).toLocaleDateString() : "—"}
                    </div>
                </div>
            </div>

            {/* Members */}
            <section>
                <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                    <Users className="w-5 h-5 text-amber-400" />
                    Members ({workspace.member_count ?? 0})
                </h2>
                <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                    {workspace.members?.length === 0 ? (
                        <div className="p-6 text-center text-slate-500 text-sm">No members found.</div>
                    ) : (
                        <table className="w-full text-left text-sm">
                            <thead className="bg-white/5 text-slate-400 font-medium">
                                <tr>
                                    <th className="px-5 py-3">Name</th>
                                    <th className="px-5 py-3">Email</th>
                                    <th className="px-5 py-3">Role</th>
                                    <th className="px-5 py-3">Active</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5 text-slate-300">
                                {workspace.members?.map((m: any) => (
                                    <tr key={m.id} className="hover:bg-white/[0.02] transition-colors">
                                        <td className="px-5 py-4 text-white">{m.full_name || "—"}</td>
                                        <td className="px-5 py-4">{m.email}</td>
                                        <td className="px-5 py-4">
                                            <span className="text-xs bg-amber-500/15 text-amber-400 px-2 py-0.5 rounded capitalize">
                                                {m.role}
                                            </span>
                                        </td>
                                        <td className="px-5 py-4">
                                            <span className={cn("text-[10px] font-bold uppercase", m.is_active ? "text-emerald-400" : "text-red-400")}>
                                                {m.is_active ? "Active" : "Inactive"}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </section>

            {/* Plan & Usage */}
            <section>
                <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                    <CreditCard className="w-5 h-5 text-amber-400" />
                    Plan & Usage
                </h2>
                <div className="bg-white/5 border border-white/10 rounded-xl p-5 space-y-4">
                    <div className="flex items-center gap-4">
                        <div className="flex-1">
                            <div className="text-xs text-slate-500 mb-1">Current Plan</div>
                            <div className="text-white font-medium text-lg">
                                {planData?.plan?.display_name || "No plan assigned"}
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <select
                                className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                                value={planData?.plan?.id || ""}
                                onChange={(e) => {
                                    if (e.target.value) handleAssignPlan(e.target.value);
                                }}
                                disabled={assigningPlan}
                            >
                                <option value="" disabled>Change plan...</option>
                                {plans.filter((p: any) => p.is_active).map((p: any) => (
                                    <option key={p.id} value={p.id}>{p.display_name}</option>
                                ))}
                            </select>
                            {assigningPlan && <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />}
                        </div>
                    </div>

                    {planData?.entitlements?.length > 0 && (
                        <div className="space-y-2">
                            <div className="text-xs text-slate-500 font-medium">Usage This Month</div>
                            {planData.entitlements.map((e: any) => {
                                const limit = e.effective_limit;
                                const used = e.used || 0;
                                const pct = limit ? Math.min(100, Math.round((used / limit) * 100)) : 0;
                                const isUnlimited = limit === null || limit === undefined;
                                const isEditing = editingLimit === e.module_key;
                                return (
                                    <div key={e.module_key} className="flex items-center gap-3">
                                        <div className="w-36 text-xs text-slate-400 truncate">
                                            {MODULE_LABELS[e.module_key] || e.module_key}
                                        </div>
                                        <div className="flex-1 bg-white/5 rounded-full h-2 overflow-hidden">
                                            {!isUnlimited && (
                                                <div
                                                    className={cn(
                                                        "h-full rounded-full transition-all",
                                                        pct >= 100 ? "bg-red-500" : pct >= 80 ? "bg-amber-500" : "bg-emerald-500"
                                                    )}
                                                    style={{ width: `${pct}%` }}
                                                />
                                            )}
                                        </div>
                                        {isEditing ? (
                                            <div className="flex items-center gap-1.5">
                                                <input
                                                    type="number"
                                                    min={0}
                                                    className="w-20 bg-white/5 border border-white/20 rounded px-2 py-1 text-xs text-white"
                                                    placeholder="Blank = plan"
                                                    value={editLimitValue}
                                                    onChange={(ev) => setEditLimitValue(ev.target.value)}
                                                    autoFocus
                                                />
                                                <button
                                                    onClick={() => handleSaveLimit(e.module_key)}
                                                    disabled={savingLimit}
                                                    className="text-emerald-400 hover:text-emerald-300 disabled:opacity-50"
                                                    title="Save"
                                                >
                                                    {savingLimit ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                                                </button>
                                                <button
                                                    onClick={() => setEditingLimit(null)}
                                                    className="text-slate-400 hover:text-slate-300"
                                                    title="Cancel"
                                                >
                                                    <X className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        ) : (
                                            <div className="flex items-center gap-1.5">
                                                <div className="w-24 text-xs text-slate-400 text-right">
                                                    {isUnlimited ? (
                                                        <span className="text-emerald-400">Unlimited</span>
                                                    ) : (
                                                        <span className={cn(pct >= 100 ? "text-red-400" : pct >= 80 ? "text-amber-400" : "text-slate-400")}>
                                                            {used} / {limit}
                                                        </span>
                                                    )}
                                                    {e.has_override && <span className="ml-1 text-amber-400">*</span>}
                                                </div>
                                                <button
                                                    onClick={() => {
                                                        setEditingLimit(e.module_key);
                                                        setEditLimitValue(e.has_override && e.effective_limit != null ? String(e.effective_limit) : "");
                                                    }}
                                                    className="text-slate-500 hover:text-amber-400 transition-colors"
                                                    title="Edit limit override"
                                                >
                                                    <Pencil className="w-3 h-3" />
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                            <p className="text-[10px] text-slate-600 mt-1">* = admin override active · Click pencil to set a custom limit</p>
                        </div>
                    )}
                </div>
            </section>

            {/* Module Overrides */}
            <section>
                <div className="flex items-center gap-2 mb-1">
                    <h2 className="text-lg font-semibold text-white">Module Overrides</h2>
                </div>
                <p className="text-slate-400 text-xs mb-4">
                    Workspace-level overrides take precedence over global module settings.
                </p>
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 flex gap-3 mb-4">
                    <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                    <p className="text-xs text-amber-200/70">
                        Setting an override here will affect all users in this workspace. The cache clears within 15 seconds.
                    </p>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-xl divide-y divide-white/5">
                    {modules.map((m) => (
                        <div key={m.module_name} className="px-5 py-4 flex items-center justify-between">
                            <div>
                                <div className="text-white text-sm font-medium">
                                    {MODULE_LABELS[m.module_name] || m.module_name}
                                </div>
                                <div className="text-xs text-slate-500 mt-0.5">
                                    Global: {m.global_enabled ? "enabled" : "disabled"}
                                    {m.has_override && (
                                        <span className="ml-2 text-amber-400 font-medium">(override active)</span>
                                    )}
                                </div>
                            </div>
                            <button
                                onClick={() => handleToggleModule(m.module_name, m.effective_enabled)}
                                disabled={toggling === m.module_name}
                                className="flex items-center gap-2 transition-colors disabled:opacity-50"
                                title={m.effective_enabled ? "Click to disable for this workspace" : "Click to enable for this workspace"}
                            >
                                {toggling === m.module_name ? (
                                    <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />
                                ) : m.effective_enabled ? (
                                    <ToggleRight className="w-7 h-7 text-emerald-400" />
                                ) : (
                                    <ToggleLeft className="w-7 h-7 text-slate-500" />
                                )}
                            </button>
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
}
