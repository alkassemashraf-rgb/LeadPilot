import { LucideIcon } from "lucide-react";

interface KPICardProps {
    label: string;
    value: string | number;
    icon: LucideIcon;
    color: string;
    bg: string;
    delta?: {
        value: string;
        positive: boolean;
    };
    loading?: boolean;
}

export function KPICard({ label, value, icon: Icon, color, bg, delta, loading }: KPICardProps) {
    if (loading) {
        return (
            <div className="bg-white dark:bg-card p-5 rounded-xl border border-slate-100 dark:border-border shadow-sm animate-pulse flex flex-col h-[130px]">
                <div className="h-10 w-10 bg-slate-100 dark:bg-slate-800/50 rounded-lg mb-auto"></div>
                <div className="h-8 bg-slate-100 dark:bg-slate-800/50 rounded w-1/2 mt-4"></div>
                <div className="h-3 bg-slate-100 dark:bg-slate-800/50 rounded w-3/4 mt-2"></div>
            </div>
        );
    }

    return (
        <div className="group bg-white dark:bg-card p-5 rounded-xl border border-slate-100 dark:border-border shadow-sm hover:shadow-md hover:border-slate-200 dark:hover:border-slate-700 transition-all duration-300 relative overflow-hidden flex flex-col">
            <div className="absolute -bottom-4 -right-4 p-4 opacity-[0.03] group-hover:opacity-[0.06] transition-opacity transform group-hover:-translate-y-1 group-hover:-translate-x-1 duration-500 pointer-events-none">
                <Icon className={`w-28 h-28 ${color}`} />
            </div>

            <div className="relative z-10 flex items-start justify-between mb-4">
                <div className={`p-2.5 rounded-lg shrink-0 ${bg} transition-colors duration-300 group-hover:bg-opacity-80`}>
                    <Icon className={`w-5 h-5 ${color}`} />
                </div>
            </div>

            <div className="relative z-10 mt-auto min-w-0">
                <h3 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-slate-50 truncate">{value}</h3>
                <p className="text-[11px] mt-1 font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest line-clamp-2 leading-tight">
                    {label}
                </p>
                {delta && (
                    <p className={`text-[10px] mt-2 font-medium flex items-center gap-1 ${delta.positive ? 'text-emerald-600' : 'text-red-500'}`}>
                        {delta.positive ? '↑' : '↓'} {delta.value}
                        <span className="text-slate-400 font-normal ml-1 truncate">vs last week</span>
                    </p>
                )}
            </div>
        </div>
    );
}
