"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { adminApi } from "@/lib/admin-api";
import {
    Building2,
    Search,
    Globe,
    Layers,
    Calendar,
    Loader2,
    ArrowUpRight,
    Users
} from "lucide-react";
import { toast } from "sonner";

export default function AdminWorkspacesPage() {
    const router = useRouter();
    const [workspaces, setWorkspaces] = useState<any[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [skip, setSkip] = useState(0);
    const limit = 20;

    const fetchWorkspaces = async () => {
        setLoading(true);
        const res = await adminApi.getWorkspaces({ skip, limit, query: search });
        if (res.success && res.data) {
            setWorkspaces(res.data.items);
            setTotal(res.data.total);
        } else {
            toast.error(res.error || "Failed to load workspaces");
        }
        setLoading(false);
    };

    useEffect(() => {
        fetchWorkspaces();
    }, [skip]);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setSkip(0);
        fetchWorkspaces();
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Building2 className="w-6 h-6 text-emerald-400" />
                        Workspace Oversight
                    </h1>
                    <p className="text-slate-400 text-sm mt-1">Global view of all tenant environments and their health.</p>
                </div>

                <form onSubmit={handleSearch} className="relative w-72">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Search workspace name..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                    />
                </form>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                <table className="w-full text-left text-sm">
                    <thead className="bg-white/5 text-slate-400 font-medium">
                        <tr>
                            <th className="px-6 py-3">Workspace</th>
                            <th className="px-6 py-3">Type</th>
                            <th className="px-6 py-3">Members</th>
                            <th className="px-6 py-3">Created</th>
                            <th className="px-6 py-3 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-slate-300">
                        {loading ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-12 text-center">
                                    <Loader2 className="w-6 h-6 text-emerald-400 animate-spin mx-auto" />
                                </td>
                            </tr>
                        ) : workspaces.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                                    No workspaces found.
                                </td>
                            </tr>
                        ) : (
                            workspaces.map((ws) => (
                                <tr key={ws.id} className="hover:bg-white/[0.02] transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="flex flex-col">
                                            <span className="font-medium text-white">{ws.name}</span>
                                            <span className="text-[10px] font-mono text-slate-500">{ws.id}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[10px] font-bold uppercase">
                                            Pro
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            <Users className="w-3.5 h-3.5 text-slate-500" />
                                            <span>{ws.members?.length || 0}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-slate-500">
                                        <div className="flex items-center gap-2">
                                            <Calendar className="w-3.5 h-3.5" />
                                            {new Date(ws.created_at).toLocaleDateString()}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <button
                                            onClick={() => router.push(`/admin/workspaces/${ws.id}`)}
                                            className="text-slate-400 hover:text-white transition-colors"
                                            title="View workspace detail"
                                        >
                                            <ArrowUpRight className="w-4 h-4" />
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>

                <div className="px-6 py-4 bg-white/5 border-t border-white/10 flex items-center justify-between">
                    <p className="text-xs text-slate-500">
                        Total {total} workspaces
                    </p>
                    <div className="flex items-center gap-2">
                        <button
                            disabled={skip === 0}
                            onClick={() => setSkip(Math.max(0, skip - limit))}
                            className="px-3 py-1 bg-white/5 border border-white/10 rounded text-xs text-white disabled:opacity-50"
                        >
                            Previous
                        </button>
                        <button
                            disabled={skip + limit >= total}
                            onClick={() => setSkip(skip + limit)}
                            className="px-3 py-1 bg-white/5 border border-white/10 rounded text-xs text-white disabled:opacity-50"
                        >
                            Next
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
