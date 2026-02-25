"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { adminApi, MODULE_LABELS } from "@/lib/admin-api";
import {
    Building2, Users, Loader2, ChevronLeft, RefreshCw,
    ToggleLeft, ToggleRight, AlertCircle
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export default function WorkspaceDetailPage() {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();

    const [workspace, setWorkspace] = useState<any>(null);
    const [modules, setModules] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [toggling, setToggling] = useState<string | null>(null);

    const load = async () => {
        setLoading(true);
        const [wsRes, modRes] = await Promise.all([
            adminApi.getWorkspaceDetail(id),
            adminApi.getWorkspaceModules(id),
        ]);

        if (wsRes.success && wsRes.data) {
            setWorkspace(wsRes.data);
        } else {
            toast.error(wsRes.error || "Failed to load workspace");
        }

        if (modRes.success && modRes.data) {
            setModules(Array.isArray(modRes.data) ? modRes.data : []);
        }

        setLoading(false);
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
