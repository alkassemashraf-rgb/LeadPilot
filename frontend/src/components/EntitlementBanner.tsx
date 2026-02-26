"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { AlertTriangle } from "lucide-react";

interface Entitlement {
    module_key: string;
    plan_limit: number | null;
    effective_limit: number | null;
    has_override: boolean;
    used: number;
    plan_name: string;
}

const MODULE_LABELS: Record<string, string> = {
    prompt_studio: "Prompt Studio",
    runtime_engine: "AI Chat",
    integrations_connect: "Integrations",
    integrations_hub: "Integrations Hub",
    automations: "Automations",
    dispatch_engine: "Dispatch",
    knowledge_files: "Knowledge Files",
    analytics: "Analytics",
    inbox: "Inbox",
    webhooks_ingestion: "Webhooks",
    zoho_sync: "Zoho Sync",
    diagnostics: "Diagnostics",
    email_engine: "Email Engine",
    email_verification: "Email Verification",
    admin_portal: "Admin Portal",
    auth: "Auth",
};

function labelFor(key: string): string {
    return MODULE_LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function EntitlementBanner() {
    const [warnings, setWarnings] = useState<
        { key: string; used: number; limit: number; pct: number }[]
    >([]);

    useEffect(() => {
        let cancelled = false;

        apiClient.get<Entitlement[]>("/workspaces/entitlements").then((res) => {
            if (cancelled || !res.success || !res.data) return;

            const hits = res.data
                .filter((e) => e.effective_limit !== null && e.effective_limit > 0)
                .map((e) => ({
                    key: e.module_key,
                    used: e.used,
                    limit: e.effective_limit as number,
                    pct: Math.round((e.used / (e.effective_limit as number)) * 100),
                }))
                .filter((e) => e.pct >= 80)
                .sort((a, b) => b.pct - a.pct);

            setWarnings(hits);
        });

        return () => {
            cancelled = true;
        };
    }, []);

    if (warnings.length === 0) return null;

    const maxPct = warnings[0].pct;
    const isOver = maxPct >= 100;

    return (
        <div
            className={`flex items-start gap-3 px-4 py-3 rounded-lg text-sm border ${
                isOver
                    ? "bg-red-50 border-red-200 text-red-800"
                    : "bg-amber-50 border-amber-200 text-amber-800"
            }`}
        >
            <AlertTriangle
                className={`h-5 w-5 shrink-0 mt-0.5 ${
                    isOver ? "text-red-500" : "text-amber-500"
                }`}
            />
            <div className="flex flex-col gap-1">
                <span className="font-semibold text-[#0F766E]">
                    {isOver ? "Usage limit reached" : "Approaching usage limits"}
                </span>
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
                    {warnings.map((w) => (
                        <span
                            key={w.key}
                            className={
                                w.pct >= 100
                                    ? "font-semibold text-red-700"
                                    : "text-amber-700"
                            }
                        >
                            {labelFor(w.key)}: {w.used}/{w.limit} this month
                        </span>
                    ))}
                </div>
            </div>
        </div>
    );
}
