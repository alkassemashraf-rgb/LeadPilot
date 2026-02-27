"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
    ArrowLeft,
    Save,
    RefreshCw,
    Loader2,
    CheckCircle2,
    AlertCircle,
    Database,
    ArrowRightLeft
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { apiClient } from "@/lib/api";
import { useLookups } from "@/lib/lookups";
import { toast } from "sonner";

interface ZohoField {
    api_name: string;
    label: string;
    data_type: string;
}

interface MappingConfig {
    module_name: string;
    dedupe_strategy: string;
    field_mappings: Record<string, string>;
}

export default function ZohoMappingPage() {
    const router = useRouter();
    const lookups = useLookups();
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [zohoFields, setZohoFields] = useState<ZohoField[]>([]);
    const [config, setConfig] = useState<MappingConfig>({
        module_name: "Leads",
        dedupe_strategy: "EMAIL_OR_PHONE",
        field_mappings: {
            first_name: "First_Name",
            last_name: "Last_Name",
            email: "Email",
            phone: "Phone",
            company: "Company",
            description: "Description"
        }
    });

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            // Parallel fetch
            const [mappingRes, fieldsRes] = await Promise.all([
                apiClient.get<MappingConfig>("/zoho/mapping"),
                apiClient.get<ZohoField[]>("/zoho/fields")
            ]);

            if (mappingRes.success && mappingRes.data) {
                // Merge with default to ensure all keys exist
                setConfig(prev => ({
                    ...prev,
                    ...mappingRes.data,
                    field_mappings: { ...prev.field_mappings, ...mappingRes.data?.field_mappings }
                }));
            }

            if (fieldsRes.success && fieldsRes.data) {
                setZohoFields(fieldsRes.data);
            } else {
                toast.error("Failed to load Zoho fields");
            }
        } catch (error) {
            console.error("Failed to load mapping data", error);
            toast.error("Failed to load configuration");
        } finally {
            setIsLoading(false);
        }
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            const res = await apiClient.post("/zoho/mapping", config);
            if (res.success) {
                toast.success("Mapping configuration saved");
                router.push("/integrations");
            } else {
                toast.error(res.error || "Failed to save configuration");
            }
        } catch (error) {
            toast.error("An unexpected error occurred");
        } finally {
            setIsSaving(false);
        }
    };

    const updateMapping = (lpField: string, zohoField: string) => {
        setConfig(prev => ({
            ...prev,
            field_mappings: {
                ...prev.field_mappings,
                [lpField]: zohoField
            }
        }));
    };

    if (isLoading) {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto space-y-8 pb-20">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Link
                        href="/integrations"
                        className="p-2 -ml-2 hover:bg-slate-100 rounded-full transition-colors text-slate-500"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Zoho Lead Mapping</h1>
                        <p className="text-slate-500 text-sm">Configure how LeadPilot contacts sync to Zoho CRM Leads.</p>
                    </div>
                </div>
                <button
                    onClick={loadData}
                    className="p-2 hover:bg-slate-100 rounded-md text-slate-500 transition-colors"
                    title="Refresh Fields"
                >
                    <RefreshCw className="w-4 h-4" />
                </button>
            </div>

            {/* Main Config Card */}
            <div className="bg-white border border-border rounded-xl shadow-sm overflow-hidden">
                <div className="p-6 border-b border-border bg-slate-50/50 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-[#dca44f]/10 border border-[#dca44f]/20 flex items-center justify-center text-[#dca44f]">
                        <Database className="w-5 h-5" />
                    </div>
                    <div>
                        <h3 className="font-bold text-slate-900">Sync Strategy</h3>
                        <p className="text-xs text-slate-500">Define how we identify existing leads to avoid duplicates.</p>
                    </div>
                </div>

                <div className="p-6 grid gap-6 md:grid-cols-2">
                    <div className="space-y-2">
                        <label className="text-sm font-bold text-slate-700">Zoho Module</label>
                        <select
                            className="w-full px-3 py-2 border border-border rounded-lg bg-slate-50 text-slate-500 text-sm cursor-not-allowed"
                            disabled
                            value={config.module_name}
                        >
                            <option value="Leads">Leads</option>
                        </select>
                        <p className="text-[10px] text-slate-400">Currently only Leads module is supported.</p>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-bold text-slate-700">Deduplication Strategy</label>
                        <select
                            className="w-full px-3 py-2 border border-border rounded-lg bg-white text-slate-900 text-sm outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                            value={config.dedupe_strategy}
                            onChange={(e) => setConfig({ ...config, dedupe_strategy: e.target.value })}
                        >
                            {lookups.dedupeStrategies.map((s) => (
                                <option key={s.key} value={s.key}>{s.label}</option>
                            ))}
                        </select>
                        <p className="text-[10px] text-slate-400">
                            {config.dedupe_strategy === "EMAIL_OR_PHONE"
                                ? "We'll check both fields. If either matches, we'll update that record."
                                : "We'll use this single field to find existing records."}
                        </p>
                    </div>
                </div>
            </div>

            {/* Field Mapping Card */}
            <div className="bg-white border border-border rounded-xl shadow-sm overflow-hidden">
                <div className="p-6 border-b border-border bg-slate-50/50 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
                            <ArrowRightLeft className="w-5 h-5" />
                        </div>
                        <div>
                            <h3 className="font-bold text-slate-900">Field Mapping</h3>
                            <p className="text-xs text-slate-500">Map LeadPilot data to your Zoho CRM fields.</p>
                        </div>
                    </div>
                    {zohoFields.length === 0 && (
                        <div className="text-xs text-amber-600 bg-amber-50 px-3 py-1 rounded-full border border-amber-100 flex items-center gap-1.5">
                            <AlertCircle className="w-3 h-3" />
                            Using default fields
                        </div>
                    )}
                </div>

                <div className="divide-y divide-border">
                    {lookups.contactFields.map((field) => (
                        <div key={field.key} className="p-4 flex items-center gap-4 hover:bg-slate-50/50 transition-colors">
                            <div className="w-1/3">
                                <label className="text-sm font-medium text-slate-700 flex items-center gap-1.5">
                                    {field.label}
                                    {field.required && <span className="text-red-500">*</span>}
                                </label>
                                <p className="text-[10px] text-slate-400 font-mono mt-0.5">user.{field.key}</p>
                            </div>

                            <ArrowLeft className="w-4 h-4 text-slate-300 rotate-180 shrink-0" />

                            <div className="flex-1">
                                <select
                                    className="w-full px-3 py-2 border border-border rounded-lg bg-white text-slate-900 text-sm outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                                    value={config.field_mappings[field.key] || ""}
                                    onChange={(e) => updateMapping(field.key, e.target.value)}
                                >
                                    <option value="">-- Do not sync --</option>
                                    {zohoFields.map((zf) => (
                                        <option key={zf.api_name} value={zf.api_name}>
                                            {zf.label} ({zf.api_name})
                                        </option>
                                    ))}
                                    {/* Fallback if zohoFields is empty (MVP static list fallback in logic above, but visual fallback here) */}
                                    {zohoFields.length === 0 && (
                                        <>
                                            <option value="First_Name">First Name (First_Name)</option>
                                            <option value="Last_Name">Last Name (Last_Name)</option>
                                            <option value="Email">Email (Email)</option>
                                            <option value="Phone">Phone (Phone)</option>
                                            <option value="Company">Company (Company)</option>
                                            <option value="Description">Description (Description)</option>
                                        </>
                                    )}
                                </select>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-4">
                <Link
                    href="/integrations"
                    className="px-6 py-2.5 border border-border rounded-lg text-sm font-bold text-slate-600 hover:bg-slate-50 transition-colors"
                >
                    Cancel
                </Link>
                <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="px-6 py-2.5 bg-teal-600 text-white rounded-lg text-sm font-bold hover:bg-teal-700 transition-all flex items-center gap-2 shadow-sm disabled:opacity-70"
                >
                    {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save Configuration
                </button>
            </div>
        </div>
    );
}
