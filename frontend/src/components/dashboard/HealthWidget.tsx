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
        healthy: "bg-emerald-50 text-emerald-700 border-emerald-100",
        warning: "bg-amber-50 text-amber-700 border-amber-100",
        error: "bg-red-50 text-red-700 border-red-100",
    };

    return (
        <div className={`flex items-center justify-between p-4 rounded-xl border ${colors[status]} transition-all duration-300 hover:shadow-sm`}>
            <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg bg-white/50 backdrop-blur-sm`}>
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
        return <div className="h-[300px] bg-white border border-slate-100 animate-pulse rounded-xl shadow-sm" />;
    }

    return (
        <div className="bg-white p-6 md:p-8 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow duration-300 h-full flex flex-col">
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold text-slate-900">Dispatch Health</h3>
                <Link href="/campaigns" className="text-xs px-3 py-1.5 bg-slate-50 text-blue-600 rounded-full hover:bg-blue-50 font-semibold transition-colors">
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
