"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import { Database, Loader2, Info, RefreshCw, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export default function AdminZohoHealthPage() {
    const [items, setItems] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const load = async () => {
        setLoading(true);
        const res = await adminApi.getZohoHealth();
        if (res.success && res.data) {
            setItems(res.data.items);
        } else {
            toast.error(res.error || "Failed to load Zoho health");
        }
        setLoading(false);
    };

    useEffect(() => { load(); }, []);

    const connected = items.filter((i) => i.status === "CONNECTED").length;
    const errored = items.filter((i) => i.status === "ERROR").length;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Database className="w-6 h-6 text-amber-400" />
                        Zoho Integration Health
                    </h1>
                    <p className="text-slate-400 text-sm mt-1">
                        {items.length} workspace integrations &mdash; {connected} connected, {errored} errored
                    </p>
                </div>
                <button
                    onClick={load}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-sm transition-colors"
                >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                </button>
            </div>

            {/* Summary cards */}
            <div className="grid grid-cols-3 gap-4">
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4">
                    <div className="text-2xl font-bold text-emerald-400">{connected}</div>
                    <div className="text-xs text-emerald-300/70 mt-1">Connected</div>
                </div>
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
                    <div className="text-2xl font-bold text-red-400">{errored}</div>
                    <div className="text-xs text-red-300/70 mt-1">Errored</div>
                </div>
                <div className="bg-slate-500/10 border border-slate-500/20 rounded-xl p-4">
                    <div className="text-2xl font-bold text-slate-300">{items.filter((i) => !i.has_mapping).length}</div>
                    <div className="text-xs text-slate-400 mt-1">No Mapping</div>
                </div>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                {loading ? (
                    <div className="flex flex-col items-center justify-center p-20 gap-4">
                        <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
                        <p className="text-sm text-slate-500">Checking Zoho integrations...</p>
                    </div>
                ) : items.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-20 gap-4">
                        <Info className="w-8 h-8 text-slate-600" />
                        <p className="text-sm text-slate-500">No Zoho integrations configured.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-white/5 text-slate-400 font-medium">
                                <tr>
                                    <th className="px-5 py-3">Workspace</th>
                                    <th className="px-5 py-3">Status</th>
                                    <th className="px-5 py-3">Has Mapping</th>
                                    <th className="px-5 py-3">Connected At</th>
                                    <th className="px-5 py-3">Last Checked</th>
                                    <th className="px-5 py-3">Last Error</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5 text-slate-300">
                                {items.map((item, i) => (
                                    <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                                        <td className="px-5 py-4 text-xs font-mono text-amber-500">{item.workspace_id?.slice(0, 12)}...</td>
                                        <td className="px-5 py-4"><StatusBadge status={item.status} /></td>
                                        <td className="px-5 py-4">
                                            {item.has_mapping ? (
                                                <CheckCircle className="w-4 h-4 text-emerald-400" />
                                            ) : (
                                                <XCircle className="w-4 h-4 text-slate-600" />
                                            )}
                                        </td>
                                        <td className="px-5 py-4 text-slate-500 text-xs">
                                            {item.connected_at ? new Date(item.connected_at).toLocaleDateString() : "—"}
                                        </td>
                                        <td className="px-5 py-4 text-slate-500 text-xs">
                                            {item.last_checked_at ? new Date(item.last_checked_at).toLocaleString() : "—"}
                                        </td>
                                        <td className="px-5 py-4 text-red-400 text-xs max-w-[180px] truncate">
                                            {item.last_error || "—"}
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
    if (s === "connected") return (
        <span className="inline-flex items-center gap-1 text-emerald-400 text-[10px] font-bold uppercase">
            <CheckCircle className="w-3 h-3" /> connected
        </span>
    );
    if (s === "error") return (
        <span className="inline-flex items-center gap-1 text-red-400 text-[10px] font-bold uppercase">
            <XCircle className="w-3 h-3" /> error
        </span>
    );
    return (
        <span className="inline-flex items-center gap-1 text-slate-400 text-[10px] font-bold uppercase">
            <AlertCircle className="w-3 h-3" /> {s || "unknown"}
        </span>
    );
}
