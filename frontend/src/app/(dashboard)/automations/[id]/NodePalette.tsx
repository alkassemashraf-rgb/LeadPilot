"use client";

import { useState, useEffect } from "react";
import { useCatalog, type CatalogEntry } from "@/lib/catalog";
import { apiClient } from "@/lib/api";
import {
    Zap, Bot, Send, User, Tag, Database, GitBranch, Clock,
    GripVertical, Lock, Shuffle, ArrowRightCircle, Filter, Map,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Icon map for catalog entries
// ---------------------------------------------------------------------------

const ICON_MAP: Record<string, React.ReactNode> = {
    bot: <Bot className="w-4 h-4" />,
    send: <Send className="w-4 h-4" />,
    user: <User className="w-4 h-4" />,
    tag: <Tag className="w-4 h-4" />,
    database: <Database className="w-4 h-4" />,
    "git-branch": <GitBranch className="w-4 h-4" />,
    clock: <Clock className="w-4 h-4" />,
    message: <Zap className="w-4 h-4" />,
    zap: <Zap className="w-4 h-4" />,
    shuffle: <Shuffle className="w-4 h-4" />,
    "arrow-right-circle": <ArrowRightCircle className="w-4 h-4" />,
    filter: <Filter className="w-4 h-4" />,
    map: <Map className="w-4 h-4" />,
};

// ---------------------------------------------------------------------------
// DraggablePaletteItem
// ---------------------------------------------------------------------------

interface PaletteItemProps {
    nodeType: string;
    label: string;
    iconHint: string;
    comingSoon?: boolean;
    isTrigger?: boolean;
    hasTrigger?: boolean;
    locked?: boolean;
}

function PaletteItem({
    nodeType,
    label,
    iconHint,
    comingSoon,
    isTrigger,
    hasTrigger,
    locked,
}: PaletteItemProps) {
    const icon = ICON_MAP[iconHint] ?? <Bot className="w-4 h-4" />;
    const disabled = locked || (isTrigger && hasTrigger);

    const onDragStart = (e: React.DragEvent) => {
        if (disabled) {
            e.preventDefault();
            return;
        }
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData(
            "application/reactflow-node",
            JSON.stringify({ nodeType, isTrigger })
        );
    };

    return (
        <div
            draggable={!disabled}
            onDragStart={onDragStart}
            className={cn(
                "flex items-center gap-2.5 px-3 py-2.5 rounded-xl border transition-all select-none group",
                disabled
                    ? "opacity-50 cursor-not-allowed border-transparent bg-slate-50"
                    : "border-transparent bg-white shadow-[0_1px_3px_0_rgba(0,0,0,0.02)] hover:border-teal-200 hover:shadow-md cursor-grab active:cursor-grabbing"
            )}
        >
            <GripVertical className={cn("w-3 h-3 shrink-0 transition-colors", disabled ? "text-slate-300" : "text-slate-300 group-hover:text-teal-400")} />
            <span className={cn("p-1.5 rounded-md", disabled ? "text-slate-400 bg-slate-100" : "text-teal-600 bg-teal-50")}>{icon}</span>
            <span className={cn("text-sm font-semibold flex-1 truncate", disabled ? "text-slate-500" : "text-slate-800")}>{label}</span>

            {locked && (
                <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded border bg-amber-50 text-amber-700 border-amber-200 shrink-0">
                    <Lock className="w-3 h-3" /> Upgrade
                </span>
            )}
            {comingSoon && !locked && (
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded bg-slate-100 text-slate-500 shrink-0">
                    Soon
                </span>
            )}
            {!locked && isTrigger && hasTrigger && (
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0 shadow-sm">
                    Added
                </span>
            )}
        </div>
    );
}

// ---------------------------------------------------------------------------
// NodePalette
// ---------------------------------------------------------------------------

interface NodePaletteProps {
    hasTrigger: boolean;
}

export default function NodePalette({ hasTrigger }: NodePaletteProps) {
    const { data: nodeTypes } = useCatalog<CatalogEntry[]>("automation-node-types");
    const { data: triggerTypes } = useCatalog<CatalogEntry[]>("automation-trigger-types");

    // Fetch workspace entitlements for module gating
    const [enabledModules, setEnabledModules] = useState<Set<string>>(new Set());
    useEffect(() => {
        apiClient.get<{ modules: { module_key: string; enabled: boolean }[] }>("/entitlements")
            .then((res) => {
                if (res.success && res.data) {
                    setEnabledModules(new Set(
                        res.data.modules.filter((m) => m.enabled).map((m) => m.module_key)
                    ));
                }
            });
    }, []);

    const isLocked = (node: CatalogEntry) => {
        const requiredModule = node.required_module as string | undefined;
        if (!requiredModule) return false;
        return !enabledModules.has(requiredModule);
    };

    return (
        <div className="w-64 flex flex-col border-r border-border bg-background/80 overflow-y-auto">
            <div className="px-4 py-3 border-b border-border">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Node Palette
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">Drag nodes onto the canvas</p>
            </div>

            {/* Triggers */}
            <div className="px-3 py-4 space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 px-1 mb-3">
                    Triggers
                </p>
                {triggerTypes?.map((t) => (
                    <PaletteItem
                        key={t.key}
                        nodeType={t.key}
                        label={t.label}
                        iconHint={t.icon_hint ?? "zap"}
                        isTrigger
                        hasTrigger={hasTrigger}
                    />
                )) ?? (
                        <div className="space-y-1.5">
                            <PaletteItem
                                nodeType="MESSAGE_INBOUND"
                                label="Inbound Message"
                                iconHint="message"
                                isTrigger
                                hasTrigger={hasTrigger}
                            />
                            <PaletteItem
                                nodeType="LEAD_AD_SUBMIT"
                                label="Lead Ad Submission"
                                iconHint="zap"
                                isTrigger
                                hasTrigger={hasTrigger}
                            />
                        </div>
                    )}
            </div>

            {/* Divider */}
            <div className="mx-3 border-t border-border" />

            {/* Agent Nodes */}
            <div className="px-3 py-4 space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 px-1 mb-3">
                    Agent Nodes
                </p>
                {nodeTypes?.filter((n) => [
                    "AI_REPLY", "AGENT_REPLY", "SEND_MESSAGE", "HUMAN_HANDOVER",
                    "TAG_CONTACT", "ZOHO_UPSERT_LEAD",
                ].includes(n.key)).map((n) => (
                    <PaletteItem
                        key={n.key}
                        nodeType={n.key}
                        label={n.label}
                        iconHint={n.icon_hint ?? "bot"}
                        comingSoon={n.runtime_supported === false}
                        locked={isLocked(n)}
                    />
                )) ?? (
                        <div className="space-y-1.5">
                            {[
                                { key: "AI_REPLY", label: "Agent Reply", iconHint: "bot" },
                                { key: "SEND_MESSAGE", label: "Send Message", iconHint: "send" },
                                { key: "HUMAN_HANDOVER", label: "Human Handover", iconHint: "user" },
                                { key: "TAG_CONTACT", label: "Tag Contact", iconHint: "tag" },
                                { key: "ZOHO_UPSERT_LEAD", label: "Zoho: Upsert Lead", iconHint: "database" },
                            ].map((n) => (
                                <PaletteItem key={n.key} nodeType={n.key} label={n.label} iconHint={n.iconHint} />
                            ))}
                        </div>
                    )}
            </div>

            {/* Divider */}
            <div className="mx-3 border-t border-border" />

            {/* Flow Control */}
            <div className="px-3 py-4 space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 px-1 mb-3">
                    Flow Control
                </p>
                {nodeTypes?.filter((n) => [
                    "CONDITION", "WAIT_DELAY", "PARALLEL", "AGENT_HANDOFF",
                ].includes(n.key)).map((n) => (
                    <PaletteItem
                        key={n.key}
                        nodeType={n.key}
                        label={n.label}
                        iconHint={n.icon_hint ?? "git-branch"}
                        comingSoon={n.runtime_supported === false}
                        locked={isLocked(n)}
                    />
                )) ?? (
                        <div className="space-y-1.5">
                            {[
                                { key: "CONDITION", label: "Condition", iconHint: "git-branch" },
                                { key: "WAIT_DELAY", label: "Wait / Delay", iconHint: "clock" },
                                { key: "PARALLEL", label: "Parallel", iconHint: "shuffle" },
                                { key: "AGENT_HANDOFF", label: "Agent Handoff", iconHint: "arrow-right-circle" },
                            ].map((n) => (
                                <PaletteItem key={n.key} nodeType={n.key} label={n.label} iconHint={n.iconHint} />
                            ))}
                        </div>
                    )}
            </div>

            {/* Divider */}
            <div className="mx-3 border-t border-border" />

            {/* Routing */}
            <div className="px-3 py-4 space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 px-1 mb-3">
                    Routing
                </p>
                {nodeTypes?.filter((n) => [
                    "QUALIFICATION_GATE", "INTENT_ROUTER",
                ].includes(n.key)).map((n) => (
                    <PaletteItem
                        key={n.key}
                        nodeType={n.key}
                        label={n.label}
                        iconHint={n.icon_hint ?? "filter"}
                        comingSoon={n.runtime_supported === false}
                        locked={isLocked(n)}
                    />
                )) ?? (
                        <div className="space-y-1.5">
                            {[
                                { key: "QUALIFICATION_GATE", label: "Qualification Gate", iconHint: "filter" },
                                { key: "INTENT_ROUTER", label: "Intent Router", iconHint: "map" },
                            ].map((n) => (
                                <PaletteItem key={n.key} nodeType={n.key} label={n.label} iconHint={n.iconHint} />
                            ))}
                        </div>
                    )}
            </div>
        </div>
    );
}
