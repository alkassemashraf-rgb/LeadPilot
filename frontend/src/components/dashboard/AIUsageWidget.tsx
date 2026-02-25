import { Cpu } from "lucide-react";

interface AIUsageProps {
    count: number;
    model: string;
    loading?: boolean;
}

export function AIUsageWidget({ count, model, loading }: AIUsageProps) {
    if (loading) {
        return <div className="h-[300px] bg-white border border-slate-100 animate-pulse rounded-xl shadow-sm" />;
    }

    return (
        <div className="group bg-white p-6 md:p-8 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-all duration-300 flex flex-col justify-center items-center text-center h-full relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-b from-purple-50/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <div className="p-4 bg-purple-50 rounded-2xl mb-4 group-hover:scale-110 transition-transform duration-300 relative z-10">
                <Cpu className="w-8 h-8 text-purple-600" />
            </div>
            <h3 className="text-5xl font-extrabold text-slate-900 relative z-10">{count}</h3>
            <p className="text-xs text-slate-500 font-semibold uppercase tracking-widest mt-2 relative z-10">AI Tasks Automated</p>
            <div className="mt-6 px-4 py-1.5 bg-slate-50 rounded-full text-xs font-mono font-medium text-slate-600 border border-slate-100 relative z-10 shadow-sm">
                Engine: {model}
            </div>
        </div>
    );
}
