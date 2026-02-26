"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { adminApi } from "@/lib/admin-api";
import {
    Landmark, Users, Building2, Loader2, ChevronLeft, RefreshCw,
    CreditCard, ShieldAlert, ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export default function AgencyDetailPage() {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();

    const [agency, setAgency] = useState<any>(null);
    const [plans, setPlans] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [updating, setUpdating] = useState(false);

    const load = async () => {
        setLoading(true);
        const [agencyRes, plansRes] = await Promise.all([
            adminApi.getAgencyDetail(id),
            adminApi.getPlans(),
        ]);
        if (agencyRes.success && agencyRes.data) {
            setAgency(agencyRes.data);
        } else {
            toast.error(agencyRes.error || "Failed to load agency");
        }
        if (plansRes.success && plansRes.data) {
            setPlans(plansRes.data.items || []);
        }
        setLoading(false);
    };

    useEffect(() => { load(); }, [id]);

    const handleToggleStatus = async () => {
        if (!agency) return;
        setUpdating(true);
        const newStatus = agency.status === "active" ? "suspended" : "active";
        const res = await adminApi.updateAgencyStatus(id, newStatus);
        if (res.success) {
            toast.success(`Agency ${newStatus === "active" ? "activated" : "suspended"}`);
            await load();
        } else {
            toast.error(res.error || "Failed to update status");
        }
        setUpdating(false);
    };

    const handleAssignPlan = async (planId: string) => {
        setUpdating(true);
        const res = await adminApi.assignAgencyPlan(id, planId);
        if (res.success) {
            toast.success("Plan assigned to agency");
            await load();
        } else {
            toast.error(res.error || "Failed to assign plan");
        }
        setUpdating(false);
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-64 gap-4">
                <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
                <p className="text-sm text-slate-500">Loading agency...</p>
            </div>
        );
    }

    if (!agency) {
        return (
            <div className="text-center py-20 text-slate-500">Agency not found.</div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4">
                <button
                    onClick={() => router.push("/admin/agencies")}
                    className="text-slate-400 hover:text-white transition-colors"
                >
                    <ChevronLeft className="w-5 h-5" />
                </button>
                <div className="flex-1">
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Landmark className="w-6 h-6 text-amber-400" />
                        {agency.name}
                    </h1>
                    <p className="text-slate-400 text-sm mt-0.5 font-mono">{agency.id}</p>
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
            <div className="grid grid-cols-3 gap-4">
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                    <div className="text-xs text-slate-500 mb-1">Status</div>
                    <div className="flex items-center gap-2">
                        <span className={cn(
                            "text-sm font-bold uppercase",
                            agency.status === "active" ? "text-emerald-400" : "text-red-400"
                        )}>
                            {agency.status}
                        </span>
                        <button
                            onClick={handleToggleStatus}
                            disabled={updating}
                            className={cn(
                                "ml-2 px-2 py-1 text-xs rounded transition-colors",
                                agency.status === "active"
                                    ? "bg-red-500/15 text-red-400 hover:bg-red-500/25"
                                    : "bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25"
                            )}
                        >
                            {agency.status === "active" ? "Suspend" : "Activate"}
                        </button>
                    </div>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                    <div className="text-xs text-slate-500 mb-1">Owner</div>
                    <div className="text-white font-medium text-sm">{agency.owner_email || "—"}</div>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                    <div className="text-xs text-slate-500 mb-1">Created</div>
                    <div className="text-white font-medium text-sm">
                        {agency.created_at ? new Date(agency.created_at).toLocaleDateString() : "—"}
                    </div>
                </div>
            </div>

            {/* Plan */}
            <section>
                <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                    <CreditCard className="w-5 h-5 text-amber-400" />
                    Agency Plan
                </h2>
                <div className="bg-white/5 border border-white/10 rounded-xl p-5">
                    <div className="flex items-center gap-4">
                        <div className="flex-1">
                            <div className="text-xs text-slate-500 mb-1">Current Plan</div>
                            <div className="text-white font-medium text-lg">
                                {agency.plan?.display_name || "No plan assigned"}
                            </div>
                        </div>
                        <select
                            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
                            value={agency.plan?.id || ""}
                            onChange={(e) => {
                                if (e.target.value) handleAssignPlan(e.target.value);
                            }}
                            disabled={updating}
                        >
                            <option value="" disabled>Change plan...</option>
                            {plans.filter((p: any) => p.is_active).map((p: any) => (
                                <option key={p.id} value={p.id}>{p.display_name}</option>
                            ))}
                        </select>
                        {updating && <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />}
                    </div>
                </div>
            </section>

            {/* Members */}
            <section>
                <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                    <Users className="w-5 h-5 text-amber-400" />
                    Members ({agency.members?.length || 0})
                </h2>
                <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                    {!agency.members?.length ? (
                        <div className="p-6 text-center text-slate-500 text-sm">No members.</div>
                    ) : (
                        <table className="w-full text-left text-sm">
                            <thead className="bg-white/5 text-slate-400 font-medium">
                                <tr>
                                    <th className="px-5 py-3">Name</th>
                                    <th className="px-5 py-3">Email</th>
                                    <th className="px-5 py-3">Role</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5 text-slate-300">
                                {agency.members.map((m: any) => (
                                    <tr key={m.id} className="hover:bg-white/[0.02] transition-colors">
                                        <td className="px-5 py-4 text-white">{m.full_name || "—"}</td>
                                        <td className="px-5 py-4">{m.email}</td>
                                        <td className="px-5 py-4">
                                            <span className="text-xs bg-violet-500/15 text-violet-400 px-2 py-0.5 rounded">
                                                {m.role}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </section>

            {/* Workspaces */}
            <section>
                <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                    <Building2 className="w-5 h-5 text-amber-400" />
                    Workspaces ({agency.workspaces?.length || 0})
                </h2>
                <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                    {!agency.workspaces?.length ? (
                        <div className="p-6 text-center text-slate-500 text-sm">No workspaces.</div>
                    ) : (
                        <table className="w-full text-left text-sm">
                            <thead className="bg-white/5 text-slate-400 font-medium">
                                <tr>
                                    <th className="px-5 py-3">Name</th>
                                    <th className="px-5 py-3">Tier</th>
                                    <th className="px-5 py-3">Created</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5 text-slate-300">
                                {agency.workspaces.map((ws: any) => (
                                    <tr
                                        key={ws.id}
                                        className="hover:bg-white/[0.02] transition-colors cursor-pointer"
                                        onClick={() => router.push(`/admin/workspaces/${ws.id}`)}
                                    >
                                        <td className="px-5 py-4 text-white font-medium">{ws.name}</td>
                                        <td className="px-5 py-4 capitalize">{ws.subscription_tier || "free"}</td>
                                        <td className="px-5 py-4">
                                            {ws.created_at ? new Date(ws.created_at).toLocaleDateString() : "—"}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </section>
        </div>
    );
}
