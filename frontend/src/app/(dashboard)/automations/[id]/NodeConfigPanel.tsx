"use client";

import {
    Bot, Send, User, Tag, Database, GitBranch, Clock, Info, X,
    Shuffle, ArrowRightCircle, Filter, Map,
} from "lucide-react";
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
    const outputs: { key: string; label: string }[] = Array.isArray(config.output_schema) ? config.output_schema : [];

    const addTask = () => onChange({ ...config, tasks: [...tasks, ""] });
    const removeTask = (i: number) =>
        onChange({ ...config, tasks: tasks.filter((_, idx) => idx !== i) });
    const updateTask = (i: number, val: string) =>
        onChange({ ...config, tasks: tasks.map((t, idx) => (idx === i ? val : t)) });

    const addOutput = () => onChange({ ...config, output_schema: [...outputs, { key: "", label: "" }] });
    const removeOutput = (i: number) =>
        onChange({ ...config, output_schema: outputs.filter((_, idx) => idx !== i) });
    const updateOutput = (i: number, field: "key" | "label", val: string) =>
        onChange({ ...config, output_schema: outputs.map((o, idx) => (idx === i ? { ...o, [field]: val } : o)) });

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

            <LabeledField label="Expected Outputs (optional)">
                <div className="space-y-2">
                    {outputs.map((output, i) => (
                        <div key={i} className="flex gap-2">
                            <input
                                className="w-28 rounded-lg border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                                placeholder="Key"
                                value={output.key}
                                onChange={(e) => updateOutput(i, "key", e.target.value)}
                            />
                            <input
                                className="flex-1 rounded-lg border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                                placeholder="Label (e.g. Budget Range)"
                                value={output.label}
                                onChange={(e) => updateOutput(i, "label", e.target.value)}
                            />
                            <button
                                onClick={() => removeOutput(i)}
                                className="p-1.5 rounded-md text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950 transition-colors"
                            >
                                <X className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    ))}
                    <button
                        onClick={addOutput}
                        className="text-xs text-teal-600 hover:text-teal-700 font-medium"
                    >
                        + Add output field
                    </button>
                </div>
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

function ConditionConfig({
    config,
    onChange,
}: {
    config: Record<string, any>;
    onChange: (updated: Record<string, any>) => void;
}) {
    const CONDITION_TYPES = [
        { value: "qualification_status", label: "Qualification Status" },
        { value: "intent", label: "Detected Intent" },
        { value: "tag", label: "Contact Tag" },
        { value: "custom_field", label: "Custom Field" },
    ];
    const OPERATORS = [
        { value: "equals", label: "Equals" },
        { value: "not_equals", label: "Not Equals" },
        { value: "contains", label: "Contains" },
        { value: "greater_than", label: "Greater Than" },
        { value: "less_than", label: "Less Than" },
    ];

    return (
        <div className="space-y-4">
            <LabeledField label="Condition Type" required>
                <select
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                    value={config.condition_type ?? ""}
                    onChange={(e) => onChange({ ...config, condition_type: e.target.value })}
                >
                    <option value="">Select a condition type...</option>
                    {CONDITION_TYPES.map((ct) => (
                        <option key={ct.value} value={ct.value}>{ct.label}</option>
                    ))}
                </select>
            </LabeledField>
            <LabeledField label="Operator" required>
                <select
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                    value={config.operator ?? ""}
                    onChange={(e) => onChange({ ...config, operator: e.target.value })}
                >
                    <option value="">Select an operator...</option>
                    {OPERATORS.map((op) => (
                        <option key={op.value} value={op.value}>{op.label}</option>
                    ))}
                </select>
            </LabeledField>
            <LabeledField label="Value">
                <input
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                    placeholder="e.g. qualified"
                    value={config.value ?? ""}
                    onChange={(e) => onChange({ ...config, value: e.target.value })}
                />
            </LabeledField>
            <div className="flex items-start gap-2 p-2.5 rounded-lg bg-cyan-50 dark:bg-cyan-950/20 border border-cyan-200 text-xs text-cyan-700">
                <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <p>Connect the <strong>TRUE</strong> handle to the path taken when the condition passes, and <strong>FALSE</strong> to the fallback path.</p>
            </div>
        </div>
    );
}

function WaitDelayConfig({
    config,
    onChange,
}: {
    config: Record<string, any>;
    onChange: (updated: Record<string, any>) => void;
}) {
    const UNITS = [
        { value: "minutes", seconds: 60, label: "Minutes" },
        { value: "hours", seconds: 3600, label: "Hours" },
        { value: "days", seconds: 86400, label: "Days" },
    ];

    const unit = config.delay_unit ?? "hours";
    const unitEntry = UNITS.find((u) => u.value === unit) ?? UNITS[1];
    const displayValue = config.delay_seconds
        ? Math.round(Number(config.delay_seconds) / unitEntry.seconds)
        : "";

    const handleChange = (rawValue: string, rawUnit: string) => {
        const unitEntry2 = UNITS.find((u) => u.value === rawUnit) ?? UNITS[1];
        const seconds = Math.max(60, (Number(rawValue) || 0) * unitEntry2.seconds);
        onChange({ ...config, delay_seconds: seconds, delay_unit: rawUnit });
    };

    return (
        <div className="space-y-4">
            <LabeledField label="Delay Duration" required>
                <div className="flex gap-2">
                    <input
                        type="number"
                        min="1"
                        className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                        placeholder="e.g. 2"
                        value={displayValue}
                        onChange={(e) => handleChange(e.target.value, unit)}
                    />
                    <select
                        className="w-28 rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                        value={unit}
                        onChange={(e) => handleChange(String(displayValue), e.target.value)}
                    >
                        {UNITS.map((u) => (
                            <option key={u.value} value={u.value}>{u.label}</option>
                        ))}
                    </select>
                </div>
                <p className="text-xs text-muted-foreground mt-1">Minimum: 1 minute.</p>
            </LabeledField>
            <div className="flex items-start gap-2 p-2.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/20 border border-indigo-200 text-xs text-indigo-700">
                <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <p>Execution pauses here. The flow resumes after the delay via a background scheduler.</p>
            </div>
        </div>
    );
}

function ParallelConfig({
    config,
    onChange,
}: {
    config: Record<string, any>;
    onChange: (updated: Record<string, any>) => void;
}) {
    const AVAILABLE_AGENTS = [
        { value: "qualification", label: "Qualification Agent" },
        { value: "crm", label: "CRM Agent" },
        { value: "reply", label: "Reply Agent" },
        { value: "handover", label: "Handover Agent" },
    ];

    const selected: string[] = Array.isArray(config.agents) ? config.agents : [];

    const toggle = (value: string) => {
        const next = selected.includes(value)
            ? selected.filter((a) => a !== value)
            : [...selected, value];
        onChange({ ...config, agents: next });
    };

    return (
        <div className="space-y-4">
            <LabeledField label="Agents to run in parallel">
                <div className="space-y-2">
                    {AVAILABLE_AGENTS.map((agent) => (
                        <label key={agent.value} className="flex items-center gap-2.5 cursor-pointer group">
                            <input
                                type="checkbox"
                                className="w-4 h-4 rounded border-border text-teal-600 focus:ring-teal-500"
                                checked={selected.includes(agent.value)}
                                onChange={() => toggle(agent.value)}
                            />
                            <span className="text-sm text-slate-700 group-hover:text-slate-900">{agent.label}</span>
                        </label>
                    ))}
                </div>
            </LabeledField>
            <div className="flex items-start gap-2 p-2.5 rounded-lg bg-teal-50 dark:bg-teal-950/20 border border-teal-200 text-xs text-teal-700">
                <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <p>Selected agents will run simultaneously. Results are merged before continuing.</p>
            </div>
        </div>
    );
}

function AgentHandoffConfig({
    config,
    onChange,
}: {
    config: Record<string, any>;
    onChange: (updated: Record<string, any>) => void;
}) {
    const AGENTS = [
        { value: "qualification", label: "Qualification Agent" },
        { value: "crm", label: "CRM Agent" },
        { value: "reply", label: "Reply Agent" },
        { value: "handover", label: "Handover Agent" },
    ];

    return (
        <LabeledField label="Target Agent" required>
            <select
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                value={config.target_agent ?? ""}
                onChange={(e) => onChange({ ...config, target_agent: e.target.value })}
            >
                <option value="">Select an agent...</option>
                {AGENTS.map((a) => (
                    <option key={a.value} value={a.value}>{a.label}</option>
                ))}
            </select>
        </LabeledField>
    );
}

function QualificationGateConfig() {
    return (
        <div className="space-y-3">
            <div className="flex items-start gap-2 p-3 rounded-lg bg-lime-50 dark:bg-lime-950/20 border border-lime-200 text-sm text-lime-800">
                <Info className="w-4 h-4 shrink-0 mt-0.5" />
                <p>
                    Routes leads based on their qualification status. Connect the{" "}
                    <strong>QUALIFIED</strong> handle for qualified leads and the{" "}
                    <strong>UNQUALIFIED</strong> handle for those still being evaluated.
                </p>
            </div>
            <p className="text-xs text-muted-foreground">
                Qualification criteria are configured in your workspace settings.
            </p>
        </div>
    );
}

function IntentRouterConfig({
    config,
    onChange,
}: {
    config: Record<string, any>;
    onChange: (updated: Record<string, any>) => void;
}) {
    const routes: { intent: string; agent: string }[] = Array.isArray(config.routes) ? config.routes : [];

    const AGENTS = ["qualification", "crm", "reply", "handover"];

    const addRoute = () =>
        onChange({ ...config, routes: [...routes, { intent: "", agent: "reply" }] });
    const removeRoute = (i: number) =>
        onChange({ ...config, routes: routes.filter((_, idx) => idx !== i) });
    const updateRoute = (i: number, field: "intent" | "agent", val: string) =>
        onChange({
            ...config,
            routes: routes.map((r, idx) => (idx === i ? { ...r, [field]: val } : r)),
        });

    return (
        <div className="space-y-4">
            <LabeledField label="Intent → Agent Routes" required>
                <div className="space-y-2">
                    {routes.map((route, i) => (
                        <div key={i} className="flex gap-2 items-center">
                            <input
                                className="flex-1 rounded-lg border border-border bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                                placeholder="Intent (e.g. complaint)"
                                value={route.intent}
                                onChange={(e) => updateRoute(i, "intent", e.target.value)}
                            />
                            <select
                                className="w-28 rounded-lg border border-border bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                                value={route.agent}
                                onChange={(e) => updateRoute(i, "agent", e.target.value)}
                            >
                                {AGENTS.map((a) => (
                                    <option key={a} value={a}>{a}</option>
                                ))}
                            </select>
                            <button
                                onClick={() => removeRoute(i)}
                                className="p-1.5 rounded-md text-muted-foreground hover:text-red-500 hover:bg-red-50 transition-colors"
                            >
                                <X className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    ))}
                    <button
                        onClick={addRoute}
                        className="text-xs text-teal-600 hover:text-teal-700 font-medium"
                    >
                        + Add route
                    </button>
                </div>
            </LabeledField>
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
    AGENT_REPLY: <Bot className="w-4 h-4" />,
    SEND_MESSAGE: <Send className="w-4 h-4" />,
    HUMAN_HANDOVER: <User className="w-4 h-4" />,
    TAG_CONTACT: <Tag className="w-4 h-4" />,
    ZOHO_UPSERT_LEAD: <Database className="w-4 h-4" />,
    CONDITION: <GitBranch className="w-4 h-4" />,
    WAIT_DELAY: <Clock className="w-4 h-4" />,
    PARALLEL: <Shuffle className="w-4 h-4" />,
    AGENT_HANDOFF: <ArrowRightCircle className="w-4 h-4" />,
    QUALIFICATION_GATE: <Filter className="w-4 h-4" />,
    INTENT_ROUTER: <Map className="w-4 h-4" />,
    MESSAGE_INBOUND: <Bot className="w-4 h-4" />,
    LEAD_AD_SUBMIT: <Bot className="w-4 h-4" />,
};

const NODE_TYPE_LABELS: Record<string, string> = {
    AI_REPLY: "AI Reply",
    AGENT_REPLY: "Agent Reply",
    SEND_MESSAGE: "Send Message",
    HUMAN_HANDOVER: "Human Handover",
    TAG_CONTACT: "Tag Contact",
    ZOHO_UPSERT_LEAD: "Zoho: Upsert Lead",
    CONDITION: "Condition",
    WAIT_DELAY: "Wait / Delay",
    PARALLEL: "Parallel",
    AGENT_HANDOFF: "Agent Handoff",
    QUALIFICATION_GATE: "Qualification Gate",
    INTENT_ROUTER: "Intent Router",
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
                {(nodeType === "AI_REPLY" || nodeType === "AGENT_REPLY") && (
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
                {nodeType === "CONDITION" && (
                    <ConditionConfig config={config} onChange={handleChange} />
                )}
                {nodeType === "WAIT_DELAY" && (
                    <WaitDelayConfig config={config} onChange={handleChange} />
                )}
                {nodeType === "PARALLEL" && (
                    <ParallelConfig config={config} onChange={handleChange} />
                )}
                {nodeType === "AGENT_HANDOFF" && (
                    <AgentHandoffConfig config={config} onChange={handleChange} />
                )}
                {nodeType === "QUALIFICATION_GATE" && <QualificationGateConfig />}
                {nodeType === "INTENT_ROUTER" && (
                    <IntentRouterConfig config={config} onChange={handleChange} />
                )}
                {isTrigger && nodeType === "MESSAGE_INBOUND" && (
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
