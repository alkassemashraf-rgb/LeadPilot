"use client";

import { useEffect, useState, useCallback } from "react";
import { adminApi } from "@/lib/admin-api";
import { Loader2, RefreshCw, Search, CheckCircle2, XCircle, Clock, AlertCircle } from "lucide-react";

interface OAuthConnection {
    id: string;
    workspace_id: string | null;
    user_id: string | null;
    provider_code: string;
    external_account_id: string | null;
    external_account_name: string | null;
    expires_at: string | null;
    token_type: string | null;
    status: "active" | "expired" | "revoked" | "failed";
    created_at: string;
    updated_at: string;
}

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; label: string; cls: string }> = {
    active: { icon: <CheckCircle2 className="w-3.5 h-3.5" />, label: "Active", cls: "text-emerald-400 bg-emerald-400/10" },
    expired: { icon: <Clock className="w-3.5 h-3.5" />, label: "Expired", cls: "text-amber-400 bg-amber-400/10" },
    revoked: { icon: <XCircle className="w-3.5 h-3.5" />, label: "Revoked", cls: "text-red-400 bg-red-400/10" },
    failed: { icon: <AlertCircle className="w-3.5 h-3.5" />, label: "Failed", cls: "text-orange-400 bg-orange-400/10" },
};

export default function OAuthConnectionsAdminPage() {
    const [connections, setConnections] = useState<OAuthConnection[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filterProvider, setFilterProvider] = useState("");

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        const qs = filterProvider ? `?provider_code=${filterProvider}` : "";
        const res = await adminApi.get<OAuthConnection[]>(`/admin/oauth/connections${qs}`);
        if (res.success) setConnections(res.data ?? []);
        else setError(res.error ?? "Failed to load connections");
        setLoading(false);
    }, [filterProvider]);

    useEffect(() => { load(); }, [load]);

    function fmt(dt: string | null) {
        if (!dt) return "—";
        return new Date(dt).toLocaleString();
    }

    function shortId(id: string | null) {
        if (!id) return "—";
        return id.length > 12 ? `${id.slice(0, 8)}…` : id;
    }

    return (
        <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-xl font-semibold text-white">OAuth Connections</h1>
                    <p className="text-sm text-white/50 mt-0.5">All workspace OAuth connections — tokens never shown</p>
                </div>
                <button
                    onClick={load}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-sm text-white/70 transition-colors"
                >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                </button>
            </div>

            {/* Filter */}
            <div className="flex items-center gap-3">
                <div className="relative flex-1 max-w-xs">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                    <input
                        type="text"
                        placeholder="Filter by provider…"
                        value={filterProvider}
                        onChange={(e) => setFilterProvider(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-1 focus:ring-white/20"
                    />
                </div>
                <span className="text-xs text-white/40">{connections.length} result{connections.length !== 1 ? "s" : ""}</span>
            </div>

            {error && (
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>
            )}

            {loading ? (
                <div className="flex items-center justify-center h-40">
                    <Loader2 className="w-6 h-6 animate-spin text-white/40" />
                </div>
            ) : connections.length === 0 ? (
                <div className="text-center text-white/40 text-sm py-12">No connections found.</div>
            ) : (
                <div className="rounded-xl border border-white/10 overflow-hidden">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-white/10 bg-white/[0.02]">
                                <th className="text-left px-4 py-3 text-white/50 font-medium">Provider</th>
                                <th className="text-left px-4 py-3 text-white/50 font-medium">Account</th>
                                <th className="text-left px-4 py-3 text-white/50 font-medium">Workspace</th>
                                <th className="text-left px-4 py-3 text-white/50 font-medium">Status</th>
                                <th className="text-left px-4 py-3 text-white/50 font-medium">Expires</th>
                                <th className="text-left px-4 py-3 text-white/50 font-medium">Connected</th>
                            </tr>
                        </thead>
                        <tbody>
                            {connections.map((c) => {
                                const s = STATUS_CONFIG[c.status] ?? STATUS_CONFIG.failed;
                                return (
                                    <tr key={c.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                                        <td className="px-4 py-3">
                                            <span className="font-medium text-white capitalize">{c.provider_code}</span>
                                        </td>
                                        <td className="px-4 py-3 text-white/60">
                                            <div>{c.external_account_name || "—"}</div>
                                            <div className="text-xs text-white/30">{shortId(c.external_account_id)}</div>
                                        </td>
                                        <td className="px-4 py-3 text-white/40 font-mono text-xs">
                                            {shortId(c.workspace_id)}
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs ${s.cls}`}>
                                                {s.icon}
                                                {s.label}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-white/40 text-xs">
                                            {fmt(c.expires_at)}
                                        </td>
                                        <td className="px-4 py-3 text-white/40 text-xs">
                                            {fmt(c.created_at)}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
