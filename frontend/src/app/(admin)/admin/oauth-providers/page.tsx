"use client";

import { useEffect, useState, useCallback } from "react";
import { adminApi } from "@/lib/admin-api";
import { Loader2, ToggleLeft, ToggleRight, RefreshCw } from "lucide-react";

interface OAuthProvider {
    id: string;
    provider_code: string;
    display_name: string;
    auth_url: string;
    token_url: string;
    scopes_json: string | null;
    is_active: boolean;
    supports_refresh_token: boolean;
    connection_count: number;
    created_at: string;
    updated_at: string;
}

export default function OAuthProvidersAdminPage() {
    const [providers, setProviders] = useState<OAuthProvider[]>([]);
    const [loading, setLoading] = useState(true);
    const [toggling, setToggling] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        const res = await adminApi.get<OAuthProvider[]>("/admin/oauth/providers");
        if (res.success) setProviders(res.data ?? []);
        else setError(res.error ?? "Failed to load providers");
        setLoading(false);
    }, []);

    useEffect(() => { load(); }, [load]);

    async function toggle(providerCode: string, current: boolean) {
        setToggling(providerCode);
        const res = await adminApi.patch<OAuthProvider>(
            `/admin/oauth/providers/${providerCode}`,
            { is_active: !current }
        );
        if (res.success && res.data) {
            setProviders((prev) =>
                prev.map((p) => (p.provider_code === providerCode ? res.data! : p))
            );
        }
        setToggling(null);
    }

    return (
        <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-xl font-semibold text-white">OAuth Providers</h1>
                    <p className="text-sm text-white/50 mt-0.5">Enable or disable OAuth providers platform-wide</p>
                </div>
                <button
                    onClick={load}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-sm text-white/70 transition-colors"
                >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                </button>
            </div>

            {error && (
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                    {error}
                </div>
            )}

            {loading ? (
                <div className="flex items-center justify-center h-40">
                    <Loader2 className="w-6 h-6 animate-spin text-white/40" />
                </div>
            ) : (
                <div className="space-y-3">
                    {providers.map((p) => (
                        <div
                            key={p.provider_code}
                            className={`flex items-center gap-4 p-4 rounded-xl border transition-all ${
                                p.is_active
                                    ? "bg-white/5 border-white/10"
                                    : "bg-red-500/5 border-red-500/20 opacity-75"
                            }`}
                        >
                            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${p.is_active ? "bg-emerald-400" : "bg-red-400"}`} />

                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <span className="text-sm font-medium text-white">{p.display_name}</span>
                                    <span className="text-xs text-white/30 font-mono">{p.provider_code}</span>
                                    {p.supports_refresh_token && (
                                        <span className="text-xs px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">refresh</span>
                                    )}
                                </div>
                                <p className="text-xs text-white/40 mt-0.5 truncate">{p.auth_url}</p>
                            </div>

                            <div className="text-xs text-white/40 text-right shrink-0">
                                <div>{p.connection_count} connection{p.connection_count !== 1 ? "s" : ""}</div>
                            </div>

                            <button
                                onClick={() => toggle(p.provider_code, p.is_active)}
                                disabled={toggling === p.provider_code}
                                className="text-white/60 hover:text-white transition-colors disabled:opacity-50"
                            >
                                {toggling === p.provider_code ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : p.is_active ? (
                                    <ToggleRight className="w-5 h-5 text-emerald-400" />
                                ) : (
                                    <ToggleLeft className="w-5 h-5 text-red-400" />
                                )}
                            </button>
                        </div>
                    ))}
                    {providers.length === 0 && (
                        <p className="text-center text-white/40 text-sm py-8">No OAuth providers found. Run the seed script.</p>
                    )}
                </div>
            )}
        </div>
    );
}
