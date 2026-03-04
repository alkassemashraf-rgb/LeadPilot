import { AlertTriangle, CheckCircle, Clock } from "lucide-react";
import Link from "next/link";

interface HealthStatProps {
    label: string;
    count: number;
    status: "healthy" | "warning" | "error";
    icon?: any;
}

function HealthStat({ label, count, status, icon: Icon }: HealthStatProps) {
    const colors = {
        healthy: "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-100 dark:border-emerald-900/30",
        warning: "bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border-amber-100 dark:border-amber-900/30",
        error: "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-100 dark:border-red-900/30",
    };

    return (
        <div className={`flex items-center justify-between p-4 rounded-xl border ${colors[status]} transition-all duration-300 hover:shadow-sm`}>
            <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg bg-white/50 dark:bg-slate-900/50 backdrop-blur-sm`}>
                    {Icon && <Icon className="w-4 h-4" />}
                </div>
                <span className="text-sm font-semibold">{label}</span>
            </div>
            <span className="text-xl font-bold">{count}</span>
        </div>
    );
}

interface DispatchHealthProps {
    pending: number;
    failed: number;
    stale: number;
    loading?: boolean;
}

export function DispatchHealthWidget({ pending, failed, stale, loading }: DispatchHealthProps) {
    if (loading) {
        return <div className="h-[300px] bg-white dark:bg-card border border-slate-100 dark:border-border animate-pulse rounded-xl shadow-sm" />;
    }

    return (
        <div className="bg-white dark:bg-card p-6 md:p-8 rounded-xl border border-slate-100 dark:border-border shadow-sm hover:shadow-md transition-shadow duration-300 h-full flex flex-col">
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold text-slate-900 dark:text-slate-50">Dispatch Health</h3>
                <Link href="/campaigns" className="text-xs px-3 py-1.5 bg-slate-50 dark:bg-slate-800 text-blue-600 dark:text-blue-400 rounded-full hover:bg-blue-50 dark:hover:bg-blue-900/50 font-semibold transition-colors">
                    View Queue →
                </Link>
            </div>

            <div className="space-y-3">
                <HealthStat
                    label="Pending Messages"
                    count={pending}
                    status={pending > 50 ? "warning" : "healthy"}
                    icon={Clock}
                />
                <HealthStat
                    label="Sending > 5m (Stale)"
                    count={stale}
                    status={stale > 0 ? "error" : "healthy"}
                    icon={AlertTriangle}
                />
                <HealthStat
                    label="Failed (24h)"
                    count={failed}
                    status={failed > 0 ? "error" : "healthy"}
                    icon={AlertTriangle}
                />
            </div>
        </div>
    );
}
