"use client";

import { useEffect, useState, useCallback } from "react";
import { adminApi, RuntimeEventEntry } from "@/lib/admin-api";
import { useCatalog, type CatalogEntry } from "@/lib/catalog";
import { Loader2, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, Copy, Check, AlertCircle, CheckCircle, MinusCircle } from "lucide-react";

function formatDate(iso: string) {
    try {
        return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "medium" });
    } catch {
        return iso;
    }
}

const SOURCE_COLORS: Record<string, string> = {
    webhook: "bg-blue-500/20 text-blue-300 border-blue-500/30",
    runtime: "bg-purple-500/20 text-purple-300 border-purple-500/30",
    dispatch: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    email: "bg-orange-500/20 text-orange-300 border-orange-500/30",
    zoho: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
    inbox: "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

function SourceBadge({ source }: { source: string }) {
    const cls = SOURCE_COLORS[source] || SOURCE_COLORS.inbox;
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border ${cls}`}>
            {source}
        </span>
    );
}

function OutcomeBadge({ outcome }: { outcome?: string | null }) {
    if (!outcome) return <span className="text-[10px] text-slate-500">—</span>;
    switch (outcome) {
        case "success":
            return (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border bg-emerald-500/20 text-emerald-300 border-emerald-500/30">
                    <CheckCircle className="w-3 h-3" /> success
                </span>
            );
        case "failure":
            return (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border bg-red-500/20 text-red-300 border-red-500/30">
                    <AlertCircle className="w-3 h-3" /> failure
                </span>
            );
        case "skipped":
            return (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border bg-amber-500/20 text-amber-300 border-amber-500/30">
                    <MinusCircle className="w-3 h-3" /> skipped
                </span>
            );
        default:
            return <span className="text-[10px] text-slate-500">{outcome}</span>;
    }
}

function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false);
    return (
        <button
            onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
            className="p-0.5 hover:bg-white/10 rounded transition-colors"
            title="Copy"
        >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-slate-500" />}
        </button>
    );
}

export default function AdminRuntimeEventsPage() {
    const { data: eventSources } = useCatalog("event-sources");
    const { data: eventOutcomes } = useCatalog("event-outcomes");
    const [events, setEvents] = useState<RuntimeEventEntry[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [skip, setSkip] = useState(0);
    const limit = 50;
    const [expandedId, setExpandedId] = useState<string | null>(null);

    // Filters
    const [sourceFilter, setSourceFilter] = useState("");
    const [eventTypeFilter, setEventTypeFilter] = useState("");
    const [outcomeFilter, setOutcomeFilter] = useState("");
    const [workspaceIdFilter, setWorkspaceIdFilter] = useState("");

    const fetchEvents = useCallback(async () => {
        setLoading(true);
        try {
            const res = await adminApi.getRuntimeEvents({
                skip,
                limit,
                source: sourceFilter || undefined,
                event_type: eventTypeFilter || undefined,
                outcome: outcomeFilter || undefined,
                workspace_id: workspaceIdFilter || undefined,
            });
            setEvents(res.data?.items || []);
            setTotal(res.data?.total || 0);
        } catch {
            setEvents([]);
        } finally {
            setLoading(false);
        }
    }, [skip, sourceFilter, eventTypeFilter, outcomeFilter, workspaceIdFilter]);

    useEffect(() => { fetchEvents(); }, [fetchEvents]);

    const totalPages = Math.ceil(total / limit);
    const currentPage = Math.floor(skip / limit) + 1;

    return (
        <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Runtime Events</h1>
                    <p className="text-sm text-slate-400 mt-1">High-volume system event trail across all subsystems</p>
                </div>
                <div className="text-sm text-slate-400">{total} total events</div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap gap-3">
                <select
                    value={sourceFilter}
                    onChange={(e) => { setSourceFilter(e.target.value); setSkip(0); }}
                    className="bg-slate-800 border border-slate-700 rounded-lg text-sm text-white px-3 py-2 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500"
                >
                    <option value="">All Sources</option>
                    {(eventSources || []).map((s) => (
                        <option key={s.key} value={s.key}>{s.label}</option>
                    ))}
                </select>
                <input
                    type="text"
                    placeholder="Event type..."
                    value={eventTypeFilter}
                    onChange={(e) => { setEventTypeFilter(e.target.value); setSkip(0); }}
                    className="bg-slate-800 border border-slate-700 rounded-lg text-sm text-white px-3 py-2 w-48 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 placeholder:text-slate-500"
                />
                <select
                    value={outcomeFilter}
                    onChange={(e) => { setOutcomeFilter(e.target.value); setSkip(0); }}
                    className="bg-slate-800 border border-slate-700 rounded-lg text-sm text-white px-3 py-2 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500"
                >
                    <option value="">All Outcomes</option>
                    {(eventOutcomes || []).map((o) => (
                        <option key={o.key} value={o.key}>{o.label}</option>
                    ))}
                </select>
                <input
                    type="text"
                    placeholder="Workspace ID..."
                    value={workspaceIdFilter}
                    onChange={(e) => { setWorkspaceIdFilter(e.target.value); setSkip(0); }}
                    className="bg-slate-800 border border-slate-700 rounded-lg text-sm text-white px-3 py-2 w-64 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 placeholder:text-slate-500"
                />
            </div>

            {/* Table */}
            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                </div>
            ) : (
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-slate-700/50 text-left text-xs uppercase tracking-wider text-slate-400">
                                <th className="px-4 py-3 w-8"></th>
                                <th className="px-4 py-3">Time</th>
                                <th className="px-4 py-3">Source</th>
                                <th className="px-4 py-3">Event Type</th>
                                <th className="px-4 py-3">Outcome</th>
                                <th className="px-4 py-3">Duration</th>
                                <th className="px-4 py-3">Correlation ID</th>
                            </tr>
                        </thead>
                        <tbody>
                            {events.map((evt) => {
                                const isExpanded = expandedId === evt.id;
                                return (
                                    <>
                                        <tr
                                            key={evt.id}
                                            className="border-b border-slate-700/30 hover:bg-slate-700/20 cursor-pointer transition-colors"
                                            onClick={() => setExpandedId(isExpanded ? null : evt.id)}
                                        >
                                            <td className="px-4 py-3">
                                                {isExpanded ? (
                                                    <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
                                                ) : (
                                                    <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                                                )}
                                            </td>
                                            <td className="px-4 py-3 text-slate-300 whitespace-nowrap text-xs">
                                                {formatDate(evt.created_at)}
                                            </td>
                                            <td className="px-4 py-3"><SourceBadge source={evt.source} /></td>
                                            <td className="px-4 py-3 text-slate-200 font-mono text-xs">{evt.event_type}</td>
                                            <td className="px-4 py-3"><OutcomeBadge outcome={evt.outcome} /></td>
                                            <td className="px-4 py-3 text-slate-400 font-mono text-xs">
                                                {evt.duration_ms !== null && evt.duration_ms !== undefined ? `${evt.duration_ms}ms` : "—"}
                                            </td>
                                            <td className="px-4 py-3">
                                                {evt.correlation_id ? (
                                                    <div className="flex items-center gap-1">
                                                        <span className="font-mono text-[10px] text-slate-500 truncate max-w-[120px]">
                                                            {evt.correlation_id}
                                                        </span>
                                                        <CopyButton text={evt.correlation_id} />
                                                    </div>
                                                ) : (
                                                    <span className="text-slate-600">—</span>
                                                )}
                                            </td>
                                        </tr>
                                        {isExpanded && (
                                            <tr key={`${evt.id}-detail`} className="bg-slate-900/50">
                                                <td colSpan={7} className="px-6 py-4">
                                                    <div className="grid grid-cols-2 gap-4 text-xs">
                                                        <div>
                                                            <span className="text-slate-500 font-semibold uppercase tracking-wider text-[10px]">Event ID</span>
                                                            <div className="text-slate-300 font-mono mt-1 flex items-center gap-1">
                                                                {evt.id} <CopyButton text={evt.id} />
                                                            </div>
                                                        </div>
                                                        <div>
                                                            <span className="text-slate-500 font-semibold uppercase tracking-wider text-[10px]">Workspace</span>
                                                            <div className="text-slate-300 font-mono mt-1">
                                                                {evt.workspace_id || "—"}
                                                            </div>
                                                        </div>
                                                        {evt.error_message && (
                                                            <div className="col-span-2">
                                                                <span className="text-slate-500 font-semibold uppercase tracking-wider text-[10px]">Error</span>
                                                                <div className="text-red-400 bg-red-900/20 p-2 rounded mt-1 font-mono break-all">
                                                                    {evt.error_message}
                                                                </div>
                                                            </div>
                                                        )}
                                                        {evt.related_ids && Object.keys(evt.related_ids).length > 0 && (
                                                            <div className="col-span-2">
                                                                <span className="text-slate-500 font-semibold uppercase tracking-wider text-[10px]">Related IDs</span>
                                                                <div className="mt-1 flex flex-wrap gap-2">
                                                                    {Object.entries(evt.related_ids).map(([k, v]) => (
                                                                        <span key={k} className="bg-slate-800 px-2 py-1 rounded text-[10px] font-mono text-slate-300 border border-slate-700">
                                                                            {k}: {v}
                                                                        </span>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}
                                                        {evt.payload && Object.keys(evt.payload).length > 0 && (
                                                            <div className="col-span-2">
                                                                <span className="text-slate-500 font-semibold uppercase tracking-wider text-[10px]">Payload</span>
                                                                <pre className="bg-slate-800 p-3 rounded mt-1 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-48 border border-slate-700">
                                                                    {JSON.stringify(evt.payload, null, 2)}
                                                                </pre>
                                                            </div>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </>
                                );
                            })}
                        </tbody>
                    </table>

                    {events.length === 0 && (
                        <div className="py-12 text-center text-slate-500 text-sm">No runtime events found</div>
                    )}
                </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">
                        Page {currentPage} of {totalPages}
                    </span>
                    <div className="flex gap-2">
                        <button
                            disabled={skip === 0}
                            onClick={() => setSkip(Math.max(0, skip - limit))}
                            className="flex items-center gap-1 px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronLeft className="w-4 h-4" /> Previous
                        </button>
                        <button
                            disabled={skip + limit >= total}
                            onClick={() => setSkip(skip + limit)}
                            className="flex items-center gap-1 px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                            Next <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
