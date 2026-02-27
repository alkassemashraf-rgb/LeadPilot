"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import { Send, Loader2, Info, RefreshCw, RotateCcw, XCircle } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useCatalog } from "@/lib/catalog";

export default function AdminDispatchPage() {
    const { data: deliveryStatuses } = useCatalog("message-delivery-statuses");
    const [items, setItems] = useState<any[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState("");
    const [actionLoading, setActionLoading] = useState<string | null>(null);

    const load = async () => {
        setLoading(true);
        const res = await adminApi.getDispatchQueue({ limit: 100 });
        if (res.success && res.data) {
            const filtered = status
                ? res.data.items.filter((i: any) => i.delivery_status === status)
                : res.data.items;
            setItems(filtered);
            setTotal(res.data.total);
        } else {
            toast.error(res.error || "Failed to load dispatch queue");
        }
        setLoading(false);
    };

    useEffect(() => { load(); }, [status]);

    const handleRetry = async (messageId: string) => {
        setActionLoading(messageId + ":retry");
        const res = await adminApi.retryDispatch(messageId);
        if (res.success) {
            toast.success("Message re-queued for dispatch");
            load();
        } else {
            toast.error(res.error || "Retry failed");
        }
        setActionLoading(null);
    };

    const handleDeadLetter = async (messageId: string) => {
        if (!confirm("Mark this message as permanently failed (dead-letter)?")) return;
        setActionLoading(messageId + ":dl");
        const res = await adminApi.deadLetterDispatch(messageId);
        if (res.success) {
            toast.success("Message marked as dead-letter");
            load();
        } else {
            toast.error(res.error || "Dead-letter failed");
        }
        setActionLoading(null);
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Send className="w-6 h-6 text-amber-400" />
                        Dispatch Queue
                    </h1>
                    <p className="text-slate-400 text-sm mt-1">{total} messages total</p>
                </div>
                <button
                    onClick={load}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-sm transition-colors"
                >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                </button>
            </div>

            <div className="flex gap-4">
                <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value)}
                    className="bg-white/5 border border-white/10 text-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50"
                >
                    <option value="" className="bg-slate-900">All Statuses</option>
                    {deliveryStatuses?.map((s) => (
                        <option key={s.key} value={s.key.toUpperCase()} className="bg-slate-900">{s.label}</option>
                    ))}
                </select>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                {loading ? (
                    <div className="flex flex-col items-center justify-center p-20 gap-4">
                        <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
                        <p className="text-sm text-slate-500">Loading dispatch queue...</p>
                    </div>
                ) : items.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-20 gap-4">
                        <Info className="w-8 h-8 text-slate-600" />
                        <p className="text-sm text-slate-500">No messages found.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-white/5 text-slate-400 font-medium">
                                <tr>
                                    <th className="px-5 py-3">Message ID</th>
                                    <th className="px-5 py-3">Workspace</th>
                                    <th className="px-5 py-3">Status</th>
                                    <th className="px-5 py-3">Attempts</th>
                                    <th className="px-5 py-3">Last Error</th>
                                    <th className="px-5 py-3">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5 text-slate-300">
                                {items.map((item) => (
                                    <tr key={item.id} className="hover:bg-white/[0.02] transition-colors">
                                        <td className="px-5 py-4 text-xs font-mono text-amber-500">{item.id?.slice(0, 12)}...</td>
                                        <td className="px-5 py-4 text-xs font-mono">{item.workspace_id?.slice(0, 8)}...</td>
                                        <td className="px-5 py-4"><StatusBadge status={item.delivery_status} /></td>
                                        <td className="px-5 py-4 text-slate-400">{item.attempt_count ?? 0}</td>
                                        <td className="px-5 py-4 text-red-400 text-xs max-w-[180px] truncate">{item.last_error || "—"}</td>
                                        <td className="px-5 py-4">
                                            <div className="flex items-center gap-3">
                                                {item.delivery_status !== "SENT" && (
                                                    <button
                                                        onClick={() => handleRetry(item.id)}
                                                        disabled={!!actionLoading}
                                                        className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition-colors disabled:opacity-50"
                                                    >
                                                        <RotateCcw className={cn("w-3 h-3", actionLoading === item.id + ":retry" && "animate-spin")} />
                                                        Retry
                                                    </button>
                                                )}
                                                {item.delivery_status !== "FAILED" && (
                                                    <button
                                                        onClick={() => handleDeadLetter(item.id)}
                                                        disabled={!!actionLoading}
                                                        className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 transition-colors disabled:opacity-50"
                                                    >
                                                        <XCircle className="w-3 h-3" />
                                                        Dead-Letter
                                                    </button>
                                                )}
                                            </div>
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
    const map: Record<string, string> = {
        sent: "text-emerald-400",
        failed: "text-red-400",
        pending: "text-amber-400",
        sending: "text-blue-400",
    };
    return (
        <span className={cn("text-[10px] font-bold uppercase", map[s] || "text-slate-400")}>{s || "unknown"}</span>
    );
}
