"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import { Mail, Loader2, Info, RefreshCw, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// Source: backend/app/core/catalog_registry.py — EMAIL_OUTBOX_STATUSES / EMAIL_TYPES
const STATUS_OPTIONS = ["", "PENDING", "SENT", "FAILED", "PROCESSING"];
const EMAIL_TYPE_OPTIONS = ["", "welcome", "verify_email", "password_reset", "invite"];

export default function AdminEmailLogsPage() {
    const [items, setItems] = useState<any[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState("");
    const [emailType, setEmailType] = useState("");
    const [retrying, setRetrying] = useState<string | null>(null);

    const load = async () => {
        setLoading(true);
        const res = await adminApi.getEmailLogs({ status: status || undefined, email_type: emailType || undefined });
        if (res.success && res.data) {
            setItems(res.data.items);
            setTotal(res.data.total);
        } else {
            toast.error(res.error || "Failed to load email logs");
        }
        setLoading(false);
    };

    useEffect(() => { load(); }, [status, emailType]);

    const handleRetry = async (outboxId: string) => {
        setRetrying(outboxId);
        const res = await adminApi.retryEmail(outboxId);
        if (res.success) {
            toast.success("Email re-queued successfully");
            load();
        } else {
            toast.error(res.error || "Retry failed");
        }
        setRetrying(null);
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Mail className="w-6 h-6 text-amber-400" />
                        Email Logs
                    </h1>
                    <p className="text-slate-400 text-sm mt-1">
                        {total} total entries across all workspaces
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

            {/* Filters */}
            <div className="flex gap-4 flex-wrap">
                <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value)}
                    className="bg-white/5 border border-white/10 text-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50"
                >
                    {STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s} className="bg-slate-900">{s || "All Statuses"}</option>
                    ))}
                </select>
                <select
                    value={emailType}
                    onChange={(e) => setEmailType(e.target.value)}
                    className="bg-white/5 border border-white/10 text-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50"
                >
                    {EMAIL_TYPE_OPTIONS.map((t) => (
                        <option key={t} value={t} className="bg-slate-900">{t || "All Types"}</option>
                    ))}
                </select>
            </div>

            {/* Table */}
            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                {loading ? (
                    <div className="flex flex-col items-center justify-center p-20 gap-4">
                        <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
                        <p className="text-sm text-slate-500">Loading email logs...</p>
                    </div>
                ) : items.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-20 gap-4">
                        <Info className="w-8 h-8 text-slate-600" />
                        <p className="text-sm text-slate-500">No email log entries found.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-white/5 text-slate-400 font-medium">
                                <tr>
                                    <th className="px-5 py-3">Recipient</th>
                                    <th className="px-5 py-3">Type</th>
                                    <th className="px-5 py-3">Status</th>
                                    <th className="px-5 py-3">Attempts</th>
                                    <th className="px-5 py-3">Sent At</th>
                                    <th className="px-5 py-3">Error</th>
                                    <th className="px-5 py-3">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5 text-slate-300">
                                {items.map((item) => (
                                    <tr key={item.id} className="hover:bg-white/[0.02] transition-colors">
                                        <td className="px-5 py-4 text-white font-medium">{item.recipient}</td>
                                        <td className="px-5 py-4">
                                            <span className="text-xs font-mono bg-white/10 px-2 py-0.5 rounded">{item.email_type}</span>
                                        </td>
                                        <td className="px-5 py-4"><StatusBadge status={item.status} /></td>
                                        <td className="px-5 py-4 text-slate-400">{item.attempt_count ?? 0}</td>
                                        <td className="px-5 py-4 text-slate-500 text-xs">
                                            {item.sent_at ? new Date(item.sent_at).toLocaleString() : "—"}
                                        </td>
                                        <td className="px-5 py-4 text-red-400 text-xs max-w-[200px] truncate">
                                            {item.error_message || "—"}
                                        </td>
                                        <td className="px-5 py-4">
                                            {(item.status === "FAILED" || item.status === "PENDING") && item.outbox_id && (
                                                <button
                                                    onClick={() => handleRetry(item.outbox_id)}
                                                    disabled={retrying === item.outbox_id}
                                                    className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition-colors disabled:opacity-50"
                                                >
                                                    <RotateCcw className={cn("w-3 h-3", retrying === item.outbox_id && "animate-spin")} />
                                                    Retry
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
    const map: Record<string, string> = {
        sent: "text-emerald-400",
        failed: "text-red-400",
        pending: "text-amber-400",
        processing: "text-blue-400",
    };
    return (
        <span className={cn("text-[10px] font-bold uppercase", map[s] || "text-slate-400")}>
            {s || "unknown"}
        </span>
    );
}
