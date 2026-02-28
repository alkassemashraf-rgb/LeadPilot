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
} from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Node type metadata
// ---------------------------------------------------------------------------

interface NodeMeta {
    label: string;
    icon: React.ReactNode;
    colorClass: string; // Tailwind border + header color
    summary: (config: Record<string, any>) => string | null;
    comingSoon?: boolean;
}

const NODE_META: Record<string, NodeMeta> = {
    AI_REPLY: {
        label: "AI Reply",
        icon: <Bot className="w-4 h-4" />,
        colorClass: "border-violet-400",
        summary: (c) => c.goal ? `Goal: ${String(c.goal).substring(0, 40)}` : null,
    },
    SEND_MESSAGE: {
        label: "Send Message",
        icon: <Send className="w-4 h-4" />,
        colorClass: "border-blue-400",
        summary: (c) => c.content ? `"${String(c.content).substring(0, 40)}"` : null,
    },
    HUMAN_HANDOVER: {
        label: "Human Handover",
        icon: <User className="w-4 h-4" />,
        colorClass: "border-orange-400",
        summary: () => "Route to human agent",
    },
    TAG_CONTACT: {
        label: "Tag Contact",
        icon: <Tag className="w-4 h-4" />,
        colorClass: "border-pink-400",
        summary: (c) => c.tag ? `Tag: ${c.tag}` : null,
    },
    ZOHO_UPSERT_LEAD: {
        label: "Zoho: Upsert Lead",
        icon: <Database className="w-4 h-4" />,
        colorClass: "border-amber-400",
        summary: () => "Sync to Zoho CRM",
    },
    CONDITION: {
        label: "Condition",
        icon: <GitBranch className="w-4 h-4" />,
        colorClass: "border-gray-400",
        summary: () => "Branch logic",
        comingSoon: true,
    },
    WAIT_DELAY: {
        label: "Wait / Delay",
        icon: <Clock className="w-4 h-4" />,
        colorClass: "border-gray-400",
        summary: () => "Pause flow",
        comingSoon: true,
    },
};

const FALLBACK_META: NodeMeta = {
    label: "Action",
    icon: <Bot className="w-4 h-4" />,
    colorClass: "border-gray-400",
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
                "relative group w-56 rounded-xl border-2 bg-card shadow-md transition-all",
                hasError ? "border-red-500 shadow-red-100" : meta.colorClass,
                selected ? "shadow-lg" : "",
                "hover:shadow-lg"
            )}
        >
            {/* Input handle */}
            <Handle
                type="target"
                position={Position.Top}
                className="!w-3 !h-3 !bg-foreground !border-2 !border-white"
            />

            {/* Delete button — appears on hover */}
            {onDelete && (
                <button
                    onClick={() => onDelete(id)}
                    className="absolute -top-2 -right-2 hidden group-hover:flex items-center justify-center w-5 h-5 rounded-full bg-red-500 text-white shadow-sm hover:bg-red-600 transition-colors z-10"
                    title="Remove node"
                >
                    <X className="w-3 h-3" />
                </button>
            )}

            {/* Body */}
            <div className="px-3 py-3 space-y-1.5">
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                        {meta.icon}
                        <span>{meta.label}</span>
                    </div>
                    {meta.comingSoon && (
                        <span className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 shrink-0">
                            Soon
                        </span>
                    )}
                </div>

                {summaryText && (
                    <p className="text-xs text-muted-foreground truncate pl-6">{summaryText}</p>
                )}

                {hasError && (
                    <div className="flex items-center gap-1 text-xs text-red-600">
                        <AlertCircle className="w-3 h-3 shrink-0" />
                        <span>Configuration required</span>
                    </div>
                )}
            </div>

            {/* Output handle */}
            <Handle
                type="source"
                position={Position.Bottom}
                className="!w-3 !h-3 !bg-foreground !border-2 !border-white"
            />
        </div>
    );
}

export default memo(ActionNode);
