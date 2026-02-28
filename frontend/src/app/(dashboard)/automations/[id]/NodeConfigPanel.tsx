"use client";

import { Bot, Send, User, Tag, Database, GitBranch, Clock, Info, X } from "lucide-react";
import type { BuilderNode } from "@/lib/automations-api";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

interface LabeledFieldProps {
    label: string;
    required?: boolean;
    children: React.ReactNode;
}

function LabeledField({ label, required, children }: LabeledFieldProps) {
    return (
        <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                {label}
                {required && <span className="text-red-500 ml-1">*</span>}
            </label>
            {children}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Per-type config forms
// ---------------------------------------------------------------------------

function AiReplyConfig({
    config,
    onChange,
}: {
    config: Record<string, any>;
    onChange: (updated: Record<string, any>) => void;
}) {
    const tasks: string[] = Array.isArray(config.tasks) ? config.tasks : [];

    const addTask = () => onChange({ ...config, tasks: [...tasks, ""] });
    const removeTask = (i: number) =>
        onChange({ ...config, tasks: tasks.filter((_, idx) => idx !== i) });
    const updateTask = (i: number, val: string) =>
        onChange({ ...config, tasks: tasks.map((t, idx) => (idx === i ? val : t)) });

    return (
        <div className="space-y-4">
            <LabeledField label="Goal" required>
                <textarea
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-teal-500 min-h-[80px]"
                    placeholder="e.g. Greet the user and collect contact info"
                    value={config.goal ?? ""}
                    onChange={(e) => onChange({ ...config, goal: e.target.value })}
                />
            </LabeledField>

            <LabeledField label="Tasks (optional)">
                <div className="space-y-2">
                    {tasks.map((task, i) => (
                        <div key={i} className="flex gap-2">
                            <input
                                className="flex-1 rounded-lg border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                                placeholder={`Task ${i + 1}`}
                                value={task}
                                onChange={(e) => updateTask(i, e.target.value)}
                            />
                            <button
                                onClick={() => removeTask(i)}
                                className="p-1.5 rounded-md text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950 transition-colors"
                            >
                                <X className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    ))}
                    <button
                        onClick={addTask}
                        className="text-xs text-teal-600 hover:text-teal-700 font-medium"
                    >
                        + Add task
                    </button>
                </div>
            </LabeledField>

            <LabeledField label="Extra Instructions (optional)">
                <textarea
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-teal-500 min-h-[60px]"
                    placeholder="Any additional context for the AI..."
                    value={config.extra_instructions ?? ""}
                    onChange={(e) => onChange({ ...config, extra_instructions: e.target.value })}
                />
            </LabeledField>
        </div>
    );
}

function SendMessageConfig({
    config,
    onChange,
}: {
    config: Record<string, any>;
    onChange: (updated: Record<string, any>) => void;
}) {
    return (
        <LabeledField label="Message Content" required>
            <textarea
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-teal-500 min-h-[120px]"
                placeholder="Enter the message to send..."
                value={config.content ?? ""}
                onChange={(e) => onChange({ ...config, content: e.target.value })}
            />
        </LabeledField>
    );
}

function HumanHandoverConfig({
    config,
    onChange,
}: {
    config: Record<string, any>;
    onChange: (updated: Record<string, any>) => void;
}) {
    return (
        <LabeledField label="Announcement Message (optional)">
            <input
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                placeholder="e.g. Transferring you to a human agent..."
                value={config.message ?? ""}
                onChange={(e) => onChange({ ...config, message: e.target.value })}
            />
        </LabeledField>
    );
}

function TagContactConfig({
    config,
    onChange,
}: {
    config: Record<string, any>;
    onChange: (updated: Record<string, any>) => void;
}) {
    return (
        <LabeledField label="Tag" required>
            <input
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                placeholder="e.g. qualified, interested, vip"
                value={config.tag ?? ""}
                onChange={(e) => onChange({ ...config, tag: e.target.value })}
            />
        </LabeledField>
    );
}

function ZohoUpsertConfig() {
    return (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 text-sm text-amber-800 dark:text-amber-300">
            <Info className="w-4 h-4 shrink-0 mt-0.5" />
            <p>
                Contact data will be synced to your connected Zoho CRM using the workspace lead
                mapping. Ensure Zoho integration is configured in Settings.
            </p>
        </div>
    );
}

function ComingSoonConfig({ nodeType }: { nodeType: string }) {
    return (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-900/40 border border-border text-sm text-muted-foreground">
            <Info className="w-4 h-4 shrink-0 mt-0.5" />
            <p>
                <strong>{nodeType}</strong> is coming soon and cannot be used in published
                automations yet. You can add it to the canvas for planning purposes.
            </p>
        </div>
    );
}

function TriggerConfig({
    config,
    onChange,
}: {
    config: Record<string, any>;
    onChange: (updated: Record<string, any>) => void;
}) {
    return (
        <LabeledField label="Keywords (optional)">
            <input
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                placeholder="hello, start, hi (comma-separated)"
                value={(config.keywords ?? []).join(", ")}
                onChange={(e) => {
                    const kw = e.target.value
                        .split(",")
                        .map((k) => k.trim())
                        .filter(Boolean);
                    onChange({ ...config, keywords: kw });
                }}
            />
            <p className="text-xs text-muted-foreground">
                Leave empty to trigger on any inbound message.
            </p>
        </LabeledField>
    );
}

// ---------------------------------------------------------------------------
// NodeConfigPanel
// ---------------------------------------------------------------------------

interface NodeConfigPanelProps {
    node: BuilderNode | null;
    onClose: () => void;
    onUpdateConfig: (nodeId: string, config: Record<string, any>) => void;
}

const NODE_TYPE_ICONS: Record<string, React.ReactNode> = {
    AI_REPLY: <Bot className="w-4 h-4" />,
    SEND_MESSAGE: <Send className="w-4 h-4" />,
    HUMAN_HANDOVER: <User className="w-4 h-4" />,
    TAG_CONTACT: <Tag className="w-4 h-4" />,
    ZOHO_UPSERT_LEAD: <Database className="w-4 h-4" />,
    CONDITION: <GitBranch className="w-4 h-4" />,
    WAIT_DELAY: <Clock className="w-4 h-4" />,
    MESSAGE_INBOUND: <Bot className="w-4 h-4" />,
    LEAD_AD_SUBMIT: <Bot className="w-4 h-4" />,
};

const NODE_TYPE_LABELS: Record<string, string> = {
    AI_REPLY: "AI Reply",
    SEND_MESSAGE: "Send Message",
    HUMAN_HANDOVER: "Human Handover",
    TAG_CONTACT: "Tag Contact",
    ZOHO_UPSERT_LEAD: "Zoho: Upsert Lead",
    CONDITION: "Condition",
    WAIT_DELAY: "Wait / Delay",
    MESSAGE_INBOUND: "Inbound Message",
    LEAD_AD_SUBMIT: "Lead Ad Submission",
};

export default function NodeConfigPanel({ node, onClose, onUpdateConfig }: NodeConfigPanelProps) {
    if (!node) {
        return (
            <div className="w-72 flex flex-col border-l border-border bg-background/80 items-center justify-center text-center px-6">
                <div className="p-3 rounded-full bg-muted mb-3">
                    <Info className="w-6 h-6 text-muted-foreground" />
                </div>
                <p className="text-sm font-medium text-muted-foreground">
                    Select a node to configure it
                </p>
            </div>
        );
    }

    const nodeType = node.data.nodeType;
    const config = node.data.config ?? {};
    const isTrigger = node.type === "triggerNode";

    const handleChange = (updated: Record<string, any>) => {
        onUpdateConfig(node.id, updated);
    };

    return (
        <div className="w-72 flex flex-col border-l border-border bg-background overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">
                        {NODE_TYPE_ICONS[nodeType] ?? <Bot className="w-4 h-4" />}
                    </span>
                    <span className="text-sm font-semibold">
                        {NODE_TYPE_LABELS[nodeType] ?? nodeType}
                    </span>
                    {isTrigger && (
                        <span className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-teal-100 dark:bg-teal-900 text-teal-600">
                            Trigger
                        </span>
                    )}
                </div>
                <button
                    onClick={onClose}
                    className="p-1 rounded-md hover:bg-muted transition-colors text-muted-foreground"
                >
                    <X className="w-4 h-4" />
                </button>
            </div>

            {/* Config body */}
            <div className="px-4 py-4 flex-1 space-y-4">
                {nodeType === "AI_REPLY" && (
                    <AiReplyConfig config={config} onChange={handleChange} />
                )}
                {nodeType === "SEND_MESSAGE" && (
                    <SendMessageConfig config={config} onChange={handleChange} />
                )}
                {nodeType === "HUMAN_HANDOVER" && (
                    <HumanHandoverConfig config={config} onChange={handleChange} />
                )}
                {nodeType === "TAG_CONTACT" && (
                    <TagContactConfig config={config} onChange={handleChange} />
                )}
                {nodeType === "ZOHO_UPSERT_LEAD" && <ZohoUpsertConfig />}
                {(nodeType === "CONDITION" || nodeType === "WAIT_DELAY") && (
                    <ComingSoonConfig nodeType={NODE_TYPE_LABELS[nodeType] ?? nodeType} />
                )}
                {isTrigger && (nodeType === "MESSAGE_INBOUND") && (
                    <TriggerConfig config={config} onChange={handleChange} />
                )}
                {isTrigger && nodeType === "LEAD_AD_SUBMIT" && (
                    <div className="text-sm text-muted-foreground">
                        Triggered automatically when a Meta Lead Ad form is submitted. No
                        configuration required.
                    </div>
                )}
            </div>

            {/* Node ID (debug) */}
            <div className="px-4 py-2 border-t border-border">
                <p className="text-[10px] text-muted-foreground/50 font-mono truncate">id: {node.id}</p>
            </div>
        </div>
    );
}
