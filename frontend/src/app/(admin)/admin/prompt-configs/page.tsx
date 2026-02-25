"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import { BookOpen, Loader2, Info, RefreshCw } from "lucide-react";
import { toast } from "sonner";

export default function AdminPromptConfigsPage() {
    const [items, setItems] = useState<any[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState<string | null>(null);

    const load = async () => {
        setLoading(true);
        const res = await adminApi.getPromptConfigs({ limit: 100 });
        if (res.success && res.data) {
            setItems(res.data.items);
            setTotal(res.data.total);
        } else {
            toast.error(res.error || "Failed to load prompt configs");
        }
        setLoading(false);
    };

    useEffect(() => { load(); }, []);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <BookOpen className="w-6 h-6 text-amber-400" />
                        Prompt Configs
                    </h1>
                    <p className="text-slate-400 text-sm mt-1">
                        Read-only view. {total} configs across all workspaces.
                    </p>
                </div>
                <button
                    onClick={load}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-sm transition-colors"
                >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                </button>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                {loading ? (
                    <div className="flex flex-col items-center justify-center p-20 gap-4">
                        <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
                        <p className="text-sm text-slate-500">Loading prompt configs...</p>
                    </div>
                ) : items.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-20 gap-4">
                        <Info className="w-8 h-8 text-slate-600" />
                        <p className="text-sm text-slate-500">No prompt configs found.</p>
                    </div>
                ) : (
                    <div className="divide-y divide-white/5">
                        {items.map((item) => (
                            <div key={item.id} className="p-5 hover:bg-white/[0.02] transition-colors">
                                <div className="flex items-start justify-between gap-4">
                                    <div className="space-y-1 flex-1">
                                        <div className="flex items-center gap-3">
                                            <span className="text-white font-medium">{item.name}</span>
                                            <span className="text-xs text-slate-500 font-mono">v{item.latest_version ?? "—"}</span>
                                            {item.model && (
                                                <span className="text-xs bg-amber-500/15 text-amber-400 px-2 py-0.5 rounded font-mono">
                                                    {item.model}
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-4 text-xs text-slate-500">
                                            <span>Workspace: <span className="font-mono">{item.workspace_id?.slice(0, 12)}...</span></span>
                                            {item.updated_at && (
                                                <span>Updated: {new Date(item.updated_at).toLocaleDateString()}</span>
                                            )}
                                        </div>
                                    </div>
                                    {item.system_prompt_preview && (
                                        <button
                                            onClick={() => setExpanded(expanded === item.id ? null : item.id)}
                                            className="text-xs text-amber-400 hover:text-amber-300 shrink-0 transition-colors"
                                        >
                                            {expanded === item.id ? "Hide" : "Preview"}
                                        </button>
                                    )}
                                </div>
                                {expanded === item.id && item.system_prompt_preview && (
                                    <div className="mt-3 p-3 bg-black/30 rounded-lg border border-white/5">
                                        <p className="text-xs font-mono text-slate-400 whitespace-pre-wrap leading-relaxed">
                                            {item.system_prompt_preview}
                                            {item.system_prompt_preview.length >= 200 && (
                                                <span className="text-slate-600"> ... [truncated]</span>
                                            )}
                                        </p>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
