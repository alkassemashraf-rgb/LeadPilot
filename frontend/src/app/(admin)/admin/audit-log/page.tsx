"use client";

import { useEffect, useState, useCallback } from "react";
import { adminApi, AuditLogEntry } from "@/lib/admin-api";
import { Loader2, AlertCircle, ChevronLeft, ChevronRight } from "lucide-react";

function formatDate(iso: string) {
    try {
        return new Date(iso).toLocaleString(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
        });
    } catch {
        return iso;
    }
}

function ActionBadge({ action }: { action: string }) {
    const colorMap: Record<string, string> = {
        module_toggle: "bg-violet-500/20 text-violet-300 border-violet-500/30",
        login: "bg-blue-500/20 text-blue-300 border-blue-500/30",
        logout: "bg-slate-500/20 text-slate-400 border-slate-500/30",
    };
    const cls = colorMap[action] || "bg-slate-500/20 text-slate-400 border-slate-500/30";
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border ${cls}`}>
            {action}
        </span>
    );
}

const PAGE_SIZE = 20;

export default function AuditLogPage() {
    const [entries, setEntries] = useState<AuditLogEntry[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [expanded, setExpanded] = useState<string | null>(null);

    const load = useCallback(async (p: number) => {
        setLoading(true);
        const res = await adminApi.getAuditLog({ skip: p * PAGE_SIZE, limit: PAGE_SIZE });
        if (res.success && res.data) {
            setEntries(res.data.items);
            setTotal(res.data.total);
        } else {
            setError(res.error || "Failed to load audit log");
        }
        setLoading(false);
    }, []);

    useEffect(() => {
        load(page);
    }, [load, page]);

    const totalPages = Math.ceil(total / PAGE_SIZE);

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-white">Audit Log</h1>
                <p className="text-slate-400 text-sm mt-1">
                    {total} total entries — all admin actions are recorded here
                </p>
            </div>

            {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-400 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    {error}
                </div>
            )}

            {loading ? (
                <div className="flex items-center justify-center h-48">
                    <Loader2 className="w-6 h-6 text-violet-400 animate-spin" />
                </div>
            ) : entries.length === 0 ? (
                <div className="bg-white/5 border border-white/10 rounded-xl p-8 text-center text-slate-500">
                    No audit log entries yet.
                </div>
            ) : (
                <div className="space-y-2">
                    {entries.map((entry) => (
                        <div
                            key={entry.id}
                            className="bg-white/5 border border-white/10 rounded-xl overflow-hidden"
                        >
                            <div
                                className="flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-white/5 transition-colors"
                                onClick={() =>
                                    setExpanded(expanded === entry.id ? null : entry.id)
                                }
                            >
                                <ActionBadge action={entry.action} />
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm text-white font-medium truncate">
                                        {entry.entity_type}:{" "}
                                        <span className="font-mono text-slate-300">
                                            {entry.entity_id}
                                        </span>
                                    </p>
                                    <p className="text-[10px] text-slate-500 font-mono mt-0.5 truncate">
                                        actor: {entry.actor_user_id}
                                    </p>
                                </div>
                                <p className="text-xs text-slate-500 flex-shrink-0 hidden sm:block">
                                    {formatDate(entry.created_at)}
                                </p>
                            </div>

                            {expanded === entry.id && (
                                <div className="border-t border-white/10 px-4 py-3 bg-black/20">
                                    <pre className="text-xs text-slate-300 overflow-x-auto whitespace-pre-wrap">
                                        {JSON.stringify(
                                            {
                                                id: entry.id,
                                                actor_user_id: entry.actor_user_id,
                                                workspace_id: entry.workspace_id,
                                                correlation_id: entry.correlation_id,
                                                created_at: entry.created_at,
                                                metadata: entry.metadata_json,
                                            },
                                            null,
                                            2
                                        )}
                                    </pre>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between pt-2">
                    <p className="text-xs text-slate-500">
                        Page {page + 1} of {totalPages}
                    </p>
                    <div className="flex gap-2">
                        <button
                            disabled={page === 0}
                            onClick={() => setPage((p) => p - 1)}
                            className="p-2 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        <button
                            disabled={page >= totalPages - 1}
                            onClick={() => setPage((p) => p + 1)}
                            className="p-2 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
