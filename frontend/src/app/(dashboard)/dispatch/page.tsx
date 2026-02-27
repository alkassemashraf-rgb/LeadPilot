"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { useCatalog, catalogLabel } from "@/lib/catalog";
import {
    RefreshCcw,
    Play,
    CheckCircle2,
    XCircle,
    Clock,
    Send,
    AlertCircle
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface OutboundMessage {
    id: string;
    content: string;
    status: string;
    attempts: number;
    last_error: string | null;
    platform: string;
    created_at: string;
}

export default function DispatchPage() {
    const { data: deliveryStatuses } = useCatalog("message-delivery-statuses");
    const [messages, setMessages] = useState<OutboundMessage[]>([]);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);

    const fetchQueue = async () => {
        try {
            const response = await apiClient.request<OutboundMessage[]>("/dispatch/queue");
            if (response.success && response.data) {
                setMessages(response.data);
            }
        } catch (error) {
            console.error("Failed to fetch queue", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchQueue();
        const interval = setInterval(fetchQueue, 10000); // Poll every 10s
        return () => clearInterval(interval);
    }, []);

    const runDispatch = async () => {
        setRunning(true);
        try {
            const response = await apiClient.request<{ processed_count: number; failed_count: number }>("/dispatch/run", {
                method: "POST"
            });
            if (response.success && response.data) {
                toast.success(`Dispatch completed: ${response.data.processed_count} processed, ${response.data.failed_count} errors`);
                fetchQueue();
            }
        } catch (error) {
            toast.error("Failed to trigger dispatch");
        } finally {
            setRunning(false);
        }
    };

    const getStatusBadge = (status: string) => {
        const label = catalogLabel(deliveryStatuses, status, status);
        switch (status) {
            case "sent":
                return (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                        <CheckCircle2 className="w-3 h-3" /> {label}
                    </span>
                );
            case "failed":
                return (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        <XCircle className="w-3 h-3" /> {label}
                    </span>
                );
            case "sending":
                return (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 animate-pulse">
                        <Send className="w-3 h-3" /> {label}
                    </span>
                );
            default:
                return (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800">
                        <Clock className="w-3 h-3" /> {catalogLabel(deliveryStatuses, "pending", "Pending")}
                    </span>
                );
        }
    };

    return (
        <div className="space-y-8">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900">Outbound Queue</h1>
                    <p className="text-slate-500 mt-1">Monitor and manage real-time message delivery.</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => fetchQueue()}
                        disabled={loading}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-border rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors shadow-sm"
                    >
                        <RefreshCcw className={cn("w-4 h-4 text-slate-500", loading && "animate-spin")} />
                        Refresh
                    </button>
                    <button
                        onClick={runDispatch}
                        disabled={running}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors shadow-sm"
                    >
                        <Play className="w-4 h-4" />
                        Run Dispatch Now
                    </button>
                </div>
            </div>

            <div className="bg-white rounded-xl border border-border shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-border bg-slate-50/50">
                    <h3 className="font-semibold text-slate-900">Recent Outbound Messages</h3>
                    <p className="text-xs text-slate-500 mt-0.5">The last 50 outbound intents and their current delivery status.</p>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm border-collapse">
                        <thead>
                            <tr className="bg-slate-50/50 border-b border-border">
                                <th className="px-6 py-3 font-semibold text-slate-900 tracking-tight">Status</th>
                                <th className="px-6 py-3 font-semibold text-slate-900 tracking-tight">Platform</th>
                                <th className="px-6 py-3 font-semibold text-slate-900 tracking-tight">Content Preview</th>
                                <th className="px-6 py-3 font-semibold text-slate-900 tracking-tight text-center">Attempts</th>
                                <th className="px-6 py-3 font-semibold text-slate-900 tracking-tight">Last Error</th>
                                <th className="px-6 py-3 font-semibold text-slate-900 tracking-tight text-right">Created At</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {messages.length === 0 && !loading ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                                        No outbound messages found in queue.
                                    </td>
                                </tr>
                            ) : (
                                messages.map((msg) => (
                                    <tr key={msg.id} className="hover:bg-slate-50/30 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap">{getStatusBadge(msg.status)}</td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="capitalize font-semibold text-slate-700">{msg.platform}</span>
                                        </td>
                                        <td className="px-6 py-4 max-w-[300px] truncate italic text-slate-600">
                                            "{msg.content}"
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-center text-slate-600 font-mono text-xs">{msg.attempts}</td>
                                        <td className="px-6 py-4">
                                            {msg.last_error ? (
                                                <div className="flex items-center gap-1.5 text-red-600 text-[10px] bg-red-50 px-2 py-1 rounded border border-red-100 max-w-[200px]" title={msg.last_error}>
                                                    <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                                                    <span className="truncate leading-tight font-medium">{msg.last_error}</span>
                                                </div>
                                            ) : (
                                                <span className="text-slate-300">-</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right text-[11px] text-slate-500 font-medium">
                                            {new Date(msg.created_at).toLocaleString()}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
