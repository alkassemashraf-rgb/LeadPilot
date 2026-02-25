"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, Loader2 } from "lucide-react";
import { adminAuth } from "@/lib/admin-auth";
import { adminApi } from "@/lib/admin-api";

export default function AdminLoginPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        const res = await adminApi.login(email, password);
        if (res.success && res.data?.access_token) {
            adminAuth.setToken(res.data.access_token);
            router.push("/admin");
        } else {
            setError(res.error || "Invalid credentials");
        }
        setLoading(false);
    };

    return (
        <div className="min-h-screen bg-[#0F172A] flex items-center justify-center px-4">
            <div className="w-full max-w-sm">
                {/* Logo */}
                <div className="flex items-center justify-center gap-2.5 mb-8">
                    <div className="w-9 h-9 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center">
                        <Shield className="w-5 h-5 text-violet-400" />
                    </div>
                    <div>
                        <span className="text-white font-bold text-base tracking-tight">LeadPilot</span>
                        <span className="ml-2 text-[10px] font-semibold uppercase tracking-widest text-violet-400 bg-violet-500/10 px-1.5 py-0.5 rounded">
                            Admin
                        </span>
                    </div>
                </div>

                {/* Card */}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-8">
                    <h1 className="text-white font-semibold text-lg mb-1">Admin Console</h1>
                    <p className="text-slate-500 text-sm mb-6">Sign in with your admin credentials.</p>

                    {error && (
                        <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1.5">
                                Email
                            </label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                autoComplete="email"
                                className="w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 transition-colors"
                                placeholder="admin@example.com"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1.5">
                                Password
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                autoComplete="current-password"
                                className="w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 transition-colors"
                                placeholder="••••••••"
                            />
                        </div>
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors flex items-center justify-center gap-2 mt-2"
                        >
                            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                            {loading ? "Signing in…" : "Sign in"}
                        </button>
                    </form>
                </div>

                <p className="text-center text-xs text-slate-600 mt-6">
                    Not an admin? <a href="/login" className="text-slate-500 hover:text-slate-400 underline">Go to product login</a>
                </p>
            </div>
        </div>
    );
}
