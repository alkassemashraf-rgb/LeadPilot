"use client";

import { useState, useEffect } from "react";
import {
    Zap,
    ArrowLeft,
    Save,
    Send,
    Rocket,
    Settings2,
    FileJson,
    CheckCircle2,
    Loader2
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { cn } from "@/lib/utils";

export default function FlowDetailPage() {
    const params = useParams();
    const id = params.id as string;
    const [flow, setFlow] = useState<any>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [isPublishing, setIsPublishing] = useState(false);
    const [status, setStatus] = useState<string>("");

    useEffect(() => {
        const fetchFlow = async () => {
            try {
                const res = await fetch(`/api/v1/automations/${id}`, {
                    headers: { 'X-Workspace-ID': 'dummy' } // In real app, get from context
                });
                const json = await res.json();
                if (json.success) setFlow(json.data);
            } catch (err) {
                console.error("Failed to fetch flow", err);
            } finally {
                setIsLoading(false);
            }
        };
        if (id) fetchFlow();
    }, [id]);

    const handlePublish = async () => {
        setIsPublishing(true);
        try {
            const res = await fetch(`/api/v1/automations/${id}/publish`, { method: 'POST' });
            const json = await res.json();
            if (json.success) setStatus("published");
        } catch (err) {
            console.error("Publish failed", err);
        } finally {
            setIsPublishing(false);
        }
    };

    if (isLoading) return (
        <div className="flex items-center justify-center h-screen">
            <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
        </div>
    );

    if (!flow) return <div className="p-8 text-center text-red-500 font-medium">Flow not found.</div>;

    const definition = flow.definition || {};
    const nodes = definition.nodes || [];
    const triggerNode = nodes.find((n: any) => n.type === 'TRIGGER');
    const actionNodes = nodes.filter((n: any) => n.type !== 'TRIGGER');

    return (
        <div className="h-full flex flex-col bg-slate-50/50">
            {/* Detail Header */}
            <header className="bg-white border-b border-border p-4 sticky top-0 z-10 shadow-sm">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link
                            href="/automations"
                            className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 transition-colors"
                        >
                            <ArrowLeft className="w-5 h-5" />
                        </Link>
                        <div>
                            <div className="flex items-center gap-2">
                                <h1 className="text-xl font-bold text-slate-900">{flow.name}</h1>
                                <span className={cn(
                                    "text-[10px] uppercase px-1.5 py-0.5 rounded-md font-bold",
                                    flow.status === "published" || status === "published"
                                        ? "bg-teal-100 text-teal-700"
                                        : "bg-slate-200 text-slate-600"
                                )}>
                                    {status === "published" ? "published" : flow.status}
                                </span>
                            </div>
                            <p className="text-sm text-muted-foreground">ID: {id}</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <button className="flex items-center gap-2 px-4 py-2 text-slate-600 font-medium hover:bg-slate-100 rounded-lg transition-colors">
                            <Save className="w-4 h-4" />
                            Save Draft
                        </button>
                        <button
                            onClick={handlePublish}
                            disabled={isPublishing || flow.status === "published" || status === "published"}
                            className={cn(
                                "flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all shadow-sm",
                                (flow.status === "published" || status === "published")
                                    ? "bg-slate-100 text-slate-400 cursor-not-allowed"
                                    : "bg-teal-600 hover:bg-teal-700 text-white"
                            )}
                        >
                            {isPublishing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Rocket className="w-4 h-4" />}
                            {(flow.status === "published" || status === "published") ? "Published" : "Publish Flow"}
                        </button>
                    </div>
                </div>
            </header>

            {/* Main Content Areas */}
            <main className="flex-1 p-8 max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Summary View */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="space-y-4">
                        <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                            <Zap className="w-5 h-5 text-teal-600" />
                            Automation Summary
                        </h2>

                        {/* Trigger Card */}
                        <div className="bg-white border border-border rounded-2xl p-6 shadow-sm ring-1 ring-teal-500/5">
                            <div className="text-xs font-bold text-teal-600 uppercase tracking-widest mb-3">Trigger Event</div>
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-teal-50 rounded-xl text-teal-600">
                                    <Zap className="w-6 h-6 fill-current" />
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-900">{triggerNode?.config?.type?.replace('_', ' ') || 'Incoming Message'}</h3>
                                    <p className="text-sm text-muted-foreground">Provider: {triggerNode?.config?.platform?.toUpperCase()}</p>
                                </div>
                            </div>
                        </div>

                        {/* Steps List */}
                        <div className="space-y-3">
                            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest pl-1">Actions & Steps</div>
                            {actionNodes.map((node: any, idx: number) => (
                                <div key={node.id} className="bg-white border border-border rounded-2xl p-5 shadow-sm flex items-center gap-4 relative">
                                    <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-500 border border-border">
                                        {idx + 1}
                                    </div>
                                    <div className="flex-1">
                                        <div className="font-bold text-slate-700 flex items-center gap-2 capitalize">
                                            {node.type.replace('_', ' ').toLowerCase()}
                                        </div>
                                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                                            {node.type === 'AI_REPLY' ? 'Generates an AI response using Prompt Studio.' :
                                                node.type === 'SEND_MESSAGE' ? (node.config?.text || 'Standard message intent.') :
                                                    node.type === 'HUMAN_HANDOVER' ? 'Notifies a team member for takeover.' : 'Processes contact update.'}
                                        </p>
                                    </div>
                                    <button className="p-2 text-slate-300 hover:text-teal-600 transition-colors">
                                        <Settings2 className="w-4 h-4" />
                                    </button>
                                </div>
                            ))}
                        </div>

                        {/* Advanced Collapsible */}
                        <div className="pt-4">
                            <button
                                onClick={() => setShowAdvanced(!showAdvanced)}
                                className="text-sm text-slate-400 font-medium flex items-center gap-2 hover:text-slate-600 transition-colors"
                            >
                                <Settings2 className={cn("w-4 h-4 transition-transform", showAdvanced && "rotate-90")} />
                                {showAdvanced ? "Hide Advanced Definition" : "View Advanced Definition (JSON)"}
                            </button>

                            {showAdvanced && (
                                <div className="mt-4 bg-slate-900 rounded-2xl p-6 overflow-x-auto border border-slate-800 animate-in fade-in slide-in-from-top-4">
                                    <pre className="text-xs font-mono text-teal-400">
                                        {JSON.stringify(definition, null, 2)}
                                    </pre>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Sidebar Info */}
                <div className="space-y-6">
                    <div className="bg-white border border-border rounded-2xl p-6 shadow-sm space-y-4">
                        <h2 className="font-semibold text-slate-900 border-b pb-2">Flow Stats</h2>
                        <div className="space-y-3 px-1">
                            <div className="flex justify-between items-center text-sm">
                                <span className="text-muted-foreground">Created</span>
                                <span className="font-medium">Today</span>
                            </div>
                            <div className="flex justify-between items-center text-sm">
                                <span className="text-muted-foreground">Version</span>
                                <span className="font-medium bg-slate-100 px-1.5 py-0.5 rounded text-[10px]">v1.0</span>
                            </div>
                            <div className="flex justify-between items-center text-sm">
                                <span className="text-muted-foreground">Total Steps</span>
                                <span className="font-medium">{actionNodes.length + 1}</span>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white border border-border rounded-2xl p-6 shadow-sm space-y-4">
                        <h2 className="font-semibold text-slate-900 border-b pb-2">Recent Logs</h2>
                        <div className="flex flex-col items-center justify-center pt-4 text-center">
                            <Zap className="w-8 h-8 text-teal-400 mb-2 opacity-30" />
                            <p className="text-sm text-muted-foreground italic">No recent executions recorded.</p>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
