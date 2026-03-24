"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { adminApi, ExecutionTraceEvent } from "@/lib/admin-api";
import {
    Loader2,
    ChevronDown,
    ChevronUp,
    ArrowLeft,
    AlertCircle,
    CheckCircle,
    MinusCircle,
} from "lucide-react";

// ─── Helpers ──────────────────────────────────────────────────────────────

function formatTime(iso: string) {
    try {
        return new Date(iso).toLocaleTimeString(undefined, {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            fractionalSecondDigits: 3,
        });
    } catch {
        return iso;
    }
}

// Source → color mapping (extends existing runtime-events palette + ADK-specific)
const SOURCE_COLORS: Record<string, string> = {
    webhook: "bg-blue-500/20 text-blue-300 border-blue-500/30",
    runtime: "bg-green-500/20 text-green-300 border-green-500/30",
    adk: "bg-violet-500/20 text-violet-300 border-violet-500/30",
    adk_runner: "bg-green-500/20 text-green-300 border-green-500/30",
    dispatch: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    zoho: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
    inbox: "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

// Event type prefix → icon hint for visual grouping
function eventCategory(eventType: string): "agent" | "tool" | "runtime" | "error" | "other" {
    if (eventType.startsWith("agent.error") || eventType === "failure") return "error";
    if (eventType.startsWith("agent.")) return "agent";
    if (eventType.startsWith("tool.")) return "tool";
    if (eventType.startsWith("runtime.")) return "runtime";
    return "other";
}

function SourceBadge({ source }: { source: string }) {
    const cls = SOURCE_COLORS[source] || SOURCE_COLORS.inbox;
    return (
        <span
            className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border ${cls}`}
        >
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

// Left-side timeline dot color per category
const CATEGORY_DOT: Record<string, string> = {
    agent: "bg-violet-400",
    tool: "bg-orange-400",
    runtime: "bg-green-400",
    error: "bg-red-400",
    other: "bg-slate-500",
};

// ─── Page ─────────────────────────────────────────────────────────────────

export default function ExecutionTracePage() {
    const { executionId } = useParams<{ executionId: string }>();
    const router = useRouter();

    const [events, setEvents] = useState<ExecutionTraceEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [expandedId, setExpandedId] = useState<string | null>(null);

    useEffect(() => {
        if (!executionId) return;
        setLoading(true);
        adminApi
            .getExecutionTrace(executionId)
            .then((res) => setEvents(res.data?.events || []))
            .catch(() => setError("Failed to load execution trace"))
            .finally(() => setLoading(false));
    }, [executionId]);

    const shortId = executionId ? executionId.slice(0, 8) : "…";

    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <div className="flex items-start gap-4">
                <button
                    onClick={() => router.back()}
                    className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors mt-0.5"
                >
                    <ArrowLeft className="w-4 h-4" /> Back
                </button>
                <div>
                    <h1 className="text-2xl font-bold text-white">
                        Execution Trace
                    </h1>
                    <p className="text-sm text-slate-400 mt-1 font-mono">
                        {executionId}
                    </p>
                </div>
            </div>

            {/* Legend */}
            <div className="flex flex-wrap gap-3 text-[10px] text-slate-400 uppercase tracking-wider">
                {Object.entries(CATEGORY_DOT).map(([cat, dot]) => (
                    <span key={cat} className="flex items-center gap-1.5">
                        <span className={`w-2 h-2 rounded-full ${dot}`} />
                        {cat}
                    </span>
                ))}
            </div>

            {/* Content */}
            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="w-6 h-6 animate-spin text-violet-500" />
                </div>
            ) : error ? (
                <div className="py-12 text-center text-red-400 text-sm">{error}</div>
            ) : (
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-slate-700/50 text-left text-xs uppercase tracking-wider text-slate-400">
                                <th className="px-4 py-3 w-8"></th>
                                <th className="px-4 py-3 w-4"></th>
                                <th className="px-4 py-3">Time</th>
                                <th className="px-4 py-3">Source</th>
                                <th className="px-4 py-3">Event Type</th>
                                <th className="px-4 py-3">Outcome</th>
                                <th className="px-4 py-3">Duration</th>
                            </tr>
                        </thead>
                        <tbody>
                            {events.map((evt) => {
                                const isExpanded = expandedId === evt.id;
                                const cat = eventCategory(evt.event_type);
                                return (
                                    <>
                                        <tr
                                            key={evt.id}
                                            className="border-b border-slate-700/30 hover:bg-slate-700/20 cursor-pointer transition-colors"
                                            onClick={() =>
                                                setExpandedId(isExpanded ? null : evt.id)
                                            }
                                        >
                                            <td className="px-4 py-3">
                                                {isExpanded ? (
                                                    <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
                                                ) : (
                                                    <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                                                )}
                                            </td>
                                            <td className="px-2 py-3">
                                                <span
                                                    className={`block w-2 h-2 rounded-full ${CATEGORY_DOT[cat]}`}
                                                />
                                            </td>
                                            <td className="px-4 py-3 text-slate-300 whitespace-nowrap text-xs font-mono">
                                                {formatTime(evt.created_at)}
                                            </td>
                                            <td className="px-4 py-3">
                                                <SourceBadge source={evt.source} />
                                            </td>
                                            <td className="px-4 py-3 text-slate-200 font-mono text-xs">
                                                {evt.event_type}
                                            </td>
                                            <td className="px-4 py-3">
                                                <OutcomeBadge outcome={evt.outcome} />
                                            </td>
                                            <td className="px-4 py-3 text-slate-400 font-mono text-xs">
                                                {evt.duration_ms != null
                                                    ? `${evt.duration_ms}ms`
                                                    : "—"}
                                            </td>
                                        </tr>
                                        {isExpanded && (
                                            <tr
                                                key={`${evt.id}-detail`}
                                                className="bg-slate-900/50"
                                            >
                                                <td colSpan={7} className="px-6 py-4">
                                                    <div className="grid grid-cols-2 gap-4 text-xs">
                                                        <div>
                                                            <span className="text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                                                                Event ID
                                                            </span>
                                                            <div className="text-slate-300 font-mono mt-1">
                                                                {evt.id}
                                                            </div>
                                                        </div>
                                                        {evt.error_message && (
                                                            <div className="col-span-2">
                                                                <span className="text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                                                                    Error
                                                                </span>
                                                                <div className="text-red-400 bg-red-900/20 p-2 rounded mt-1 font-mono break-all">
                                                                    {evt.error_message}
                                                                </div>
                                                            </div>
                                                        )}
                                                        {evt.payload &&
                                                            Object.keys(evt.payload).length > 0 && (
                                                                <div className="col-span-2">
                                                                    <span className="text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                                                                        Payload
                                                                    </span>
                                                                    <pre className="bg-slate-800 p-3 rounded mt-1 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-48 border border-slate-700">
                                                                        {JSON.stringify(
                                                                            evt.payload,
                                                                            null,
                                                                            2
                                                                        )}
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
                        <div className="py-12 text-center text-slate-500 text-sm">
                            No events recorded for this execution
                        </div>
                    )}
                </div>
            )}

            {events.length > 0 && (
                <p className="text-xs text-slate-500 text-right">
                    {events.length} event{events.length !== 1 ? "s" : ""} — instance{" "}
                    <span className="font-mono">{shortId}…</span>
                </p>
            )}
        </div>
    );
}
