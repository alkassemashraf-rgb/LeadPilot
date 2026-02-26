"use client";

import { useEffect, useState, useCallback } from "react";
import { adminApi, AuditLogEntry } from "@/lib/admin-api";
import { Loader2, AlertCircle, ChevronLeft, ChevronRight, Copy, Check } from "lucide-react";

function formatDate(iso: string) {
    try {
        return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
    } catch {
        return iso;
    }
}

function OutcomeBadge({ outcome }: { outcome?: string | null }) {
    if (!outcome) return <span className="text-[10px] text-slate-500">—</span>;
    const cls = outcome === "success"
        ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
        : "bg-red-500/20 text-red-300 border-red-500/30";
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border ${cls}`}>
            {outcome}
        </span>
    );
}

function ActionBadge({ action }: { action: string }) {
    const colorMap: Record<string, string> = {
        user_login: "bg-blue-500/20 text-blue-300 border-blue-500/30",
        user_signup: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30",
        module_toggle: "bg-violet-500/20 text-violet-300 border-violet-500/30",
        workspace_module_set: "bg-violet-500/20 text-violet-300 border-violet-500/30",
        email_retry: "bg-amber-500/20 text-amber-300 border-amber-500/30",
        webhook_replay: "bg-orange-500/20 text-orange-300 border-orange-500/30",
        dispatch_retry: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
        dispatch_dead_letter: "bg-red-500/20 text-red-300 border-red-500/30",
        agency_create: "bg-purple-500/20 text-purple-300 border-purple-500/30",
    };
    const cls = colorMap[action] || "bg-slate-500/20 text-slate-400 border-slate-500/30";
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border ${cls}`}>
            {action.replace(/_/g, " ")}
        </span>
    );
}

function ActorTypeBadge({ type }: { type?: string | null }) {
    if (!type) return null;
    const cls = type === "admin"
        ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
        : "bg-slate-500/20 text-slate-400 border-slate-500/30";
    return (
        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium uppercase tracking-wider border ${cls}`}>
            {type}
        </span>
    );
}

function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false);
    const copy = async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };
    return (
        <button onClick={copy} className="p-1 rounded hover:bg-white/10 transition-colors" title="Copy">
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-slate-500" />}
        </button>
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

    // Filters
    const [actionFilter, setActionFilter] = useState("");
    const [actorTypeFilter, setActorTypeFilter] = useState("");
    const [outcomeFilter, setOutcomeFilter] = useState("");

    const load = useCallback(async (p: number) => {
        setLoading(true);
        setError(null);
        const params: Record<string, any> = { skip: p * PAGE_SIZE, limit: PAGE_SIZE };
        if (actionFilter) params.action = actionFilter;
        if (actorTypeFilter) params.actor_type = actorTypeFilter;
        if (outcomeFilter) params.outcome = outcomeFilter;

        const res = await adminApi.getAuditLog(params);
        if (res.success && res.data) {
            setEntries(res.data.items);
            setTotal(res.data.total);
        } else {
            setError(res.error || "Failed to load audit log");
        }
        setLoading(false);
    }, [actionFilter, actorTypeFilter, outcomeFilter]);

    useEffect(() => { load(page); }, [load, page]);

    const totalPages = Math.ceil(total / PAGE_SIZE);

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-white">Audit Log</h1>
                <p className="text-slate-400 text-sm mt-1">
                    {total} total entries — all system and user actions are recorded here
                </p>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap gap-3">
                <select
                    value={actionFilter}
                    onChange={(e) => { setActionFilter(e.target.value); setPage(0); }}
                    className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-slate-300 focus:ring-2 focus:ring-violet-500 focus:border-violet-500"
                >
                    <option value="">All Actions</option>
                    <option value="user_login">Login</option>
                    <option value="user_signup">Signup</option>
                    <option value="verify_email">Verify Email</option>
                    <option value="workspace_create">Workspace Create</option>
                    <option value="workspace_invite">Workspace Invite</option>
                    <option value="workspace_module_set">Module Set</option>
                    <option value="email_retry">Email Retry</option>
                    <option value="webhook_replay">Webhook Replay</option>
                    <option value="dispatch_retry">Dispatch Retry</option>
                    <option value="dispatch_dead_letter">Dispatch Dead Letter</option>
                    <option value="agency_create">Agency Create</option>
                    <option value="agency_member_invite">Agency Invite</option>
                    <option value="agency_workspace_create">Agency WS Create</option>
                    <option value="module_toggle">Module Toggle</option>
                    <option value="update_workspace_settings">WS Settings Update</option>
                    <option value="update_system_settings">System Settings Update</option>
                </select>
                <select
                    value={actorTypeFilter}
                    onChange={(e) => { setActorTypeFilter(e.target.value); setPage(0); }}
                    className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-slate-300 focus:ring-2 focus:ring-violet-500 focus:border-violet-500"
                >
                    <option value="">All Actor Types</option>
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                    <option value="system">System</option>
                </select>
                <select
                    value={outcomeFilter}
                    onChange={(e) => { setOutcomeFilter(e.target.value); setPage(0); }}
                    className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-slate-300 focus:ring-2 focus:ring-violet-500 focus:border-violet-500"
                >
                    <option value="">All Outcomes</option>
                    <option value="success">Success</option>
                    <option value="failure">Failure</option>
                </select>
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
                    No audit log entries match the current filters.
                </div>
            ) : (
                <div className="space-y-2">
                    {entries.map((entry) => (
                        <div
                            key={entry.id}
                            className="bg-white/5 border border-white/10 rounded-xl overflow-hidden"
                        >
                            <div
                                className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-white/5 transition-colors"
                                onClick={() => setExpanded(expanded === entry.id ? null : entry.id)}
                            >
                                <ActionBadge action={entry.action} />
                                <OutcomeBadge outcome={entry.outcome} />
                                <ActorTypeBadge type={entry.actor_type} />
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm text-white font-medium truncate">
                                        {entry.entity_type}:{" "}
                                        <span className="font-mono text-slate-300 text-xs">{entry.entity_id}</span>
                                    </p>
                                    <p className="text-[10px] text-slate-500 font-mono mt-0.5 truncate">
                                        actor: {entry.actor_user_id || "—"}
                                        {entry.ip_address && ` · ${entry.ip_address}`}
                                    </p>
                                </div>
                                <p className="text-xs text-slate-500 flex-shrink-0 hidden sm:block">
                                    {formatDate(entry.created_at)}
                                </p>
                            </div>

                            {expanded === entry.id && (
                                <div className="border-t border-white/10 px-4 py-3 bg-black/20">
                                    <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                                        <div>
                                            <span className="text-slate-500">Request: </span>
                                            <span className="text-slate-300 font-mono">
                                                {entry.request_method} {entry.request_path || "—"}
                                            </span>
                                        </div>
                                        <div>
                                            <span className="text-slate-500">IP: </span>
                                            <span className="text-slate-300 font-mono">{entry.ip_address || "—"}</span>
                                        </div>
                                        {entry.workspace_id && (
                                            <div>
                                                <span className="text-slate-500">Workspace: </span>
                                                <span className="text-slate-300 font-mono">{entry.workspace_id}</span>
                                            </div>
                                        )}
                                        {entry.agency_id && (
                                            <div>
                                                <span className="text-slate-500">Agency: </span>
                                                <span className="text-slate-300 font-mono">{entry.agency_id}</span>
                                            </div>
                                        )}
                                        {entry.correlation_id && (
                                            <div className="flex items-center gap-1">
                                                <span className="text-slate-500">Correlation: </span>
                                                <span className="text-slate-300 font-mono text-[10px]">{entry.correlation_id}</span>
                                                <CopyButton text={entry.correlation_id} />
                                            </div>
                                        )}
                                        {entry.error_code && (
                                            <div>
                                                <span className="text-slate-500">Error: </span>
                                                <span className="text-red-400 font-mono">{entry.error_code}</span>
                                            </div>
                                        )}
                                        {entry.error_message && (
                                            <div className="col-span-2">
                                                <span className="text-slate-500">Error message: </span>
                                                <span className="text-red-300">{entry.error_message}</span>
                                            </div>
                                        )}
                                    </div>
                                    {entry.metadata_json && Object.keys(entry.metadata_json).length > 0 && (
                                        <div>
                                            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Metadata</p>
                                            <pre className="text-xs text-slate-300 overflow-x-auto whitespace-pre-wrap bg-black/20 rounded p-2">
                                                {JSON.stringify(entry.metadata_json, null, 2)}
                                            </pre>
                                        </div>
                                    )}
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
