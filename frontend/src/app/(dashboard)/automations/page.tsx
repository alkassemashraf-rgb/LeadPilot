"use client";

import { useState, useEffect } from "react";
import {
    Zap,
    Plus,
    ChevronRight,
    Loader2,
    LayoutTemplate,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiClient } from "@/lib/api";
import { createFlow } from "@/lib/automations-api";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface Flow {
    id: string;
    name: string;
    description: string;
    status: "draft" | "published";
    created_at: string;
    source_template_id?: string | null;
}

export default function AutomationsPage() {
    const router = useRouter();
    const [flows, setFlows] = useState<Flow[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [creating, setCreating] = useState(false);

    // Fetch flows from backend
    useEffect(() => {
        const fetchFlows = async () => {
            const res = await apiClient.get("/automations");
            if (res.success && res.data) {
                setFlows(res.data);
            }
            setIsLoading(false);
        };
        fetchFlows();
    }, []);

    const handleCreateBlank = async () => {
        setCreating(true);
        const res = await createFlow("Untitled Automation");
        if (res.success && res.data) {
            router.push(`/automations/${res.data.flow_id}`);
        }
        setCreating(false);
    };

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8">
            {/* Header */}
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Automations</h1>
                    <p className="text-muted-foreground mt-2">
                        Build and manage your AI-driven workflows.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Link
                        href="/templates"
                        className="flex items-center gap-2 border border-border hover:border-teal-400 text-foreground px-4 py-2 rounded-lg font-medium transition-colors"
                    >
                        <LayoutTemplate className="w-4 h-4" />
                        Templates
                    </Link>
                    <button
                        onClick={handleCreateBlank}
                        disabled={creating}
                        className="flex items-center gap-2 bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-sm disabled:opacity-50"
                    >
                        {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                        Create Blank
                    </button>
                </div>
            </div>

            {/* Stats/Badges Placeholder */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-1">
                    <p className="text-sm text-muted-foreground">Active Flows</p>
                    <p className="text-2xl font-bold">{flows.filter(f => f.status === "published").length}</p>
                </div>
                <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-1">
                    <p className="text-sm text-muted-foreground">Drafts</p>
                    <p className="text-2xl font-bold">{flows.filter(f => f.status === "draft").length}</p>
                </div>
                <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-1">
                    <p className="text-sm text-muted-foreground">Total Executions (24h)</p>
                    <p className="text-2xl font-bold">128</p>
                </div>
            </div>

            {/* Flow List */}
            <div className="space-y-4">
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-20 text-muted-foreground space-y-4">
                        <Loader2 className="w-8 h-8 animate-spin" />
                        <p>Loading your automations...</p>
                    </div>
                ) : flows.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-20 border-2 border-dashed border-border rounded-2xl bg-slate-50/50 space-y-4">
                        <Zap className="w-12 h-12 text-slate-300" />
                        <div className="text-center">
                            <h3 className="font-semibold text-lg">No automations yet</h3>
                            <p className="text-muted-foreground">Get started by creating your first AI workflow.</p>
                        </div>
                        <Link href="/templates" className="text-teal-600 font-medium hover:underline">
                            Browse templates
                        </Link>
                    </div>
                ) : (
                    <div className="grid gap-3">
                        {flows.map((flow) => (
                            <Link
                                key={flow.id}
                                href={`/automations/${flow.id}`}
                                className="group flex items-center justify-between p-4 rounded-xl border border-border bg-card hover:border-teal-200 hover:bg-teal-50/30 transition-all shadow-sm"
                            >
                                <div className="flex items-center gap-4">
                                    <div className={cn(
                                        "p-2.5 rounded-lg flex items-center justify-center ring-1",
                                        flow.status === "published"
                                            ? "bg-teal-50 text-teal-600 ring-teal-200"
                                            : "bg-slate-50 text-slate-500 ring-slate-200"
                                    )}>
                                        <Zap className="w-5 h-5 fill-current" />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                                            {flow.name}
                                            <span className={cn(
                                                "text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded-md font-bold",
                                                flow.status === "published"
                                                    ? "bg-teal-100 text-teal-700"
                                                    : "bg-slate-200 text-slate-600"
                                            )}>
                                                {flow.status}
                                            </span>
                                            {flow.source_template_id && (
                                                <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded-md font-bold bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                                                    From Template
                                                </span>
                                            )}
                                        </h3>
                                        <p className="text-sm text-muted-foreground line-clamp-1 max-w-md">
                                            {flow.description}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="text-right hidden sm:block mr-4">
                                        <p className="text-xs text-muted-foreground uppercase font-medium">Last active</p>
                                        <p className="text-sm text-slate-700">2 hours ago</p>
                                    </div>
                                    <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-teal-400 transform group-hover:translate-x-1 transition-all" />
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
