"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import { Zap, Loader2, Info, RefreshCw, PowerOff } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export default function AdminAutomationsPage() {
    const [items, setItems] = useState<any[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [disabling, setDisabling] = useState<string | null>(null);

    const load = async () => {
        setLoading(true);
        const res = await adminApi.getAdminAutomations({ limit: 100 });
        if (res.success && res.data) {
            setItems(res.data.items);
            setTotal(res.data.total);
        } else {
            toast.error(res.error || "Failed to load automations");
        }
        setLoading(false);
    };

    useEffect(() => { load(); }, []);

    const handleDisable = async (flowId: string, name: string) => {
        if (!confirm(`Disable automation "${name}"? This will unpublish it.`)) return;
        setDisabling(flowId);
        const res = await adminApi.disableFlow(flowId);
        if (res.success) {
            toast.success(`Flow "${name}" has been unpublished`);
            load();
        } else {
            toast.error(res.error || "Failed to disable flow");
        }
        setDisabling(null);
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Zap className="w-6 h-6 text-amber-400" />
                        Automations
                    </h1>
                    <p className="text-slate-400 text-sm mt-1">{total} flows across all workspaces</p>
                </div>
                <button
                    onClick={load}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-sm transition-colors"
                >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                </button>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                {loading ? (
                    <div className="flex flex-col items-center justify-center p-20 gap-4">
                        <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
                        <p className="text-sm text-slate-500">Loading automations...</p>
                    </div>
                ) : items.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-20 gap-4">
                        <Info className="w-8 h-8 text-slate-600" />
                        <p className="text-sm text-slate-500">No automation flows found.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-white/5 text-slate-400 font-medium">
                                <tr>
                                    <th className="px-5 py-3">Flow Name</th>
                                    <th className="px-5 py-3">Workspace</th>
                                    <th className="px-5 py-3">Status</th>
                                    <th className="px-5 py-3">Trigger</th>
                                    <th className="px-5 py-3">Created</th>
                                    <th className="px-5 py-3">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5 text-slate-300">
                                {items.map((item) => (
                                    <tr key={item.id} className="hover:bg-white/[0.02] transition-colors">
                                        <td className="px-5 py-4 text-white font-medium">{item.name || "Untitled"}</td>
                                        <td className="px-5 py-4 text-xs font-mono">{item.workspace_id?.slice(0, 8)}...</td>
                                        <td className="px-5 py-4">
                                            <StatusBadge status={item.status} />
                                        </td>
                                        <td className="px-5 py-4 text-xs font-mono bg-white/[0.03] rounded px-2 py-0.5 w-fit">{item.trigger_type || "—"}</td>
                                        <td className="px-5 py-4 text-slate-500 text-xs">
                                            {item.created_at ? new Date(item.created_at).toLocaleDateString() : "—"}
                                        </td>
                                        <td className="px-5 py-4">
                                            {item.status === "PUBLISHED" && (
                                                <button
                                                    onClick={() => handleDisable(item.id, item.name || item.id)}
                                                    disabled={disabling === item.id}
                                                    className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 transition-colors disabled:opacity-50"
                                                >
                                                    <PowerOff className="w-3 h-3" />
                                                    {disabling === item.id ? "Disabling..." : "Disable"}
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}

function StatusBadge({ status }: { status: string }) {
    const s = (status || "").toLowerCase();
    return (
        <span className={cn(
            "text-[10px] font-bold uppercase",
            s === "published" ? "text-emerald-400" : "text-slate-400"
        )}>
            {s || "unknown"}
        </span>
    );
}
