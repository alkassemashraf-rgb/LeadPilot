"use client";

import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api";
import { ChevronDown, ChevronRight, Clock, AlertCircle, CheckCircle, MinusCircle } from "lucide-react";
import { cn } from "@/lib/utils";

type RuntimeEvent = {
    id: string;
    event_type: string;
    source: string;
    correlation_id?: string | null;
    related_ids?: Record<string, string> | null;
    payload?: Record<string, unknown> | null;
    outcome?: string | null;
    error_message?: string | null;
    duration_ms?: number | null;
    created_at: string;
};

const SOURCE_COLORS: Record<string, string> = {
    webhook: "bg-blue-100 text-blue-700 border-blue-200",
    runtime: "bg-purple-100 text-purple-700 border-purple-200",
    dispatch: "bg-emerald-100 text-emerald-700 border-emerald-200",
    email: "bg-orange-100 text-orange-700 border-orange-200",
    zoho: "bg-cyan-100 text-cyan-700 border-cyan-200",
    inbox: "bg-slate-100 text-slate-600 border-slate-200",
};

function OutcomeBadge({ outcome }: { outcome?: string | null }) {
    if (!outcome) return null;
    switch (outcome) {
        case "success":
            return <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />;
        case "failure":
            return <AlertCircle className="w-3.5 h-3.5 text-red-500" />;
        case "skipped":
            return <MinusCircle className="w-3.5 h-3.5 text-amber-500" />;
        default:
            return null;
    }
}

export default function TimelinePanel({ conversationId }: { conversationId: string }) {
    const [events, setEvents] = useState<RuntimeEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState<string | null>(null);

    useEffect(() => {
        if (!conversationId) return;
        setLoading(true);
        apiClient
            .get<{ items: RuntimeEvent[]; total: number }>(
                `/support/timeline?conversation_id=${conversationId}&limit=100`
            )
            .then((res) => setEvents(res.data?.items || []))
            .catch(() => setEvents([]))
            .finally(() => setLoading(false));
    }, [conversationId]);

    if (loading) {
        return (
            <div className="p-4 text-center text-slate-400 text-sm">Loading timeline...</div>
        );
    }

    if (events.length === 0) {
        return (
            <div className="p-6 text-center text-slate-400 text-sm">
                <Clock className="w-8 h-8 mx-auto mb-2 opacity-30" />
                No runtime events for this conversation
            </div>
        );
    }

    return (
        <div className="space-y-1 p-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 px-1 mb-3">
                Event Timeline ({events.length})
            </h3>
            {events.map((evt) => {
                const isExpanded = expandedId === evt.id;
                const colorClass = SOURCE_COLORS[evt.source] || SOURCE_COLORS.inbox;

                return (
                    <div key={evt.id} className="border border-slate-100 rounded-lg overflow-hidden">
                        <button
                            className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-slate-50 transition-colors"
                            onClick={() => setExpandedId(isExpanded ? null : evt.id)}
                        >
                            {isExpanded ? (
                                <ChevronDown className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                            ) : (
                                <ChevronRight className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                            )}
                            <span
                                className={cn(
                                    "text-[10px] font-bold uppercase px-1.5 py-0.5 rounded border flex-shrink-0",
                                    colorClass
                                )}
                            >
                                {evt.source}
                            </span>
                            <span className="text-xs text-slate-700 truncate flex-1">
                                {evt.event_type}
                            </span>
                            <OutcomeBadge outcome={evt.outcome} />
                            <span className="text-[10px] text-slate-400 whitespace-nowrap">
                                {new Date(evt.created_at).toLocaleTimeString([], {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                    second: "2-digit",
                                })}
                            </span>
                        </button>

                        {isExpanded && (
                            <div className="px-3 pb-3 pt-1 bg-slate-50 text-xs space-y-2 border-t border-slate-100">
                                {evt.duration_ms !== null && evt.duration_ms !== undefined && (
                                    <div className="text-slate-500">
                                        Duration: <span className="font-mono">{evt.duration_ms}ms</span>
                                    </div>
                                )}
                                {evt.correlation_id && (
                                    <div className="text-slate-500 truncate">
                                        Correlation: <span className="font-mono">{evt.correlation_id}</span>
                                    </div>
                                )}
                                {evt.error_message && (
                                    <div className="text-red-600 bg-red-50 p-2 rounded text-[11px] break-all">
                                        {evt.error_message}
                                    </div>
                                )}
                                {evt.payload && Object.keys(evt.payload).length > 0 && (
                                    <pre className="bg-white p-2 rounded border border-slate-200 text-[10px] font-mono overflow-x-auto max-h-32">
                                        {JSON.stringify(evt.payload, null, 2)}
                                    </pre>
                                )}
                                {evt.related_ids && Object.keys(evt.related_ids).length > 0 && (
                                    <div className="text-slate-500">
                                        <span className="font-semibold">Related: </span>
                                        {Object.entries(evt.related_ids).map(([k, v]) => (
                                            <span key={k} className="font-mono text-[10px] mr-2">
                                                {k}={v?.slice(0, 8)}...
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
