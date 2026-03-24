"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
    Bot,
    Send,
    User,
    Tag,
    Database,
    GitBranch,
    Clock,
    X,
    AlertCircle,
    Shuffle,
    ArrowRightCircle,
    Filter,
    Map,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Node type metadata
// ---------------------------------------------------------------------------

interface NodeMeta {
    label: string;
    icon: React.ReactNode;
    colorClass: string; // Tailwind border + hover color
    headerClass: string; // Tailwind header background
    iconClass: string; // Tailwind icon background + text color
    summary: (config: Record<string, any>) => string | null;
    /** Nodes with conditional output handles (renders labeled true/false or qualified/unqualified handles) */
    multiHandle?: "true-false" | "qualified-unqualified";
    comingSoon?: boolean;
}

const NODE_META: Record<string, NodeMeta> = {
    AI_REPLY: {
        label: "AI Reply",
        icon: <Bot className="w-4 h-4" />,
        colorClass: "border-violet-300 hover:border-violet-400",
        headerClass: "bg-violet-50/50",
        iconClass: "text-violet-600 bg-violet-100/50 border-violet-200/50",
        summary: (c) => c.goal ? `Goal: ${String(c.goal).substring(0, 40)}` : null,
    },
    AGENT_REPLY: {
        label: "Agent Reply",
        icon: <Bot className="w-4 h-4" />,
        colorClass: "border-violet-300 hover:border-violet-400",
        headerClass: "bg-violet-50/50",
        iconClass: "text-violet-600 bg-violet-100/50 border-violet-200/50",
        summary: (c) => c.goal ? `Goal: ${String(c.goal).substring(0, 40)}` : null,
    },
    SEND_MESSAGE: {
        label: "Send Message",
        icon: <Send className="w-4 h-4" />,
        colorClass: "border-blue-300 hover:border-blue-400",
        headerClass: "bg-blue-50/50",
        iconClass: "text-blue-600 bg-blue-100/50 border-blue-200/50",
        summary: (c) => c.content ? `"${String(c.content).substring(0, 40)}"` : null,
    },
    HUMAN_HANDOVER: {
        label: "Human Handover",
        icon: <User className="w-4 h-4" />,
        colorClass: "border-orange-300 hover:border-orange-400",
        headerClass: "bg-orange-50/50",
        iconClass: "text-orange-600 bg-orange-100/50 border-orange-200/50",
        summary: () => "Route to human agent",
    },
    TAG_CONTACT: {
        label: "Tag Contact",
        icon: <Tag className="w-4 h-4" />,
        colorClass: "border-pink-300 hover:border-pink-400",
        headerClass: "bg-pink-50/50",
        iconClass: "text-pink-600 bg-pink-100/50 border-pink-200/50",
        summary: (c) => c.tag ? `Tag: ${c.tag}` : null,
    },
    ZOHO_UPSERT_LEAD: {
        label: "Zoho: Upsert Lead",
        icon: <Database className="w-4 h-4" />,
        colorClass: "border-amber-300 hover:border-amber-400",
        headerClass: "bg-amber-50/50",
        iconClass: "text-amber-600 bg-amber-100/50 border-amber-200/50",
        summary: () => "Sync to Zoho CRM",
    },
    CONDITION: {
        label: "Condition",
        icon: <GitBranch className="w-4 h-4" />,
        colorClass: "border-cyan-300 hover:border-cyan-400",
        headerClass: "bg-cyan-50/50",
        iconClass: "text-cyan-600 bg-cyan-100/50 border-cyan-200/50",
        summary: (c) => c.condition_type ? `If ${c.condition_type} ${c.operator ?? ""} ${c.value ?? ""}`.trim() : "Configure condition",
        multiHandle: "true-false",
    },
    WAIT_DELAY: {
        label: "Wait / Delay",
        icon: <Clock className="w-4 h-4" />,
        colorClass: "border-indigo-300 hover:border-indigo-400",
        headerClass: "bg-indigo-50/50",
        iconClass: "text-indigo-600 bg-indigo-100/50 border-indigo-200/50",
        summary: (c) => c.delay_seconds ? `Wait ${c.delay_seconds}s (${c.delay_unit ?? "seconds"})` : "Set delay",
    },
    PARALLEL: {
        label: "Parallel",
        icon: <Shuffle className="w-4 h-4" />,
        colorClass: "border-teal-300 hover:border-teal-400",
        headerClass: "bg-teal-50/50",
        iconClass: "text-teal-600 bg-teal-100/50 border-teal-200/50",
        summary: (c) => {
            const agents: string[] = Array.isArray(c.agents) ? c.agents : [];
            return agents.length ? `Run: ${agents.join(", ")}` : "Configure agents";
        },
    },
    AGENT_HANDOFF: {
        label: "Agent Handoff",
        icon: <ArrowRightCircle className="w-4 h-4" />,
        colorClass: "border-emerald-300 hover:border-emerald-400",
        headerClass: "bg-emerald-50/50",
        iconClass: "text-emerald-600 bg-emerald-100/50 border-emerald-200/50",
        summary: (c) => c.target_agent ? `→ ${c.target_agent}` : "Select agent",
    },
    QUALIFICATION_GATE: {
        label: "Qualification Gate",
        icon: <Filter className="w-4 h-4" />,
        colorClass: "border-lime-300 hover:border-lime-400",
        headerClass: "bg-lime-50/50",
        iconClass: "text-lime-600 bg-lime-100/50 border-lime-200/50",
        summary: () => "Route qualified / unqualified",
        multiHandle: "qualified-unqualified",
    },
    INTENT_ROUTER: {
        label: "Intent Router",
        icon: <Map className="w-4 h-4" />,
        colorClass: "border-rose-300 hover:border-rose-400",
        headerClass: "bg-rose-50/50",
        iconClass: "text-rose-600 bg-rose-100/50 border-rose-200/50",
        summary: (c) => {
            const routes: any[] = Array.isArray(c.routes) ? c.routes : [];
            return routes.length ? `${routes.length} route(s)` : "Configure routes";
        },
    },
};

const FALLBACK_META: NodeMeta = {
    label: "Action",
    icon: <Bot className="w-4 h-4" />,
    colorClass: "border-slate-300 hover:border-slate-400",
    headerClass: "bg-slate-50/50",
    iconClass: "text-slate-600 bg-slate-100/50 border-slate-200/50",
    summary: () => null,
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface ActionNodeData {
    nodeType: string;
    config: Record<string, any>;
    hasError?: boolean;
    onDelete?: (id: string) => void;
    [key: string]: unknown;
}

function ActionNode({ id, data, selected }: NodeProps) {
    const nodeType = (data as ActionNodeData).nodeType;
    const config = (data as ActionNodeData).config ?? {};
    const hasError = (data as ActionNodeData).hasError ?? false;
    const onDelete = (data as ActionNodeData).onDelete;

    const meta = NODE_META[nodeType] ?? FALLBACK_META;
    const summaryText = meta.summary(config);

    return (
        <div
            className={cn(
                "relative group w-56 rounded-[14px] border-2 bg-white shadow-sm transition-all duration-200 overflow-hidden",
                hasError ? "border-red-400 shadow-[0_0_0_4px_rgba(248,113,113,0.15)]" : meta.colorClass,
                selected ? "shadow-[0_0_0_4px_rgba(148,163,184,0.15)] border-slate-400" : ""
            )}
        >
            {/* Input handle */}
            <Handle
                type="target"
                position={Position.Top}
                className="!w-3 !h-3 !bg-slate-400 !border-2 !border-white !-top-1.5"
            />

            {/* Delete button — appears on hover */}
            {onDelete && (
                <button
                    onClick={() => onDelete(id)}
                    className="absolute -top-2.5 -right-2.5 hidden group-hover:flex items-center justify-center w-5 h-5 rounded-full bg-red-500 text-white shadow-sm hover:bg-red-600 transition-colors z-10"
                    title="Remove node"
                >
                    <X className="w-3 h-3" />
                </button>
            )}

            {/* Body */}
            <div className={cn("px-3.5 py-4 space-y-2", meta.headerClass)}>
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5 text-sm font-semibold text-slate-800">
                        <span className={cn("p-1.5 rounded-md border", meta.iconClass)}>
                            {meta.icon}
                        </span>
                        <span>{meta.label}</span>
                    </div>
                    {meta.comingSoon && (
                        <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-800 text-white shrink-0 shadow-sm">
                            Soon
                        </span>
                    )}
                </div>

                {summaryText && (
                    <p className="text-xs font-medium text-slate-500 truncate pl-9">{summaryText}</p>
                )}

                {hasError && (
                    <div className="flex items-center gap-1.5 text-xs font-medium text-red-600 bg-red-50 border border-red-100 p-2 rounded-lg mt-1">
                        <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                        <span>Configuration required</span>
                    </div>
                )}
            </div>

            {/* Output handle(s) — single by default, two for branching nodes */}
            {meta.multiHandle === "true-false" ? (
                <div className="relative h-4 flex justify-between px-6">
                    <div className="relative flex flex-col items-center">
                        <span className="text-[9px] font-bold text-emerald-600 mb-0.5">TRUE</span>
                        <Handle
                            type="source"
                            position={Position.Bottom}
                            id="true"
                            className="!w-3 !h-3 !bg-emerald-400 !border-2 !border-white !static !transform-none"
                        />
                    </div>
                    <div className="relative flex flex-col items-center">
                        <span className="text-[9px] font-bold text-red-500 mb-0.5">FALSE</span>
                        <Handle
                            type="source"
                            position={Position.Bottom}
                            id="false"
                            className="!w-3 !h-3 !bg-red-400 !border-2 !border-white !static !transform-none"
                        />
                    </div>
                </div>
            ) : meta.multiHandle === "qualified-unqualified" ? (
                <div className="relative h-4 flex justify-between px-4">
                    <div className="relative flex flex-col items-center">
                        <span className="text-[9px] font-bold text-lime-600 mb-0.5">QUALIFIED</span>
                        <Handle
                            type="source"
                            position={Position.Bottom}
                            id="qualified"
                            className="!w-3 !h-3 !bg-lime-500 !border-2 !border-white !static !transform-none"
                        />
                    </div>
                    <div className="relative flex flex-col items-center">
                        <span className="text-[9px] font-bold text-slate-500 mb-0.5">UNQUALIFIED</span>
                        <Handle
                            type="source"
                            position={Position.Bottom}
                            id="unqualified"
                            className="!w-3 !h-3 !bg-slate-400 !border-2 !border-white !static !transform-none"
                        />
                    </div>
                </div>
            ) : (
                <Handle
                    type="source"
                    position={Position.Bottom}
                    className="!w-3 !h-3 !bg-slate-400 !border-2 !border-white !-bottom-1.5"
                />
            )}
        </div>
    );
}

export default memo(ActionNode);
