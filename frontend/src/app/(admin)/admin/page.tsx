"use client";

import { useEffect, useState } from "react";
import { adminApi, SystemOverview } from "@/lib/admin-api";
import {
    Users,
    Building2,
    ScrollText,
    ToggleLeft,
    CheckCircle,
    XCircle,
    Loader2,
} from "lucide-react";

function StatCard({
    label,
    value,
    icon: Icon,
    color,
}: {
    label: string;
    value: string | number;
    icon: React.ElementType;
    color: string;
}) {
    return (
        <div className="bg-white/5 border border-white/10 rounded-xl p-5 flex items-center gap-4">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
                <Icon className="w-5 h-5" />
            </div>
            <div>
                <p className="text-2xl font-bold text-white">{value}</p>
                <p className="text-xs text-slate-400 mt-0.5">{label}</p>
            </div>
        </div>
    );
}

export default function AdminOverviewPage() {
    const [overview, setOverview] = useState<SystemOverview | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        adminApi.getOverview().then((res) => {
            if (res.success && res.data) {
                setOverview(res.data);
            } else {
                setError(res.error || "Failed to load overview");
            }
            setLoading(false);
        });
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-6 h-6 text-violet-400 animate-spin" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-400">
                {error}
            </div>
        );
    }

    const totalModules = overview ? Object.keys(overview.modules).length : 0;
    const enabledModules = overview
        ? Object.values(overview.modules).filter(Boolean).length
        : 0;

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-white">System Overview</h1>
                <p className="text-slate-400 text-sm mt-1">
                    Platform health and resource summary
                </p>
            </div>

            {/* Stat Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    label="Total Users"
                    value={overview?.users_total ?? 0}
                    icon={Users}
                    color="bg-blue-500/20 text-blue-400"
                />
                <StatCard
                    label="Workspaces"
                    value={overview?.workspaces_total ?? 0}
                    icon={Building2}
                    color="bg-emerald-500/20 text-emerald-400"
                />
                <StatCard
                    label="Audit Log Entries"
                    value={overview?.audit_log_entries ?? 0}
                    icon={ScrollText}
                    color="bg-amber-500/20 text-amber-400"
                />
                <StatCard
                    label={`Modules On (${enabledModules}/${totalModules})`}
                    value={`${Math.round((enabledModules / Math.max(totalModules, 1)) * 100)}%`}
                    icon={ToggleLeft}
                    color="bg-violet-500/20 text-violet-400"
                />
            </div>

            {/* Module Status Grid */}
            <div>
                <h2 className="text-base font-semibold text-white mb-3">Module States</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {overview &&
                        Object.entries(overview.modules).map(([name, enabled]) => (
                            <div
                                key={name}
                                className="flex items-center justify-between bg-white/5 border border-white/10 rounded-lg px-4 py-2.5"
                            >
                                <span className="text-sm text-slate-300 font-mono">{name}</span>
                                {enabled ? (
                                    <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-medium">
                                        <CheckCircle className="w-3.5 h-3.5" />
                                        enabled
                                    </div>
                                ) : (
                                    <div className="flex items-center gap-1.5 text-red-400 text-xs font-medium">
                                        <XCircle className="w-3.5 h-3.5" />
                                        disabled
                                    </div>
                                )}
                            </div>
                        ))}
                </div>
            </div>

            {/* System Info */}
            <div className="bg-white/5 border border-white/10 rounded-xl p-5">
                <h2 className="text-sm font-semibold text-white mb-3">System Info</h2>
                <dl className="space-y-2 text-sm">
                    <div className="flex justify-between">
                        <dt className="text-slate-500">Platform</dt>
                        <dd className="text-slate-200 font-mono">{overview?.platform}</dd>
                    </div>
                    <div className="flex justify-between">
                        <dt className="text-slate-500">Python Version</dt>
                        <dd className="text-slate-200 font-mono">{overview?.python_version}</dd>
                    </div>
                </dl>
            </div>
        </div>
    );
}
