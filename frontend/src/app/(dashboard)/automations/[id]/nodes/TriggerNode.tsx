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
                "relative w-56 rounded-[14px] border-2 bg-white shadow-sm transition-all duration-200 overflow-hidden",
                selected ? "border-teal-500 shadow-[0_0_0_4px_rgba(20,184,166,0.15)]" : "border-teal-300 hover:border-teal-400"
            )}
        >
            {/* Header */}
            <div className="flex items-center gap-2.5 px-3.5 py-2.5 bg-gradient-to-r from-teal-50 to-teal-50/10 border-b border-teal-100/80">
                <div className="p-1.5 rounded-md bg-teal-600 text-white shadow-sm">
                    <Zap className="w-3.5 h-3.5" />
                </div>
                <span className="text-[11px] font-bold uppercase tracking-widest text-teal-700">
                    Trigger
                </span>
            </div>

            {/* Body */}
            <div className="px-3.5 py-4 space-y-1.5 bg-white">
                <div className="flex items-center gap-2.5 text-sm font-semibold text-slate-800">
                    <span className="text-slate-500 bg-slate-50 p-1.5 rounded-md border border-slate-100">
                        {TRIGGER_ICONS[nodeType] ?? <Zap className="w-4 h-4" />}
                    </span>
                    <span className="truncate">{TRIGGER_LABELS[nodeType] ?? nodeType}</span>
                </div>
                {platform && (
                    <p className="text-xs font-medium text-slate-500 pl-9">
                        {PLATFORM_LABELS[platform] ?? platform}
                    </p>
                )}
            </div>

            {/* Output handle */}
            <Handle
                type="source"
                position={Position.Bottom}
                className="!w-3 !h-3 !bg-teal-500 !border-2 !border-white !-bottom-1.5"
            />
        </div>
    );
}

export default memo(TriggerNode);
