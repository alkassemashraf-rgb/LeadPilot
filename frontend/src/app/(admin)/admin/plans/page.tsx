"use client";

import { useEffect, useState, useCallback } from "react";
import { adminApi, MODULE_LABELS } from "@/lib/admin-api";
import {
    CreditCard,
    Plus,
    Save,
    Loader2,
    RefreshCw,
    ToggleLeft,
    ToggleRight,
    ChevronDown,
    ChevronRight,
} from "lucide-react";
import { toast } from "sonner";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Plan {
    id: string;
    name: string;
    display_name: string;
    description: string | null;
    entitlement_count: number;
    workspace_count: number;
    is_active: boolean;
    sort_order: number;
}

interface Entitlement {
    module_key: string;
    hard_limit: number | null;
}

interface PlanDetail extends Plan {
    entitlements: Entitlement[];
}

/* ------------------------------------------------------------------ */
/*  Entitlement Editor                                                 */
/* ------------------------------------------------------------------ */

function EntitlementEditor({
    planId,
    onSaved,
}: {
    planId: string;
    onSaved: () => void;
}) {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [entitlements, setEntitlements] = useState<
        Record<string, { enabled: boolean; hard_limit: number | null }>
    >({});

    useEffect(() => {
        let cancelled = false;
        (async () => {
            setLoading(true);
            const res = await adminApi.getPlanDetail(planId);
            if (cancelled) return;
            if (res.success && res.data) {
                const detail = res.data as PlanDetail;
                const map: Record<string, { enabled: boolean; hard_limit: number | null }> = {};
                // initialise all modules as unchecked
                for (const key of Object.keys(MODULE_LABELS)) {
                    map[key] = { enabled: false, hard_limit: null };
                }
                // overlay existing entitlements
                for (const ent of detail.entitlements ?? []) {
                    map[ent.module_key] = { enabled: true, hard_limit: ent.hard_limit };
                }
                setEntitlements(map);
            } else {
                toast.error(res.error || "Failed to load plan entitlements");
            }
            setLoading(false);
        })();
        return () => { cancelled = true; };
    }, [planId]);

    const toggle = (key: string) => {
        setEntitlements((prev) => ({
            ...prev,
            [key]: { ...prev[key], enabled: !prev[key].enabled },
        }));
    };

    const setLimit = (key: string, value: string) => {
        const num = value === "" ? null : parseInt(value, 10);
        setEntitlements((prev) => ({
            ...prev,
            [key]: { ...prev[key], hard_limit: isNaN(num as number) ? null : num },
        }));
    };

    const handleSave = async () => {
        setSaving(true);
        const payload: { module_key: string; hard_limit: number | null }[] = [];
        for (const [key, val] of Object.entries(entitlements)) {
            if (val.enabled) {
                payload.push({ module_key: key, hard_limit: val.hard_limit });
            }
        }
        const res = await adminApi.setPlanEntitlements(planId, payload);
        if (res.success) {
            toast.success("Entitlements saved");
            onSaved();
        } else {
            toast.error(res.error || "Failed to save entitlements");
        }
        setSaving(false);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {Object.entries(MODULE_LABELS).map(([key, label]) => {
                    const ent = entitlements[key];
                    if (!ent) return null;
                    return (
                        <div
                            key={key}
                            className={`flex items-center gap-3 px-3 py-2 rounded-lg border transition-all ${
                                ent.enabled
                                    ? "bg-white/5 border-white/10"
                                    : "bg-white/[0.02] border-white/5 opacity-60"
                            }`}
                        >
                            <input
                                type="checkbox"
                                checked={ent.enabled}
                                onChange={() => toggle(key)}
                                className="accent-amber-400 w-4 h-4 flex-shrink-0"
                            />
                            <div className="flex-1 min-w-0">
                                <p className="text-sm text-white truncate">{label}</p>
                                <p className="text-[10px] text-slate-500 font-mono">{key}</p>
                            </div>
                            <input
                                type="number"
                                min={0}
                                placeholder="No limit"
                                value={ent.hard_limit ?? ""}
                                onChange={(e) => setLimit(key, e.target.value)}
                                disabled={!ent.enabled}
                                className="w-24 bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-white placeholder:text-slate-600 disabled:opacity-30 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                            />
                        </div>
                    );
                })}
            </div>

            <div className="flex justify-end">
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-black font-semibold text-sm rounded-lg transition-colors disabled:opacity-50"
                >
                    {saving ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                        <Save className="w-4 h-4" />
                    )}
                    Save Entitlements
                </button>
            </div>
        </div>
    );
}

/* ------------------------------------------------------------------ */
/*  Create Plan Form                                                   */
/* ------------------------------------------------------------------ */

function CreatePlanForm({
    onCreated,
    onCancel,
}: {
    onCreated: () => void;
    onCancel: () => void;
}) {
    const [name, setName] = useState("");
    const [displayName, setDisplayName] = useState("");
    const [description, setDescription] = useState("");
    const [sortOrder, setSortOrder] = useState(0);
    const [saving, setSaving] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!name.trim() || !displayName.trim()) {
            toast.error("Name and display name are required");
            return;
        }
        setSaving(true);
        const res = await adminApi.createPlan({
            name: name.trim(),
            display_name: displayName.trim(),
            description: description.trim() || undefined,
            sort_order: sortOrder,
        });
        if (res.success) {
            toast.success("Plan created");
            onCreated();
        } else {
            toast.error(res.error || "Failed to create plan");
        }
        setSaving(false);
    };

    const inputClass =
        "w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-amber-500/50";

    return (
        <form onSubmit={handleSubmit} className="bg-white/5 border border-white/10 rounded-xl p-6 space-y-4">
            <h3 className="text-lg font-semibold text-white">Create New Plan</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label className="block text-xs text-slate-400 mb-1">
                        Name (slug)
                    </label>
                    <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="e.g. pro_monthly"
                        className={inputClass}
                        required
                    />
                </div>
                <div>
                    <label className="block text-xs text-slate-400 mb-1">
                        Display Name
                    </label>
                    <input
                        type="text"
                        value={displayName}
                        onChange={(e) => setDisplayName(e.target.value)}
                        placeholder="e.g. Pro Monthly"
                        className={inputClass}
                        required
                    />
                </div>
                <div className="md:col-span-2">
                    <label className="block text-xs text-slate-400 mb-1">
                        Description
                    </label>
                    <input
                        type="text"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Optional description"
                        className={inputClass}
                    />
                </div>
                <div>
                    <label className="block text-xs text-slate-400 mb-1">
                        Sort Order
                    </label>
                    <input
                        type="number"
                        value={sortOrder}
                        onChange={(e) => setSortOrder(parseInt(e.target.value, 10) || 0)}
                        className={inputClass}
                    />
                </div>
            </div>

            <div className="flex items-center gap-3 pt-2">
                <button
                    type="submit"
                    disabled={saving}
                    className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-black font-semibold text-sm rounded-lg transition-colors disabled:opacity-50"
                >
                    {saving ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                        <Plus className="w-4 h-4" />
                    )}
                    Create Plan
                </button>
                <button
                    type="button"
                    onClick={onCancel}
                    className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
                >
                    Cancel
                </button>
            </div>
        </form>
    );
}

/* ------------------------------------------------------------------ */
/*  Plan Row                                                           */
/* ------------------------------------------------------------------ */

function PlanRow({
    plan,
    expanded,
    onToggleExpand,
    onToggleActive,
    togglingActive,
    onEntitlementsSaved,
}: {
    plan: Plan;
    expanded: boolean;
    onToggleExpand: () => void;
    onToggleActive: (planId: string, isActive: boolean) => void;
    togglingActive: string | null;
    onEntitlementsSaved: () => void;
}) {
    const isBusy = togglingActive === plan.id;

    return (
        <>
            <tr
                className="hover:bg-white/[0.02] transition-colors cursor-pointer"
                onClick={onToggleExpand}
            >
                <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                        {expanded ? (
                            <ChevronDown className="w-4 h-4 text-slate-500 flex-shrink-0" />
                        ) : (
                            <ChevronRight className="w-4 h-4 text-slate-500 flex-shrink-0" />
                        )}
                        <div>
                            <p className="font-medium text-white">{plan.display_name}</p>
                            <p className="text-[10px] font-mono text-slate-500">{plan.name}</p>
                        </div>
                    </div>
                </td>
                <td className="px-6 py-4 text-slate-300 text-sm max-w-xs truncate">
                    {plan.description || <span className="text-slate-600">--</span>}
                </td>
                <td className="px-6 py-4 text-center text-sm text-slate-300">
                    {plan.entitlement_count}
                </td>
                <td className="px-6 py-4 text-center text-sm text-slate-300">
                    {plan.workspace_count}
                </td>
                <td className="px-6 py-4 text-center">
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            if (!isBusy) onToggleActive(plan.id, !plan.is_active);
                        }}
                        disabled={isBusy}
                        className="inline-flex items-center gap-1 transition-colors"
                        title={plan.is_active ? "Deactivate plan" : "Activate plan"}
                    >
                        {isBusy ? (
                            <Loader2 className="w-6 h-6 text-amber-400 animate-spin" />
                        ) : plan.is_active ? (
                            <ToggleRight className="w-7 h-7 text-emerald-400" />
                        ) : (
                            <ToggleLeft className="w-7 h-7 text-slate-500" />
                        )}
                    </button>
                </td>
                <td className="px-6 py-4 text-center text-sm text-slate-400">
                    {plan.sort_order}
                </td>
            </tr>

            {expanded && (
                <tr>
                    <td colSpan={6} className="px-6 py-4 bg-white/[0.02] border-t border-white/5">
                        <div className="space-y-3">
                            <h4 className="text-sm font-semibold text-amber-400">
                                Module Entitlements
                            </h4>
                            <EntitlementEditor
                                planId={plan.id}
                                onSaved={onEntitlementsSaved}
                            />
                        </div>
                    </td>
                </tr>
            )}
        </>
    );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function AdminPlansPage() {
    const [plans, setPlans] = useState<Plan[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [showCreate, setShowCreate] = useState(false);
    const [togglingActive, setTogglingActive] = useState<string | null>(null);

    const fetchPlans = useCallback(async () => {
        setLoading(true);
        const res = await adminApi.getPlans();
        if (res.success && res.data) {
            setPlans(res.data.items ?? []);
        } else {
            toast.error(res.error || "Failed to load plans");
        }
        setLoading(false);
    }, []);

    useEffect(() => {
        fetchPlans();
    }, [fetchPlans]);

    const handleToggleActive = async (planId: string, isActive: boolean) => {
        setTogglingActive(planId);
        const res = await adminApi.updatePlan(planId, { is_active: isActive });
        if (res.success) {
            setPlans((prev) =>
                prev.map((p) => (p.id === planId ? { ...p, is_active: isActive } : p))
            );
            toast.success(`Plan ${isActive ? "activated" : "deactivated"}`);
        } else {
            toast.error(res.error || "Failed to update plan");
        }
        setTogglingActive(null);
    };

    const handleCreated = () => {
        setShowCreate(false);
        fetchPlans();
    };

    const handleEntitlementsSaved = () => {
        fetchPlans();
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <CreditCard className="w-6 h-6 text-amber-400" />
                        Plan Management
                    </h1>
                    <p className="text-slate-400 text-sm mt-1">
                        Configure subscription plans and their module entitlements.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={fetchPlans}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-slate-300 hover:text-white hover:bg-white/10 transition-colors disabled:opacity-50"
                    >
                        <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                        Refresh
                    </button>
                    <button
                        onClick={() => setShowCreate(!showCreate)}
                        className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-black font-semibold text-sm rounded-lg transition-colors"
                    >
                        <Plus className="w-4 h-4" />
                        Create Plan
                    </button>
                </div>
            </div>

            {/* Create form */}
            {showCreate && (
                <CreatePlanForm
                    onCreated={handleCreated}
                    onCancel={() => setShowCreate(false)}
                />
            )}

            {/* Plans table */}
            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                <table className="w-full text-left text-sm">
                    <thead className="bg-white/5 text-slate-400 font-medium">
                        <tr>
                            <th className="px-6 py-3">Plan</th>
                            <th className="px-6 py-3">Description</th>
                            <th className="px-6 py-3 text-center">Entitlements</th>
                            <th className="px-6 py-3 text-center">Workspaces</th>
                            <th className="px-6 py-3 text-center">Active</th>
                            <th className="px-6 py-3 text-center">Sort</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-slate-300">
                        {loading ? (
                            <tr>
                                <td colSpan={6} className="px-6 py-12 text-center">
                                    <Loader2 className="w-6 h-6 text-amber-400 animate-spin mx-auto" />
                                </td>
                            </tr>
                        ) : plans.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                                    No plans found. Create one to get started.
                                </td>
                            </tr>
                        ) : (
                            plans.map((plan) => (
                                <PlanRow
                                    key={plan.id}
                                    plan={plan}
                                    expanded={expandedId === plan.id}
                                    onToggleExpand={() =>
                                        setExpandedId(expandedId === plan.id ? null : plan.id)
                                    }
                                    onToggleActive={handleToggleActive}
                                    togglingActive={togglingActive}
                                    onEntitlementsSaved={handleEntitlementsSaved}
                                />
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
