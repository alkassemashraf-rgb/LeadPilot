"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Zap, MessageSquare, MousePointerClick } from "lucide-react";
import { cn } from "@/lib/utils";

const TRIGGER_ICONS: Record<string, React.ReactNode> = {
    MESSAGE_INBOUND: <MessageSquare className="w-4 h-4" />,
    LEAD_AD_SUBMIT: <MousePointerClick className="w-4 h-4" />,
};

const TRIGGER_LABELS: Record<string, string> = {
    MESSAGE_INBOUND: "Inbound Message",
    LEAD_AD_SUBMIT: "Lead Ad Submission",
};

const PLATFORM_LABELS: Record<string, string> = {
    whatsapp: "WhatsApp",
    meta: "Meta (Messenger / IG)",
};

function TriggerNode({ data, selected }: NodeProps) {
    const nodeType = data.nodeType as string;
    const platform = data.platform as string | undefined;

    return (
        <div
            className={cn(
                "relative w-56 rounded-xl border-2 bg-card shadow-md transition-shadow",
                selected ? "border-teal-500 shadow-teal-200" : "border-teal-400",
                "hover:shadow-lg"
            )}
        >
            {/* Header */}
            <div className="flex items-center gap-2 px-3 py-2 bg-teal-50 dark:bg-teal-950 rounded-t-xl border-b border-teal-200 dark:border-teal-800">
                <div className="p-1 rounded-md bg-teal-600 text-white">
                    <Zap className="w-3 h-3" />
                </div>
                <span className="text-xs font-semibold uppercase tracking-wide text-teal-700 dark:text-teal-300">
                    Trigger
                </span>
            </div>

            {/* Body */}
            <div className="px-3 py-3 space-y-1">
                <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                    {TRIGGER_ICONS[nodeType] ?? <Zap className="w-4 h-4" />}
                    <span>{TRIGGER_LABELS[nodeType] ?? nodeType}</span>
                </div>
                {platform && (
                    <p className="text-xs text-muted-foreground pl-6">
                        {PLATFORM_LABELS[platform] ?? platform}
                    </p>
                )}
            </div>

            {/* Output handle */}
            <Handle
                type="source"
                position={Position.Bottom}
                className="!w-3 !h-3 !bg-teal-500 !border-2 !border-white"
            />
        </div>
    );
}

export default memo(TriggerNode);
