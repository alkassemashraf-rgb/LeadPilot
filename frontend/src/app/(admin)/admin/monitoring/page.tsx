"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { adminApi } from "@/lib/admin-api";
import {
    Activity,
    Plug,
    Zap,
    Webhook,
    Loader2,
    CheckCircle,
    XCircle,
    AlertCircle,
    Info,
    RotateCcw,
    ExternalLink,
    BarChart2,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type Tab = "integrations" | "webhooks" | "executions" | "agent-metrics";

export default function AdminMonitoringPage() {
    const [activeTab, setActiveTab] = useState<Tab>("integrations");
    const [data, setData] = useState<any[]>([]);
    const [metrics, setMetrics] = useState<Record<string, number>>({});
    const [loading, setLoading] = useState(true);
    const [replaying, setReplaying] = useState<string | null>(null);

    const fetchData = async () => {
        setLoading(true);
        if (activeTab === "agent-metrics") {
            const res = await adminApi.getAdminMetrics();
            if (res.success && res.data) setMetrics(res.data as Record<string, number>);
            else toast.error(res.error || "Failed to load metrics");
            setLoading(false);
            return;
        }
        let res;
        if (activeTab === "integrations") res = await adminApi.getIntegrations();
        else if (activeTab === "webhooks") res = await adminApi.getWebhooks();
        else res = await adminApi.getExecutions();

        if (res.success && res.data) {
            setData(res.data.items);
        } else {
            toast.error(res.error || `Failed to load ${activeTab}`);
        }
        setLoading(false);
    };

    const handleReplay = async (eventLogId: string) => {
        setReplaying(eventLogId);
        const res = await adminApi.replayWebhook(eventLogId);
        if (res.success) {
            toast.success("Webhook re-queued for processing");
            fetchData();
        } else {
            toast.error(res.error || "Replay failed");
        }
        setReplaying(null);
    };

    useEffect(() => {
        fetchData();
    }, [activeTab]);

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                    <Activity className="w-6 h-6 text-amber-400" />
                    System Monitoring
                </h1>
                <p className="text-slate-400 text-sm mt-1">Real-time health and connectivity diagnostics.</p>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-white/10 gap-6">
                <button
                    onClick={() => setActiveTab("integrations")}
                    className={cn(
                        "pb-3 text-sm font-medium transition-colors relative",
                        activeTab === "integrations" ? "text-amber-400" : "text-slate-500 hover:text-slate-300"
                    )}
                >
                    Integrations
                    {activeTab === "integrations" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-amber-400" />}
                </button>
                <button
                    onClick={() => setActiveTab("webhooks")}
                    className={cn(
                        "pb-3 text-sm font-medium transition-colors relative",
                        activeTab === "webhooks" ? "text-amber-400" : "text-slate-500 hover:text-slate-300"
                    )}
                >
                    Webhooks
                    {activeTab === "webhooks" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-amber-400" />}
                </button>
                <button
                    onClick={() => setActiveTab("executions")}
                    className={cn(
                        "pb-3 text-sm font-medium transition-colors relative",
                        activeTab === "executions" ? "text-amber-400" : "text-slate-500 hover:text-slate-300"
                    )}
                >
                    Executions
                    {activeTab === "executions" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-amber-400" />}
                </button>
                <button
                    onClick={() => setActiveTab("agent-metrics")}
                    className={cn(
                        "pb-3 text-sm font-medium transition-colors relative flex items-center gap-1.5",
                        activeTab === "agent-metrics" ? "text-amber-400" : "text-slate-500 hover:text-slate-300"
                    )}
                >
                    <BarChart2 className="w-3.5 h-3.5" /> Agent Metrics
                    {activeTab === "agent-metrics" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-amber-400" />}
                </button>
            </div>

            {/* Agent Metrics Tab */}
            {activeTab === "agent-metrics" && (
                loading ? (
                    <div className="flex flex-col items-center justify-center p-20 gap-4">
                        <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
                    </div>
                ) : (
                    <AgentMetricsPanel metrics={metrics} />
                )
            )}

            {/* Content Area — other tabs */}
            {activeTab !== "agent-metrics" && <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden min-h-[400px]">
                {loading ? (
                    <div className="flex flex-col items-center justify-center p-20 gap-4">
                        <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
                        <p className="text-sm text-slate-500">Retrieving system telemetry...</p>
                    </div>
                ) : data.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-20 gap-4">
                        <Info className="w-8 h-8 text-slate-600" />
                        <p className="text-sm text-slate-500">No telemetry records found for {activeTab}.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-white/5 text-slate-400 font-medium">
                                <tr>
                                    {activeTab === "integrations" && (
                                        <>
                                            <th className="px-6 py-3">Provider</th>
                                            <th className="px-6 py-3">Workspace</th>
                                            <th className="px-6 py-3">Status</th>
                                            <th className="px-6 py-3">Last Checked</th>
                                        </>
                                    )}
                                    {activeTab === "webhooks" && (
                                        <>
                                            <th className="px-6 py-3">ID</th>
                                            <th className="px-6 py-3">Source</th>
                                            <th className="px-6 py-3">Event</th>
                                            <th className="px-6 py-3">Status</th>
                                            <th className="px-6 py-3">Received</th>
                                            <th className="px-6 py-3">Actions</th>
                                        </>
                                    )}
                                    {activeTab === "executions" && (
                                        <>
                                            <th className="px-6 py-3">Execution ID</th>
                                            <th className="px-6 py-3">Flow</th>
                                            <th className="px-6 py-3">Status</th>
                                            <th className="px-6 py-3">Started</th>
                                            <th className="px-6 py-3">Trace</th>
                                        </>
                                    )}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5 text-slate-300">
                                {data.map((item, i) => (
                                    <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                                        {activeTab === "integrations" && (
                                            <>
                                                <td className="px-6 py-4 font-semibold text-white uppercase tracking-wider">{item.provider}</td>
                                                <td className="px-6 py-4 text-xs font-mono">{item.workspace_id}</td>
                                                <td className="px-6 py-4">
                                                    <StatusBadge status={item.status} />
                                                </td>
                                                <td className="px-6 py-4 text-slate-500">{new Date(item.last_checked_at).toLocaleString()}</td>
                                            </>
                                        )}
                                        {activeTab === "webhooks" && (
                                            <>
                                                <td className="px-6 py-4 text-xs font-mono">{item.id.slice(0, 8)}...</td>
                                                <td className="px-6 py-4 text-white">{item.provider}</td>
                                                <td className="px-6 py-4 text-xs font-mono bg-white/[0.03] rounded">{item.event_type}</td>
                                                <td className="px-6 py-4">
                                                    <StatusBadge status={item.status} />
                                                </td>
                                                <td className="px-6 py-4 text-slate-500">{new Date(item.received_at || item.created_at).toLocaleString()}</td>
                                                <td className="px-6 py-4">
                                                    <button
                                                        onClick={() => handleReplay(item.id)}
                                                        disabled={replaying === item.id}
                                                        className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition-colors disabled:opacity-50"
                                                    >
                                                        <RotateCcw className={cn("w-3 h-3", replaying === item.id && "animate-spin")} />
                                                        Replay
                                                    </button>
                                                </td>
                                            </>
                                        )}
                                        {activeTab === "executions" && (
                                            <>
                                                <td className="px-6 py-4 text-xs font-mono text-amber-500">{item.id.slice(0, 12)}</td>
                                                <td className="px-6 py-4 text-white">Flow: {item.flow_version_id?.slice(0, 8)}</td>
                                                <td className="px-6 py-4">
                                                    <StatusBadge status={item.status} />
                                                </td>
                                                <td className="px-6 py-4 text-slate-500">{new Date(item.created_at).toLocaleTimeString()}</td>
                                                <td className="px-6 py-4">
                                                    <Link
                                                        href={`/admin/executions/${item.id}`}
                                                        className="flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300 transition-colors"
                                                    >
                                                        <ExternalLink className="w-3 h-3" /> View Trace
                                                    </Link>
                                                </td>
                                            </>
                                        )}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>}

            <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex gap-4">
                <AlertCircle className="w-5 h-5 text-amber-500 shrink-0" />
                <div className="text-xs text-amber-200/70 space-y-1">
                    <p className="font-semibold text-amber-400">Security Note:</p>
                    <p>Secret fields (tokens, keys) are automatically masked in this view. Only structural and status data are visible to monitoring staff.</p>
                </div>
            </div>
        </div>
    );
}

function AgentMetricsPanel({ metrics }: { metrics: Record<string, number> }) {
    const agentKeys = Object.entries(metrics).filter(([k]) => k.startsWith("agent.") || k.startsWith("gauge:agent."));
    if (agentKeys.length === 0) {
        return (
            <div className="bg-white/5 border border-white/10 rounded-xl p-12 text-center text-slate-500 text-sm">
                No agent metrics recorded yet. Metrics appear after the first agent turn.
            </div>
        );
    }
    return (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {agentKeys.map(([k, v]) => {
                const label = k.replace("gauge:", "").replace("agent.", "").replace(/_/g, " ");
                return (
                    <div key={k} className="bg-white/5 border border-white/10 rounded-xl p-4">
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">{label}</p>
                        <p className="text-2xl font-bold text-white mt-1">{v.toLocaleString()}</p>
                    </div>
                );
            })}
        </div>
    );
}

function StatusBadge({ status }: { status: string }) {
    const s = status.toLowerCase();
    if (s === "connected" || s === "success" || s === "completed") {
        return (
            <span className="inline-flex items-center gap-1 text-emerald-400 text-[10px] font-bold uppercase">
                <CheckCircle className="w-3 h-3" />
                {s}
            </span>
        );
    }
    if (s === "error" || s === "failed") {
        return (
            <span className="inline-flex items-center gap-1 text-red-400 text-[10px] font-bold uppercase">
                <XCircle className="w-3 h-3" />
                {s}
            </span>
        );
    }
    return (
        <span className="inline-flex items-center gap-1 text-amber-400 text-[10px] font-bold uppercase">
            <Activity className="w-3 h-3" />
            {s}
        </span>
    );
}
