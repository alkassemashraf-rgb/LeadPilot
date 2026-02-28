"use client";

import { useCatalog, type CatalogEntry } from "@/lib/catalog";
import { Zap, Bot, Send, User, Tag, Database, GitBranch, Clock, GripVertical } from "lucide-react";
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
}

function PaletteItem({
    nodeType,
    label,
    iconHint,
    comingSoon,
    isTrigger,
    hasTrigger,
}: PaletteItemProps) {
    const icon = ICON_MAP[iconHint] ?? <Bot className="w-4 h-4" />;
    const disabled = isTrigger && hasTrigger;

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
                "flex items-center gap-2.5 px-3 py-2 rounded-lg border transition-colors cursor-grab active:cursor-grabbing select-none",
                disabled
                    ? "opacity-40 cursor-not-allowed border-border bg-card"
                    : "border-border bg-card hover:border-teal-400 hover:bg-teal-50 dark:hover:bg-teal-950/40"
            )}
        >
            <GripVertical className="w-3 h-3 text-muted-foreground/50 shrink-0" />
            <span className="text-foreground/70">{icon}</span>
            <span className="text-sm font-medium text-foreground flex-1 truncate">{label}</span>
            {comingSoon && (
                <span className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 shrink-0">
                    Soon
                </span>
            )}
            {disabled && (
                <span className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-teal-100 dark:bg-teal-900 text-teal-600 shrink-0">
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

    return (
        <div className="w-64 flex flex-col border-r border-border bg-background/80 overflow-y-auto">
            <div className="px-4 py-3 border-b border-border">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Node Palette
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">Drag nodes onto the canvas</p>
            </div>

            {/* Triggers */}
            <div className="px-3 py-3 space-y-1.5">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-1 mb-2">
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

            {/* Action Nodes */}
            <div className="px-3 py-3 space-y-1.5">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-1 mb-2">
                    Actions
                </p>
                {nodeTypes?.map((n) => (
                    <PaletteItem
                        key={n.key}
                        nodeType={n.key}
                        label={n.label}
                        iconHint={n.icon_hint ?? "bot"}
                        comingSoon={n.runtime_supported === false}
                    />
                )) ?? (
                    <div className="space-y-1.5">
                        {[
                            { key: "AI_REPLY", label: "AI Reply", iconHint: "bot" },
                            { key: "SEND_MESSAGE", label: "Send Message", iconHint: "send" },
                            { key: "HUMAN_HANDOVER", label: "Human Handover", iconHint: "user" },
                            { key: "TAG_CONTACT", label: "Tag Contact", iconHint: "tag" },
                            { key: "ZOHO_UPSERT_LEAD", label: "Zoho: Upsert Lead", iconHint: "database" },
                            { key: "CONDITION", label: "Condition", iconHint: "git-branch", comingSoon: true },
                            { key: "WAIT_DELAY", label: "Wait / Delay", iconHint: "clock", comingSoon: true },
                        ].map((n) => (
                            <PaletteItem
                                key={n.key}
                                nodeType={n.key}
                                label={n.label}
                                iconHint={n.iconHint}
                                comingSoon={"comingSoon" in n ? n.comingSoon : false}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
