"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import {
    Users,
    Search,
    UserCheck,
    UserMinus,
    ShieldAlert,
    ExternalLink,
    Loader2,
    RefreshCw
} from "lucide-react";
import { toast } from "sonner";

export default function AdminUsersPage() {
    const [users, setUsers] = useState<any[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [skip, setSkip] = useState(0);
    const limit = 20;

    const fetchUsers = async () => {
        setLoading(true);
        const res = await adminApi.getUsers({ skip, limit, query: search });
        if (res.success && res.data) {
            setUsers(res.data.items);
            setTotal(res.data.total);
        } else {
            toast.error(res.error || "Failed to load users");
        }
        setLoading(false);
    };

    useEffect(() => {
        fetchUsers();
    }, [skip]);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setSkip(0);
        fetchUsers();
    };

    const handleToggleStatus = async (user: any) => {
        const res = await adminApi.toggleUserStatus(user.id, !user.is_active);
        if (res.success) {
            toast.success(`User ${user.is_active ? "deactivated" : "activated"}`);
            fetchUsers();
        } else {
            toast.error(res.error || "Action failed");
        }
    };

    const handleImpersonate = async (user: any) => {
        toast.promise(adminApi.impersonateUser(user.id), {
            loading: "Generating secure session...",
            success: (res) => {
                if (res.success && res.data?.access_token) {
                    // Start postMessage handshake flow
                    const tenantUrl = window.location.origin + "/impersonation/consume";
                    const newWindow = window.open(tenantUrl, "_blank");

                    if (newWindow) {
                        const listener = (event: MessageEvent) => {
                            if (event.data?.type === "LP_IMPERSONATION_READY") {
                                newWindow.postMessage({
                                    type: "LP_IMPERSONATION_SET_TOKEN",
                                    token: res.data?.access_token
                                }, "*");
                                window.removeEventListener("message", listener);
                            }
                        };
                        window.addEventListener("message", listener);
                        return "Impersonation session started in new tab.";
                    }
                    return "Session generated, but popup blocked. Enable popups to continue.";
                }
                throw new Error(res.error || "Failed to impersonate");
            },
            error: (err) => err.message
        });
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Users className="w-6 h-6 text-blue-400" />
                        User Management
                    </h1>
                    <p className="text-slate-400 text-sm mt-1">Manage product users and provide support.</p>
                </div>

                <form onSubmit={handleSearch} className="relative w-72">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Search by email or name..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    />
                </form>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                <table className="w-full text-left text-sm">
                    <thead className="bg-white/5 text-slate-400 font-medium">
                        <tr>
                            <th className="px-6 py-3">User</th>
                            <th className="px-6 py-3">Status</th>
                            <th className="px-6 py-3">Workspaces</th>
                            <th className="px-6 py-3">Joined</th>
                            <th className="px-6 py-3 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-slate-300">
                        {loading ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-12 text-center">
                                    <Loader2 className="w-6 h-6 text-blue-400 animate-spin mx-auto" />
                                </td>
                            </tr>
                        ) : users.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                                    No users found matching your search.
                                </td>
                            </tr>
                        ) : (
                            users.map((user) => (
                                <tr key={user.id} className="hover:bg-white/[0.02] transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="flex flex-col">
                                            <span className="font-medium text-white">{user.full_name || "Untitled User"}</span>
                                            <span className="text-xs text-slate-500">{user.email}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        {user.is_active ? (
                                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-bold uppercase">
                                                Active
                                            </span>
                                        ) : (
                                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 text-[10px] font-bold uppercase">
                                                Deactivated
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 font-mono text-xs">
                                        {user.workspaces?.length || 0} workspaces
                                    </td>
                                    <td className="px-6 py-4 text-slate-500">
                                        {new Date(user.created_at).toLocaleDateString()}
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex items-center justify-end gap-2">
                                            <button
                                                onClick={() => handleToggleStatus(user)}
                                                className="p-1.5 hover:bg-white/10 rounded-lg transition-colors group"
                                                title={user.is_active ? "Deactivate User" : "Activate User"}
                                            >
                                                {user.is_active ? (
                                                    <UserMinus className="w-4 h-4 text-red-400" />
                                                ) : (
                                                    <UserCheck className="w-4 h-4 text-emerald-400" />
                                                )}
                                            </button>
                                            <button
                                                onClick={() => handleImpersonate(user)}
                                                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-lg shadow-blue-900/20 active:scale-95"
                                            >
                                                <ShieldAlert className="w-3.5 h-3.5" />
                                                Impersonate
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>

                {/* Pagination */}
                <div className="px-6 py-4 bg-white/5 border-t border-white/10 flex items-center justify-between">
                    <p className="text-xs text-slate-500">
                        Showing {users.length} of {total} users
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
