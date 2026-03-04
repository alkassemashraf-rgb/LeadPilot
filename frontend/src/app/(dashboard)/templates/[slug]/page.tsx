"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
    ArrowLeft,
    Loader2,
    Zap,
    MessageSquare,
    MousePointerClick,
    Bot,
    Send,
    User,
    Tag,
    Database,
    GitBranch,
    Clock,
    AlertCircle,
    CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getTemplate, cloneTemplate, type TemplateDetail } from "@/lib/templates-api";
import { toast } from "sonner";

const NODE_TYPE_ICONS: Record<string, React.ReactNode> = {
    MESSAGE_INBOUND: <MessageSquare className="w-4 h-4" />,
    LEAD_AD_SUBMIT: <MousePointerClick className="w-4 h-4" />,
    AI_REPLY: <Bot className="w-4 h-4" />,
    SEND_MESSAGE: <Send className="w-4 h-4" />,
    HUMAN_HANDOVER: <User className="w-4 h-4" />,
    TAG_CONTACT: <Tag className="w-4 h-4" />,
    ZOHO_UPSERT_LEAD: <Database className="w-4 h-4" />,
    CONDITION: <GitBranch className="w-4 h-4" />,
    WAIT_DELAY: <Clock className="w-4 h-4" />,
};

const NODE_TYPE_LABELS: Record<string, string> = {
    MESSAGE_INBOUND: "Inbound Message",
    LEAD_AD_SUBMIT: "Lead Ad Submission",
    AI_REPLY: "AI Reply",
    SEND_MESSAGE: "Send Message",
    HUMAN_HANDOVER: "Human Handover",
    TAG_CONTACT: "Tag Contact",
    ZOHO_UPSERT_LEAD: "Zoho: Upsert Lead",
    CONDITION: "Condition (Coming Soon)",
    WAIT_DELAY: "Wait / Delay (Coming Soon)",
};

const INTEGRATION_LABELS: Record<string, string> = {
    zoho: "Zoho CRM",
    whatsapp: "WhatsApp",
    meta: "Meta (Messenger/Instagram)",
};

function FlowSummary({ graph }: { graph: Record<string, any> }) {
    const nodes: any[] = graph.nodes ?? [];
    const edges: any[] = graph.edges ?? [];

    const triggerNode = nodes.find((n: any) => n.type === "triggerNode");
    const actionNodes = nodes.filter((n: any) => n.type === "actionNode");

    return (
        <div className="space-y-3">
            {/* Trigger */}
            {triggerNode && (
                <div className="flex items-center gap-3 p-3.5 rounded-xl border border-teal-200/80 bg-gradient-to-r from-teal-50 to-transparent shadow-sm">
                    <div className="p-2.5 rounded-lg bg-teal-600 text-white shadow-sm">
                        <Zap className="w-4 h-4" />
                    </div>
                    <div>
                        <p className="text-[10px] font-bold text-teal-600 uppercase tracking-widest mb-0.5">
                            Trigger
                        </p>
                        <p className="text-sm font-semibold text-slate-900">
                            {NODE_TYPE_LABELS[triggerNode.data?.nodeType] ?? triggerNode.data?.nodeType}
                        </p>
                    </div>
                </div>
            )}

            {/* Steps */}
            {actionNodes.map((node: any, i: number) => (
                <div key={node.id} className="flex items-center gap-3 p-3.5 rounded-xl border border-slate-200 bg-white shadow-[0_2px_8px_-2px_rgba(0,0,0,0.05)] hover:shadow-md transition-all">
                    <div className="w-7 h-7 rounded-full border border-slate-200 bg-slate-50 flex items-center justify-center text-xs font-bold text-slate-500 shrink-0">
                        {i + 1}
                    </div>
                    <span className="text-slate-600 p-1.5 rounded-md bg-slate-50 border border-slate-100">
                        {NODE_TYPE_ICONS[node.data?.nodeType] ?? <Bot className="w-4 h-4" />}
                    </span>
                    <p className="text-sm font-semibold text-slate-800">
                        {NODE_TYPE_LABELS[node.data?.nodeType] ?? node.data?.nodeType}
                    </p>
                </div>
            ))}

            {actionNodes.length === 0 && (
                <p className="text-sm text-muted-foreground">No action steps configured.</p>
            )}

            <p className="text-xs text-muted-foreground">
                {edges.length} connection{edges.length !== 1 ? "s" : ""} in this flow
            </p>
        </div>
    );
}

export default function TemplateDetailPage() {
    const params = useParams();
    const slug = params.slug as string;
    const router = useRouter();

    const [template, setTemplate] = useState<TemplateDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [cloning, setCloning] = useState(false);
    const [cloneSuccess, setCloneSuccess] = useState(false);
    const [error, setError] = useState("");
    const [variableValues, setVariableValues] = useState<Record<string, string>>({});

    useEffect(() => {
        getTemplate(slug).then((res) => {
            if (res.success && res.data) {
                setTemplate(res.data);
                // Pre-fill defaults
                const defaults: Record<string, string> = {};
                for (const v of res.data.variables ?? []) {
                    if (v.default_value) defaults[v.key] = v.default_value;
                }
                setVariableValues(defaults);
            } else {
                setError("Template not found.");
            }
            setLoading(false);
        });
    }, [slug]);

    const handleClone = async () => {
        // Validate required variables
        const missingVars = (template?.variables ?? []).filter(
            (v) => v.required && !variableValues[v.key] && !v.default_value
        );
        if (missingVars.length > 0) {
            toast.error(`Please fill in: ${missingVars.map((v) => v.label).join(", ")}`);
            return;
        }
        setCloning(true);
        const hasVars = Object.keys(variableValues).length > 0;
        const res = await cloneTemplate(slug, undefined, hasVars ? variableValues : undefined);
        if (res.success && res.data) {
            setCloneSuccess(true);
            toast.success("Template cloned successfully");
            setTimeout(() => router.push(res.data!.redirect_path), 1000);
        } else {
            toast.error(res.error ?? "Failed to clone template.");
        }
        setCloning(false);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (error || !template) {
        return (
            <div className="p-8 max-w-4xl mx-auto space-y-4">
                <Link href="/templates" className="flex items-center gap-2 text-muted-foreground hover:text-foreground text-sm">
                    <ArrowLeft className="w-4 h-4" /> Back to Templates
                </Link>
                <div className="flex items-center gap-2 text-red-600">
                    <AlertCircle className="w-5 h-5" />
                    <p>{error || "Template not found."}</p>
                </div>
            </div>
        );
    }

    const hasPublishedVersion = !!template.latest_version;

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8">
            {/* Back */}
            <Link
                href="/templates"
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground text-sm w-fit"
            >
                <ArrowLeft className="w-4 h-4" />
                Back to Templates
            </Link>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left: Details */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="space-y-3">
                        <h1 className="text-3xl font-bold tracking-tight">{template.name}</h1>
                        {template.description && (
                            <p className="text-muted-foreground text-lg">{template.description}</p>
                        )}
                        <div className="flex flex-wrap gap-2">
                            {template.platforms.map((p) => (
                                <span
                                    key={p}
                                    className="text-xs font-bold px-3 py-1 rounded-full bg-slate-800 text-white uppercase tracking-wider shadow-sm"
                                >
                                    {p}
                                </span>
                            ))}
                            {template.industry_tags.map((tag) => (
                                <span
                                    key={tag}
                                    className="text-xs font-bold px-3 py-1 rounded-full bg-slate-50 border border-slate-200 text-slate-600 uppercase tracking-wider"
                                >
                                    {tag}
                                </span>
                            ))}
                        </div>
                    </div>

                    {/* Required integrations warning */}
                    {template.required_integrations.length > 0 && (
                        <div className="flex items-start gap-3 p-4 rounded-xl border border-amber-200 bg-amber-50 text-sm text-amber-800 shadow-sm relative overflow-hidden">
                            <div className="absolute left-0 top-0 bottom-0 w-1 bg-amber-400" />
                            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-amber-600" />
                            <div className="space-y-1.5">
                                <p className="font-semibold text-amber-900">Required integrations:</p>
                                <ul className="list-disc list-inside space-y-0.5 text-amber-700 font-medium ml-1">
                                    {template.required_integrations.map((int) => (
                                        <li key={int}>{INTEGRATION_LABELS[int] ?? int}</li>
                                    ))}
                                </ul>
                                <p className="pt-1 text-xs text-amber-600/90 font-medium">
                                    Make sure these are connected in your workspace settings before using this template.
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Flow Summary */}
                    <div className="space-y-3">
                        <h2 className="font-semibold text-lg">Flow Structure</h2>
                        {hasPublishedVersion ? (
                            <FlowSummary graph={template.latest_version!.builder_graph_json} />
                        ) : (
                            <p className="text-sm text-muted-foreground">
                                No published version available yet.
                            </p>
                        )}
                    </div>
                </div>

                {/* Right: CTA */}
                <div className="space-y-4">
                    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/50 space-y-5 sticky top-6">
                        <div>
                            <p className="text-sm font-medium text-foreground">
                                {hasPublishedVersion
                                    ? `Version ${template.latest_version!.version_number}`
                                    : "Not yet published"}
                            </p>
                            {template.latest_version?.published_at && (
                                <p className="text-xs text-muted-foreground">
                                    Published {new Date(template.latest_version.published_at).toLocaleDateString()}
                                </p>
                            )}
                        </div>

                        {/* Variable inputs */}
                        {hasPublishedVersion && (template.variables ?? []).length > 0 && (
                            <div className="space-y-3 border-t border-border pt-4">
                                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                    Customize
                                </p>
                                {template.variables.map((v) => (
                                    <div key={v.key} className="space-y-1">
                                        <label className="text-xs font-medium text-foreground flex items-center gap-1">
                                            {v.label}
                                            {v.required && <span className="text-red-500">*</span>}
                                        </label>
                                        {v.description && (
                                            <p className="text-[11px] text-muted-foreground">{v.description}</p>
                                        )}
                                        {v.var_type === "textarea" ? (
                                            <textarea
                                                className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 resize-none min-h-[60px]"
                                                placeholder={v.default_value ?? ""}
                                                value={variableValues[v.key] ?? ""}
                                                onChange={(e) =>
                                                    setVariableValues((prev) => ({ ...prev, [v.key]: e.target.value }))
                                                }
                                            />
                                        ) : (
                                            <input
                                                type={v.var_type === "number" ? "number" : v.var_type === "url" ? "url" : v.var_type === "phone" ? "tel" : "text"}
                                                className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                                                placeholder={v.default_value ?? ""}
                                                value={variableValues[v.key] ?? ""}
                                                onChange={(e) =>
                                                    setVariableValues((prev) => ({ ...prev, [v.key]: e.target.value }))
                                                }
                                            />
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}

                        {hasPublishedVersion ? (
                            <button
                                onClick={handleClone}
                                disabled={cloning || cloneSuccess}
                                className={cn(
                                    "w-full flex items-center justify-center gap-2 py-2.5 rounded-xl font-medium transition-colors",
                                    cloneSuccess
                                        ? "bg-teal-100 dark:bg-teal-900 text-teal-700 dark:text-teal-300"
                                        : "bg-teal-600 hover:bg-teal-700 text-white disabled:opacity-50"
                                )}
                            >
                                {cloning ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : cloneSuccess ? (
                                    <CheckCircle2 className="w-4 h-4" />
                                ) : (
                                    <Zap className="w-4 h-4" />
                                )}
                                {cloneSuccess ? "Opening canvas…" : "Use This Template"}
                            </button>
                        ) : (
                            <div className="text-center text-sm text-muted-foreground py-2">
                                Not available yet
                            </div>
                        )}

                        <Link
                            href="/templates"
                            className="block text-center text-sm text-muted-foreground hover:text-foreground transition-colors"
                        >
                            Browse all templates
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
