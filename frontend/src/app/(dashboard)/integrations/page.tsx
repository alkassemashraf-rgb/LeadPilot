"use client";

import { useState, useEffect } from "react";
import {
    Plug,
    CheckCircle2,
    XCircle,
    AlertCircle,
    ExternalLink,
    Settings2,
    RefreshCw,
    Loader2,
    Share2
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { apiClient } from "@/lib/api";

type Status = "connected" | "disconnected" | "error";

interface IntegrationProvider {
    id: string;
    provider: string;
    name: string;
    description: string;
    status: Status;
    lastChecked?: string;
    icon: string;
}

const PROVIDER_METADATA: Record<string, any> = {
    zoho: {
        name: "Zoho CRM",
        description: "Sync leads and contacts directly into your Zoho CRM pipeline.",
        icon: 'data:image/svg+xml;utf8,<svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><title>Zoho</title><path fill="%230F766E" d="M21.758 12c0 5.39-4.368 9.758-9.758 9.758S2.242 17.39 2.242 12c0-5.39 4.368-9.758 9.758-9.758S21.758 6.61 21.758 12zm-9.035-4.482H6.554v2.09l4.16 4.303H6.554v2.09h6.169V14.12h.001l-4.148-4.29h4.148v-2.09.001zM17.446 12A2.77 2.77 0 1014.675 9.23 2.772 2.772 0 0017.446 12zm0 2.08A2.77 2.77 0 1020.217 16.85 2.772 2.772 0 0017.446 14.08z"/></svg>',
        fields: [{ name: "org_id", label: "Organization ID", type: "text" }, { name: "access_token", label: "Access Token", type: "password" }]
    },
    whatsapp: {
        name: "WhatsApp Cloud API",
        description: "Official API for professional messaging and automation.",
        icon: "https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg",
        fields: [{ name: "phone_number_id", label: "Phone Number ID", type: "text" }, { name: "access_token", label: "Access Token", type: "password" }]
    },
    meta: {
        name: "Meta (Instagram/Messenger)",
        description: "Automate responses for Instagram DM and Facebook Messenger.",
        icon: "https://upload.wikimedia.org/wikipedia/commons/7/7b/Meta_Platforms_Inc._logo.svg",
        fields: [{ name: "page_id", label: "Page ID", type: "text" }, { name: "access_token", label: "Access Token", type: "password" }]
    }
};

export default function IntegrationsPage() {
    const [integrations, setIntegrations] = useState<IntegrationProvider[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [configModal, setConfigModal] = useState<{ provider: string } | null>(null);
    const [configPayload, setConfigPayload] = useState<Record<string, string>>({});
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [fetchError, setFetchError] = useState<string | null>(null);

    const buildDefaultCards = () =>
        Object.keys(PROVIDER_METADATA).map(providerKey => ({
            id: providerKey,
            provider: providerKey,
            name: PROVIDER_METADATA[providerKey].name,
            description: PROVIDER_METADATA[providerKey].description,
            icon: PROVIDER_METADATA[providerKey].icon,
            status: "disconnected" as Status,
            lastChecked: undefined
        }));

    const fetchIntegrations = async () => {
        setIsLoading(true);
        setFetchError(null);
        const res = await apiClient.get<any[]>("/integrations");
        if (res.success && res.data) {
            const mapped = Object.keys(PROVIDER_METADATA).map(providerKey => {
                const backendRecord = res.data?.find(r => r.provider === providerKey);
                return {
                    id: backendRecord?.id || providerKey,
                    provider: providerKey,
                    name: PROVIDER_METADATA[providerKey].name,
                    description: PROVIDER_METADATA[providerKey].description,
                    icon: PROVIDER_METADATA[providerKey].icon,
                    status: backendRecord?.status || "disconnected",
                    lastChecked: backendRecord?.last_checked_at ? new Date(backendRecord.last_checked_at).toLocaleTimeString() : undefined
                };
            });
            setIntegrations(mapped as any);
        } else {
            setFetchError(res.error || "Failed to load integrations.");
            setIntegrations(buildDefaultCards() as any);
        }
        setIsLoading(false);
    };

    useEffect(() => {
        fetchIntegrations();
    }, []);

    const handleConnect = async () => {
        if (!configModal) return;
        setIsSubmitting(true);

        // Extract provider_workspace_id from payload based on provider
        let pwid = "";
        if (configModal.provider === "whatsapp") pwid = configPayload.phone_number_id;
        else if (configModal.provider === "meta") pwid = configPayload.page_id;
        else pwid = configPayload.org_id;

        const res = await apiClient.post(`/integrations/${configModal.provider}/connect`, {
            provider_workspace_id: pwid,
            config: configPayload
        });

        if (res.success) {
            setConfigModal(null);
            setConfigPayload({});
            await fetchIntegrations();
        } else {
            alert(res.error || "Failed to connect");
        }
        setIsSubmitting(false);
    };

    const handleDisconnect = async (provider: string) => {
        if (!confirm(`Are you sure you want to disconnect ${provider}?`)) return;
        setIsSubmitting(true);
        const res = await apiClient.post(`/integrations/${provider}/disconnect`);
        if (res.success) {
            await fetchIntegrations();
        }
        setIsSubmitting(false);
    };

    const getStatusInfo = (status: Status) => {
        switch (status) {
            case "connected":
                return { label: "Connected", icon: CheckCircle2, color: "text-emerald-600 bg-emerald-50 border-emerald-100" };
            case "error":
                return { label: "System Error", icon: AlertCircle, color: "text-red-600 bg-red-50 border-red-100" };
            default:
                return { label: "Disconnected", icon: XCircle, color: "text-slate-400 bg-slate-50 border-slate-100" };
        }
    };

    return (
        <div className="flex flex-col space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Integrations Hub</h1>
                    <p className="text-slate-500 text-sm">Connect your business tools to LeadPilot automation.</p>
                </div>
                <button
                    onClick={fetchIntegrations}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-4 py-2 border border-border rounded-md text-sm font-bold hover:bg-slate-50 transition-colors disabled:opacity-50"
                >
                    <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
                    Refresh
                </button>
            </div>

            {fetchError && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center gap-3">
                    <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
                    <p className="text-sm text-amber-800">{fetchError} Showing default status below.</p>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {isLoading ? (
                    <div className="col-span-full py-20 flex flex-col items-center justify-center text-slate-400 gap-4">
                        <Loader2 className="w-8 h-8 animate-spin" />
                        <p className="text-sm font-medium">Loading integrations...</p>
                    </div>
                ) : integrations.map((item) => {
                    const status = getStatusInfo(item.status);
                    const metadata = PROVIDER_METADATA[item.provider];
                    return (
                        <div key={item.provider} className="bg-white border border-border rounded-xl shadow-sm hover:shadow-md transition-shadow flex flex-col">
                            <div className="p-6 flex-1">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="w-12 h-12 rounded-lg border border-slate-100 p-2 flex items-center justify-center bg-white shadow-sm">
                                        <img src={metadata.icon} alt={metadata.name} className="w-8 h-8 object-contain" />
                                    </div>
                                    <div className={cn(
                                        "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold border",
                                        status.color
                                    )}>
                                        <status.icon className="w-3 h-3" />
                                        {status.label}
                                    </div>
                                </div>

                                <h3 className="font-bold text-slate-800 mb-1">{metadata.name}</h3>
                                <p className="text-xs text-slate-500 leading-relaxed min-h-[40px]">
                                    {metadata.description}
                                </p>

                                {item.lastChecked && (
                                    <div className="mt-4 flex items-center gap-2 text-[10px] text-slate-400 font-medium">
                                        <CheckCircle2 className="w-3 h-3" />
                                        Last checked: {item.lastChecked}
                                    </div>
                                )}
                            </div>

                            <div className="px-6 py-4 bg-slate-50/50 border-t border-border rounded-b-xl flex items-center justify-between gap-3">
                                {item.status === "connected" ? (
                                    <>
                                        <button
                                            onClick={() => setConfigModal({ provider: item.provider })}
                                            className="flex-1 px-3 py-2 bg-white border border-border rounded-md text-xs font-bold hover:bg-slate-50 transition-colors flex items-center justify-center gap-2"
                                        >
                                            <Settings2 className="w-3.5 h-3.5" />
                                            Update
                                        </button>
                                        {item.provider === "zoho" && (
                                            <Link href="/integrations/zoho/mapping" className="flex-1 px-3 py-2 bg-white border border-border rounded-md text-xs font-bold hover:bg-slate-50 transition-colors flex items-center justify-center gap-2">
                                                <Share2 className="w-3.5 h-3.5" />
                                                Mapping
                                            </Link>
                                        )}
                                        <button
                                            onClick={() => handleDisconnect(item.provider)}
                                            className="flex-1 px-3 py-2 bg-white border border-red-100 text-red-500 rounded-md text-xs font-bold hover:bg-red-50 transition-colors"
                                        >
                                            Disconnect
                                        </button>
                                    </>
                                ) : (
                                    <button
                                        onClick={() => setConfigModal({ provider: item.provider })}
                                        className="w-full px-3 py-2 bg-teal-600 text-white rounded-md text-xs font-bold hover:bg-teal-700 transition-colors flex items-center justify-center gap-2 shadow-sm"
                                    >
                                        <Plug className="w-3.5 h-3.5" />
                                        Connect {metadata.name}
                                    </button>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Custom Integration Banner relocated */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 flex items-center justify-between">
                <div>
                    <h2 className="text-sm font-bold text-slate-900 mb-1">Need a custom integration?</h2>
                    <p className="text-slate-500 text-xs">
                        Contact support for early access to our Developer API and Webhooks.
                    </p>
                </div>
                <button className="px-4 py-2 bg-white border border-border rounded-md font-bold text-xs hover:bg-slate-50 transition-colors flex items-center gap-2">
                    Talk to Support
                    <ExternalLink className="w-3 h-3" />
                </button>
            </div>

            {/* Configuration Modal */}
            {configModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md border border-border animate-in fade-in zoom-in-95 duration-200 overflow-hidden">
                        <div className="p-6 border-b border-border bg-slate-50/50">
                            <div className="flex items-center gap-3">
                                <img src={PROVIDER_METADATA[configModal.provider].icon} className="w-8 h-8" />
                                <div>
                                    <h3 className="font-bold text-slate-900">Connect {PROVIDER_METADATA[configModal.provider].name}</h3>
                                    <p className="text-xs text-slate-500">Enter your credentials to sync LeadPilot.</p>
                                </div>
                            </div>
                        </div>
                        <div className="p-6 space-y-4">
                            {PROVIDER_METADATA[configModal.provider].fields.map((f: any) => (
                                <div key={f.name} className="space-y-1.5">
                                    <label className="text-xs font-bold text-slate-600 uppercase tracking-wider">{f.label}</label>
                                    <input
                                        type={f.type}
                                        className="w-full px-4 py-2 border border-border rounded-lg outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all text-sm"
                                        placeholder={`Enter ${f.label.toLowerCase()}...`}
                                        value={configPayload[f.name] || ""}
                                        onChange={(e) => setConfigPayload({ ...configPayload, [f.name]: e.target.value })}
                                    />
                                </div>
                            ))}
                        </div>
                        <div className="p-6 bg-slate-50/50 border-t border-border flex gap-3">
                            <button
                                onClick={() => { setConfigModal(null); setConfigPayload({}); }}
                                className="flex-1 px-4 py-2 border border-border rounded-lg text-sm font-bold hover:bg-white transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleConnect}
                                disabled={isSubmitting}
                                className="flex-1 px-4 py-2 bg-teal-600 text-white rounded-lg text-sm font-bold hover:bg-teal-700 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                            >
                                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                                Save Connection
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
