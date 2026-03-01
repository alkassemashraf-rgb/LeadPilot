"use client";

import { useEffect, useState } from "react";
import { Zap, Users, MessageSquare, TrendingUp, Send, AlertOctagon, Database, CreditCard, ArrowRight } from "lucide-react";
import Link from "next/link";
import { apiClient } from "@/lib/api";
import { cn } from "@/lib/utils";
import { KPICard } from "@/components/dashboard/KPICard";
import { SimpleLineChart, SimpleBarChart } from "@/components/dashboard/Charts";
import { DispatchHealthWidget } from "@/components/dashboard/HealthWidget";
import { AIUsageWidget } from "@/components/dashboard/AIUsageWidget";
import { toast } from "sonner";

export default function DashboardPage() {
    const [loading, setLoading] = useState(true);
    const [summary, setSummary] = useState<any>(null);
    const [convHistory, setConvHistory] = useState<any[]>([]);
    const [execBreakdown, setExecBreakdown] = useState<any>(null);
    const [aiUsage, setAiUsage] = useState<any>(null);
    const [entitlements, setEntitlements] = useState<any>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Fetch all data in parallel
                const [summaryRes, historyRes, breakdownRes, aiRes, entRes] = await Promise.all([
                    apiClient.get("analytics/summary?range=7"),
                    apiClient.get("analytics/timeseries?metric=conversations&range=7&bucket=day"),
                    apiClient.get("analytics/executions/breakdown?range=7"),
                    apiClient.get("analytics/ai-usage?range=7"),
                    apiClient.get("entitlements"),
                ]);

                if (summaryRes.success) setSummary(summaryRes.data);
                if (historyRes.success) setConvHistory(historyRes.data);
                if (breakdownRes.success) setExecBreakdown(breakdownRes.data);
                if (aiRes.success) setAiUsage(aiRes.data);
                if (entRes.success) setEntitlements(entRes.data);

                if (!summaryRes.success) console.error("Summary failed", summaryRes.error);

            } catch (error) {
                console.error("Dashboard fetch error:", error);
                toast.error("Failed to load dashboard data");
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    // Transform breakdown for chart
    const breakdownData = execBreakdown ? [
        { label: "Completed", value: execBreakdown.completed || 0, color: "#10B981" }, // Emerald 500
        { label: "Failed", value: execBreakdown.failed || 0, color: "#EF4444" },    // Red 500
        { label: "Aborted", value: execBreakdown.aborted || 0, color: "#F59E0B" },  // Amber 500
    ] : [];

    // Parse values safely
    const stats = [
        {
            name: "New Conversations",
            value: summary?.conversations_count ?? 0,
            icon: Users,
            color: "text-slate-600",
            bg: "bg-slate-100" // Neutral
        },
        {
            name: "Inbound Msgs",
            value: summary?.inbound_messages_count ?? 0,
            icon: MessageSquare,
            color: "text-emerald-600",
            bg: "bg-emerald-50" // Emerald accent
        },
        {
            name: "Outbound Sent",
            value: summary?.outbound_messages_sent_count ?? 0,
            icon: Send,
            color: "text-emerald-600",
            bg: "bg-emerald-50"
        },
        {
            name: "Outbound Failed",
            value: summary?.outbound_messages_failed_count ?? 0,
            icon: AlertOctagon,
            color: "text-red-600",
            bg: "bg-red-50" // Error state permitted
        },
        {
            name: "Zoho Synced",
            value: summary?.zoho_synced_contacts_count ?? 0,
            icon: Database,
            color: "text-slate-600",
            bg: "bg-slate-100"
        },
        {
            name: "Auto Success %",
            value: `${summary?.automation_success_rate ?? 0}%`,
            icon: Zap,
            color: "text-emerald-600",
            bg: "bg-emerald-50"
        },
    ];

    return (
        <div className="space-y-8 pb-10">
            {/* Dashboard Header Banner */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center bg-gradient-to-r from-emerald-50 via-teal-50 to-cyan-50 p-6 md:p-8 border border-emerald-100 rounded-2xl shadow-sm relative overflow-hidden">
                <div className="absolute right-0 top-0 opacity-10 pointer-events-none transform translate-x-1/4 -translate-y-1/4">
                    <Zap className="w-64 h-64 text-emerald-600" />
                </div>
                <div className="relative z-10">
                    <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Dashboard Overview</h1>
                    <p className="text-slate-600 mt-2 font-medium">Operational insights and performance for the last 7 days.</p>
                </div>
                <div className="mt-4 md:mt-0 px-4 py-2 bg-white/80 backdrop-blur-sm rounded-xl border border-emerald-100 shadow-sm flex items-center gap-3 relative z-10">
                    <span className="relative flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                    </span>
                    <span className="text-sm font-bold text-slate-700">System Optimal</span>
                </div>
            </div>

            {/* Plan & Usage Card */}
            {entitlements?.plan && (
                <div className="bg-white p-5 rounded-xl border border-slate-100 shadow-sm">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2.5">
                            <CreditCard className="w-5 h-5 text-teal-600" />
                            <h3 className="font-semibold text-slate-900">Plan & Usage</h3>
                            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-100 text-teal-700">
                                {entitlements.plan.display_name}
                            </span>
                        </div>
                        <Link
                            href="/settings"
                            className="flex items-center gap-1 text-xs font-medium text-teal-600 hover:text-teal-700 transition-colors"
                        >
                            View all <ArrowRight className="w-3 h-3" />
                        </Link>
                    </div>
                    {entitlements.usage && entitlements.usage.length > 0 ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {entitlements.usage.slice(0, 3).map((u: any) => {
                                const pct = u.effective_limit ? Math.min(100, Math.round((u.used / u.effective_limit) * 100)) : 0;
                                return (
                                    <div key={u.module_key} className="space-y-1.5">
                                        <div className="flex items-center justify-between text-xs">
                                            <span className="font-medium text-slate-700">{u.module_key.replace(/_/g, " ")}</span>
                                            <span className="text-muted-foreground">
                                                {u.used} / {u.effective_limit ?? "∞"}
                                            </span>
                                        </div>
                                        <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                                            <div
                                                className={cn(
                                                    "h-full rounded-full transition-all",
                                                    pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-amber-500" : "bg-teal-500"
                                                )}
                                                style={{ width: `${pct}%` }}
                                            />
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <p className="text-sm text-muted-foreground">No usage limits configured for your plan.</p>
                    )}
                </div>
            )}

            {/* KPI Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-5">
                {stats.map((stat, i) => (
                    <KPICard
                        key={stat.name}
                        label={stat.name}
                        value={stat.value}
                        icon={stat.icon}
                        color={stat.color}
                        bg={stat.bg}
                        loading={loading}
                    />
                ))}
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                {/* Line Chart */}
                <div className="bg-white p-6 md:p-8 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow duration-300 lg:col-span-2 flex flex-col">
                    <h3 className="text-lg font-bold text-slate-900 mb-6">Conversation Volume (Daily)</h3>
                    <div className="flex-1 min-h-[250px]">
                        <SimpleLineChart
                            data={convHistory}
                            color="#059669" // Emerald 600
                            height={250}
                            loading={loading}
                        />
                    </div>
                </div>

                {/* Execution Bar Chart */}
                <div className="bg-white p-6 md:p-8 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow duration-300 flex flex-col">
                    <h3 className="text-lg font-bold text-slate-900 mb-6">Execution Status</h3>
                    <div className="flex-1 min-h-[250px] flex items-end">
                        <SimpleBarChart
                            data={breakdownData}
                            height={250}
                            loading={loading}
                        />
                    </div>
                </div>
            </div>

            {/* Health & AI */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                <div className="lg:col-span-2">
                    <DispatchHealthWidget
                        loading={loading}
                        pending={summary?.dispatch_health?.pending_count ?? 0}
                        failed={summary?.dispatch_health?.failed_count ?? 0}
                        stale={summary?.dispatch_health?.sending_stale_count ?? 0}
                    />
                </div>
                <div>
                    <AIUsageWidget
                        loading={loading}
                        count={aiUsage?.ai_step_count ?? 0}
                        model={aiUsage?.model_name || "Gemini"}
                    />
                </div>
            </div>
        </div>
    );
}
