"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { adminApi } from "@/lib/admin-api";
import { Landmark, Search, Loader2, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export default function AgenciesPage() {
    const router = useRouter();
    const [agencies, setAgencies] = useState<any[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [query, setQuery] = useState("");

    const load = async (search?: string) => {
        setLoading(true);
        const res = await adminApi.getAgencies({ query: search, limit: 50 });
        if (res.success && res.data) {
            setAgencies(res.data.items || []);
            setTotal(res.data.total || 0);
        }
        setLoading(false);
    };

    useEffect(() => { load(); }, []);

    const handleSearch = () => load(query);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                    <Landmark className="w-6 h-6 text-amber-400" />
                    Agencies
                    <span className="text-sm font-normal text-slate-500 ml-2">({total})</span>
                </h1>
            </div>

            {/* Search */}
            <div className="flex items-center gap-3">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Search by name or owner email..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                        className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500/50"
                    />
                </div>
                <button
                    onClick={handleSearch}
                    className="px-4 py-2.5 bg-amber-600 hover:bg-amber-500 text-white text-sm font-medium rounded-lg transition-colors"
                >
                    Search
                </button>
            </div>

            {/* Table */}
            {loading ? (
                <div className="flex flex-col items-center justify-center h-64 gap-4">
                    <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
                    <p className="text-sm text-slate-500">Loading agencies...</p>
                </div>
            ) : agencies.length === 0 ? (
                <div className="text-center py-20 text-slate-500">
                    No agencies found.
                </div>
            ) : (
                <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-white/5 text-slate-400 font-medium">
                            <tr>
                                <th className="px-5 py-3">Name</th>
                                <th className="px-5 py-3">Owner</th>
                                <th className="px-5 py-3">Workspaces</th>
                                <th className="px-5 py-3">Members</th>
                                <th className="px-5 py-3">Status</th>
                                <th className="px-5 py-3"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5 text-slate-300">
                            {agencies.map((a) => (
                                <tr
                                    key={a.id}
                                    className="hover:bg-white/[0.02] transition-colors cursor-pointer"
                                    onClick={() => router.push(`/admin/agencies/${a.id}`)}
                                >
                                    <td className="px-5 py-4 text-white font-medium">{a.name}</td>
                                    <td className="px-5 py-4">{a.owner_email}</td>
                                    <td className="px-5 py-4">{a.workspace_count}</td>
                                    <td className="px-5 py-4">{a.member_count}</td>
                                    <td className="px-5 py-4">
                                        <span className={cn(
                                            "text-xs font-bold uppercase px-2 py-0.5 rounded",
                                            a.status === "active"
                                                ? "bg-emerald-500/15 text-emerald-400"
                                                : "bg-red-500/15 text-red-400"
                                        )}>
                                            {a.status}
                                        </span>
                                    </td>
                                    <td className="px-5 py-4">
                                        <ChevronRight className="w-4 h-4 text-slate-600" />
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
