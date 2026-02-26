"use client";

import { useEffect, useState, useCallback } from "react";
import { apiClient } from "@/lib/api";
import { Loader2, AlertCircle, ChevronLeft, ChevronRight, Search, Filter } from "lucide-react";

interface AuditEntry {
    id: string;
    actor_user_id?: string | null;
    actor_type?: string | null;
    action: string;
    entity_type: string;
    entity_id: string;
    outcome?: string | null;
    metadata_json?: Record<string, unknown> | null;
    correlation_id?: string | null;
    ip_address?: string | null;
    request_path?: string | null;
    request_method?: string | null;
    error_code?: string | null;
    error_message?: string | null;
    created_at: string;
}

function formatDate(iso: string) {
    try {
        return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
    } catch {
        return iso;
    }
}

function OutcomeBadge({ outcome }: { outcome?: string | null }) {
    if (!outcome) return null;
    const cls = outcome === "success"
        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
        : "bg-red-50 text-red-700 border-red-200";
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border ${cls}`}>
            {outcome}
        </span>
    );
}

function ActionBadge({ action }: { action: string }) {
    const colorMap: Record<string, string> = {
        user_login: "bg-blue-50 text-blue-700 border-blue-200",
        user_signup: "bg-indigo-50 text-indigo-700 border-indigo-200",
        workspace_create: "bg-violet-50 text-violet-700 border-violet-200",
        workspace_invite: "bg-purple-50 text-purple-700 border-purple-200",
        automation_create: "bg-amber-50 text-amber-700 border-amber-200",
        automation_publish: "bg-amber-50 text-amber-700 border-amber-200",
        integration_connect: "bg-emerald-50 text-emerald-700 border-emerald-200",
        integration_disconnect: "bg-rose-50 text-rose-700 border-rose-200",
        dispatch_trigger: "bg-cyan-50 text-cyan-700 border-cyan-200",
        inbox_reply: "bg-teal-50 text-teal-700 border-teal-200",
        inbox_status_change: "bg-sky-50 text-sky-700 border-sky-200",
    };
    const cls = colorMap[action] || "bg-slate-50 text-slate-600 border-slate-200";
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border ${cls}`}>
            {action.replace(/_/g, " ")}
        </span>
    );
}

const PAGE_SIZE = 25;

export default function LogsPage() {
    const [entries, setEntries] = useState<AuditEntry[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [expanded, setExpanded] = useState<string | null>(null);
    const [actionFilter, setActionFilter] = useState("");
    const [outcomeFilter, setOutcomeFilter] = useState("");

    const load = useCallback(async (p: number) => {
        setLoading(true);
        setError(null);
        const qs = new URLSearchParams();
        qs.set("skip", String(p * PAGE_SIZE));
        qs.set("limit", String(PAGE_SIZE));
        if (actionFilter) qs.set("action", actionFilter);
        if (outcomeFilter) qs.set("outcome", outcomeFilter);

        const res = await apiClient.get<{ items: AuditEntry[]; total: number }>(`/audit-logs?${qs.toString()}`);
        if (res.success && res.data) {
            setEntries(res.data.items);
            setTotal(res.data.total);
        } else {
            setError(res.error || "Failed to load activity log");
        }
        setLoading(false);
    }, [actionFilter, outcomeFilter]);

    useEffect(() => { load(page); }, [load, page]);

    const totalPages = Math.ceil(total / PAGE_SIZE);

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold tracking-tight text-slate-900">Activity Log</h1>
                <p className="text-slate-500 text-sm mt-1">
                    {total} events recorded in this workspace
                </p>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap gap-3">
                <select
                    value={actionFilter}
                    onChange={(e) => { setActionFilter(e.target.value); setPage(0); }}
                    className="px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm text-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                    <option value="">All Actions</option>
                    <option value="workspace_create">Workspace Create</option>
                    <option value="workspace_invite">Workspace Invite</option>
                    <option value="workspace_member_remove">Member Remove</option>
                    <option value="workspace_role_change">Role Change</option>
                    <option value="automation_create">Automation Create</option>
                    <option value="automation_publish">Automation Publish</option>
                    <option value="integration_connect">Integration Connect</option>
                    <option value="integration_disconnect">Integration Disconnect</option>
                    <option value="dispatch_trigger">Dispatch Trigger</option>
                    <option value="inbox_reply">Inbox Reply</option>
                    <option value="inbox_status_change">Inbox Status Change</option>
                    <option value="update_workspace_settings">Settings Update</option>
                </select>
                <select
                    value={outcomeFilter}
                    onChange={(e) => { setOutcomeFilter(e.target.value); setPage(0); }}
                    className="px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm text-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                    <option value="">All Outcomes</option>
                    <option value="success">Success</option>
                    <option value="failure">Failure</option>
                </select>
            </div>

            {error && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    {error}
                </div>
            )}

            {loading ? (
                <div className="flex items-center justify-center h-48">
                    <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
                </div>
            ) : entries.length === 0 ? (
                <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
                    No activity log entries yet.
                </div>
            ) : (
                <div className="space-y-2">
                    {entries.map((entry) => (
                        <div
                            key={entry.id}
                            className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm"
                        >
                            <div
                                className="flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-slate-50 transition-colors"
                                onClick={() => setExpanded(expanded === entry.id ? null : entry.id)}
                            >
                                <ActionBadge action={entry.action} />
                                <OutcomeBadge outcome={entry.outcome} />
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm text-slate-900 font-medium truncate">
                                        {entry.entity_type}:{" "}
                                        <span className="font-mono text-slate-500 text-xs">{entry.entity_id}</span>
                                    </p>
                                </div>
                                <p className="text-xs text-slate-400 flex-shrink-0 hidden sm:block">
                                    {formatDate(entry.created_at)}
                                </p>
                            </div>

                            {expanded === entry.id && (
                                <div className="border-t border-slate-100 px-4 py-3 bg-slate-50">
                                    <pre className="text-xs text-slate-600 overflow-x-auto whitespace-pre-wrap">
                                        {JSON.stringify({
                                            id: entry.id,
                                            actor_user_id: entry.actor_user_id,
                                            actor_type: entry.actor_type,
                                            outcome: entry.outcome,
                                            ip_address: entry.ip_address,
                                            request_method: entry.request_method,
                                            request_path: entry.request_path,
                                            correlation_id: entry.correlation_id,
                                            error_code: entry.error_code,
                                            error_message: entry.error_message,
                                            metadata: entry.metadata_json,
                                            created_at: entry.created_at,
                                        }, null, 2)}
                                    </pre>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {totalPages > 1 && (
                <div className="flex items-center justify-between pt-2">
                    <p className="text-xs text-slate-500">
                        Page {page + 1} of {totalPages}
                    </p>
                    <div className="flex gap-2">
                        <button
                            disabled={page === 0}
                            onClick={() => setPage((p) => p - 1)}
                            className="p-2 rounded-lg bg-white border border-slate-200 text-slate-500 hover:text-slate-900 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        <button
                            disabled={page >= totalPages - 1}
                            onClick={() => setPage((p) => p + 1)}
                            className="p-2 rounded-lg bg-white border border-slate-200 text-slate-500 hover:text-slate-900 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
