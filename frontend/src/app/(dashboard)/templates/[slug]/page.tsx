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
                <div className="flex items-center gap-3 p-3 rounded-xl border border-teal-200 dark:border-teal-800 bg-teal-50 dark:bg-teal-950/20">
                    <div className="p-2 rounded-lg bg-teal-600 text-white">
                        <Zap className="w-4 h-4" />
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-teal-700 dark:text-teal-300 uppercase tracking-wide">
                            Trigger
                        </p>
                        <p className="text-sm font-medium text-foreground">
                            {NODE_TYPE_LABELS[triggerNode.data?.nodeType] ?? triggerNode.data?.nodeType}
                        </p>
                    </div>
                </div>
            )}

            {/* Steps */}
            {actionNodes.map((node: any, i: number) => (
                <div key={node.id} className="flex items-center gap-3 p-3 rounded-xl border border-border bg-card">
                    <div className="w-6 h-6 rounded-full border border-border bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground shrink-0">
                        {i + 1}
                    </div>
                    <span className="text-muted-foreground">
                        {NODE_TYPE_ICONS[node.data?.nodeType] ?? <Bot className="w-4 h-4" />}
                    </span>
                    <p className="text-sm font-medium text-foreground">
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

    useEffect(() => {
        getTemplate(slug).then((res) => {
            if (res.success && res.data) setTemplate(res.data);
            else setError("Template not found.");
            setLoading(false);
        });
    }, [slug]);

    const handleClone = async () => {
        setCloning(true);
        const res = await cloneTemplate(slug);
        if (res.success && res.data) {
            setCloneSuccess(true);
            setTimeout(() => router.push(res.data!.redirect_path), 1000);
        } else {
            setError(res.error ?? "Failed to clone template.");
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
                                    className="text-xs font-semibold px-2 py-1 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 uppercase tracking-wide"
                                >
                                    {p}
                                </span>
                            ))}
                            {template.industry_tags.map((tag) => (
                                <span
                                    key={tag}
                                    className="text-xs font-semibold px-2 py-1 rounded-full bg-muted text-muted-foreground uppercase tracking-wide"
                                >
                                    {tag}
                                </span>
                            ))}
                        </div>
                    </div>

                    {/* Required integrations warning */}
                    {template.required_integrations.length > 0 && (
                        <div className="flex items-start gap-2 p-4 rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/20 text-sm text-amber-700 dark:text-amber-300">
                            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                            <div>
                                <p className="font-semibold">Required integrations:</p>
                                <ul className="mt-1 list-disc list-inside space-y-0.5">
                                    {template.required_integrations.map((int) => (
                                        <li key={int}>{INTEGRATION_LABELS[int] ?? int}</li>
                                    ))}
                                </ul>
                                <p className="mt-2 text-xs">
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
                    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm space-y-4 sticky top-6">
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

                        {error && (
                            <p className="text-xs text-red-600 text-center">{error}</p>
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
