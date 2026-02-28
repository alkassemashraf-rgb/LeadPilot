"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import {
    ReactFlow,
    Background,
    Controls,
    MiniMap,
    addEdge,
    useNodesState,
    useEdgesState,
    type Node,
    type Edge,
    type OnConnect,
    type NodeTypes,
    BackgroundVariant,
    ReactFlowProvider,
    useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import {
    ArrowLeft,
    CheckCircle2,
    AlertTriangle,
    Loader2,
    Play,
    Rocket,
    RotateCcw,
    ChevronDown,
    X,
    Save,
    Clock,
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
    getDraft,
    saveDraft,
    validateDraft,
    publishDraft,
    getVersions,
    rollbackToVersion,
    simulate,
    getFlow,
    type BuilderGraph,
    type BuilderNode,
    type BuilderEdge,
    type ValidationError,
    type FlowVersion,
    type SimulateStep,
} from "@/lib/automations-api";

import TriggerNode from "./nodes/TriggerNode";
import ActionNode from "./nodes/ActionNode";
import NodePalette from "./NodePalette";
import NodeConfigPanel from "./NodeConfigPanel";

// ---------------------------------------------------------------------------
// React Flow node types registration
// ---------------------------------------------------------------------------

const nodeTypes: NodeTypes = {
    triggerNode: TriggerNode,
    actionNode: ActionNode,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function builderNodesToRF(
    builderNodes: BuilderNode[],
    errorNodeIds: Set<string>,
    onDelete: (id: string) => void
): Node[] {
    return builderNodes.map((n) => ({
        id: n.id,
        type: n.type,
        position: n.position,
        data: {
            ...n.data,
            hasError: errorNodeIds.has(n.id),
            onDelete: n.type === "actionNode" ? onDelete : undefined,
        },
    }));
}

function rfNodesToBuilder(rfNodes: Node[]): BuilderNode[] {
    return rfNodes.map((n) => ({
        id: n.id,
        type: n.type as "triggerNode" | "actionNode",
        position: n.position,
        data: {
            nodeType: n.data.nodeType as string,
            platform: n.data.platform as string | undefined,
            config: (n.data.config as Record<string, any>) ?? {},
        },
    }));
}

function rfEdgesToBuilder(rfEdges: Edge[]): BuilderEdge[] {
    return rfEdges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        sourceHandle: e.sourceHandle ?? undefined,
    }));
}

function generateNodeId(): string {
    return `node-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
}

// ---------------------------------------------------------------------------
// Save status badge
// ---------------------------------------------------------------------------

type SaveStatus = "idle" | "saving" | "saved" | "error";

function SaveBadge({ status }: { status: SaveStatus }) {
    if (status === "idle") return null;
    return (
        <div
            className={cn(
                "flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full",
                status === "saving" && "text-muted-foreground bg-muted",
                status === "saved" && "text-teal-700 bg-teal-100 dark:bg-teal-950 dark:text-teal-300",
                status === "error" && "text-red-700 bg-red-100 dark:bg-red-950 dark:text-red-300"
            )}
        >
            {status === "saving" && <Loader2 className="w-3 h-3 animate-spin" />}
            {status === "saved" && <CheckCircle2 className="w-3 h-3" />}
            {status === "error" && <AlertTriangle className="w-3 h-3" />}
            {status === "saving" ? "Saving…" : status === "saved" ? "Saved" : "Save failed"}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Simulate Drawer
// ---------------------------------------------------------------------------

function SimulateDrawer({
    flowId,
    onClose,
}: {
    flowId: string;
    onClose: () => void;
}) {
    const [mockPayload, setMockPayload] = useState('{"content": "Hello", "sender": "+1234567890"}');
    const [result, setResult] = useState<{
        valid: boolean;
        steps: SimulateStep[];
        dispatch_blocked: boolean;
        message: string;
        errors?: ValidationError[];
    } | null>(null);
    const [loading, setLoading] = useState(false);
    const [payloadError, setPayloadError] = useState("");

    const run = async () => {
        setLoading(true);
        setPayloadError("");
        let parsed: Record<string, any> | undefined;
        try {
            parsed = JSON.parse(mockPayload);
        } catch {
            setPayloadError("Invalid JSON — fix the payload above.");
            setLoading(false);
            return;
        }
        const res = await simulate(flowId, parsed);
        if (res.success && res.data) setResult(res.data);
        setLoading(false);
    };

    return (
        <div className="absolute right-0 top-0 h-full w-96 bg-background border-l border-border shadow-xl z-30 flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <div className="flex items-center gap-2">
                    <Play className="w-4 h-4 text-teal-600" />
                    <span className="text-sm font-semibold">Simulate</span>
                </div>
                <button onClick={onClose} className="p-1 rounded hover:bg-muted text-muted-foreground">
                    <X className="w-4 h-4" />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
                <div className="space-y-2">
                    <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Mock Trigger Payload (JSON)
                    </label>
                    <textarea
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono resize-none focus:outline-none focus:ring-2 focus:ring-teal-500 min-h-[100px]"
                        value={mockPayload}
                        onChange={(e) => setMockPayload(e.target.value)}
                    />
                    {payloadError && <p className="text-xs text-red-500">{payloadError}</p>}
                </div>

                <button
                    onClick={run}
                    disabled={loading}
                    className="w-full flex items-center justify-center gap-2 bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    Run Simulation
                </button>

                {result && (
                    <div className="space-y-3">
                        {!result.valid && result.errors && (
                            <div className="p-3 rounded-lg border border-red-200 bg-red-50 dark:bg-red-950/20 text-sm text-red-700 dark:text-red-300 space-y-1">
                                <p className="font-semibold">Validation errors:</p>
                                {result.errors.map((e, i) => (
                                    <p key={i} className="text-xs">{e.node_id}: {e.message}</p>
                                ))}
                            </div>
                        )}
                        {result.valid && (
                            <>
                                <div className="flex items-center gap-2 text-xs text-teal-700 dark:text-teal-300 font-medium">
                                    <CheckCircle2 className="w-3.5 h-3.5" />
                                    No real messages sent — simulation mode
                                </div>
                                <div className="space-y-2">
                                    {result.steps.map((step, i) => (
                                        <div
                                            key={i}
                                            className="p-3 rounded-lg border border-border bg-card text-xs space-y-1"
                                        >
                                            <div className="flex items-center justify-between">
                                                <span className="font-semibold text-foreground">
                                                    {i + 1}. {step.node_type}
                                                </span>
                                                <span className="text-muted-foreground text-[10px] bg-muted px-1.5 py-0.5 rounded-full">
                                                    blocked
                                                </span>
                                            </div>
                                            <p className="text-muted-foreground">{step.description}</p>
                                            {step.would_send && (
                                                <p className="text-foreground italic">
                                                    Would send: &ldquo;{step.would_send}&rdquo;
                                                </p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                                <p className="text-xs text-muted-foreground">{result.message}</p>
                            </>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Versions Dropdown
// ---------------------------------------------------------------------------

function VersionsDropdown({
    flowId,
    onRollback,
}: {
    flowId: string;
    onRollback: (newVersionNumber: number) => void;
}) {
    const [open, setOpen] = useState(false);
    const [versions, setVersions] = useState<FlowVersion[]>([]);
    const [loading, setLoading] = useState(false);
    const [rolling, setRolling] = useState<string | null>(null);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!open) return;
        setLoading(true);
        getVersions(flowId).then((res) => {
            if (res.success && res.data) setVersions(res.data);
            setLoading(false);
        });
    }, [open, flowId]);

    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
        };
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

    const handleRollback = async (v: FlowVersion) => {
        setRolling(v.id);
        const res = await rollbackToVersion(flowId, v.id);
        if (res.success && res.data) {
            onRollback(res.data.new_version_number);
        }
        setRolling(null);
        setOpen(false);
    };

    return (
        <div className="relative" ref={ref}>
            <button
                onClick={() => setOpen((o) => !o)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border hover:border-teal-400 text-sm font-medium text-foreground transition-colors"
            >
                <Clock className="w-4 h-4" />
                Versions
                <ChevronDown className={cn("w-3.5 h-3.5 transition-transform", open && "rotate-180")} />
            </button>

            {open && (
                <div className="absolute right-0 top-10 z-20 w-72 rounded-xl border border-border bg-background shadow-xl overflow-hidden">
                    <div className="px-3 py-2.5 border-b border-border text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Published Versions
                    </div>
                    {loading ? (
                        <div className="flex items-center justify-center p-4">
                            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                        </div>
                    ) : versions.length === 0 ? (
                        <div className="px-4 py-3 text-sm text-muted-foreground">
                            No published versions yet.
                        </div>
                    ) : (
                        <div className="max-h-60 overflow-y-auto divide-y divide-border">
                            {versions.map((v) => (
                                <div
                                    key={v.id}
                                    className="flex items-center justify-between px-3 py-2.5 hover:bg-muted/50"
                                >
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-medium">v{v.version_number}</span>
                                        {v.is_active && (
                                            <span className="text-[10px] bg-teal-100 dark:bg-teal-900 text-teal-600 dark:text-teal-300 px-1.5 py-0.5 rounded-full font-semibold uppercase tracking-wide">
                                                Live
                                            </span>
                                        )}
                                        <span className="text-xs text-muted-foreground">
                                            {new Date(v.created_at).toLocaleDateString()}
                                        </span>
                                    </div>
                                    {!v.is_active && (
                                        <button
                                            onClick={() => handleRollback(v)}
                                            disabled={rolling === v.id}
                                            className="flex items-center gap-1 text-xs text-teal-600 hover:text-teal-700 font-medium disabled:opacity-50"
                                        >
                                            {rolling === v.id ? (
                                                <Loader2 className="w-3 h-3 animate-spin" />
                                            ) : (
                                                <RotateCcw className="w-3 h-3" />
                                            )}
                                            Rollback
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Main Canvas Editor (inner, needs ReactFlowProvider context)
// ---------------------------------------------------------------------------

function CanvasEditor({ flowId }: { flowId: string }) {
    const router = useRouter();
    const { screenToFlowPosition } = useReactFlow();

    // Flow metadata
    const [flowName, setFlowName] = useState("Loading…");

    // React Flow state
    const [rfNodes, setRfNodes, onNodesChange] = useNodesState([]);
    const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState([]);

    // UI state
    const [selectedNode, setSelectedNode] = useState<BuilderNode | null>(null);
    const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
    const [validating, setValidating] = useState(false);
    const [publishing, setPublishing] = useState(false);
    const [errors, setErrors] = useState<ValidationError[]>([]);
    const [publishResult, setPublishResult] = useState<{
        success: boolean;
        version_number?: number;
        message?: string;
    } | null>(null);
    const [showSimulate, setShowSimulate] = useState(false);
    const [loading, setLoading] = useState(true);

    // Error node IDs set
    const errorNodeIds = useMemo(
        () => new Set(errors.map((e) => e.node_id)),
        [errors]
    );

    // Does the canvas already have a trigger?
    const hasTrigger = useMemo(
        () => rfNodes.some((n) => n.type === "triggerNode"),
        [rfNodes]
    );

    // ---------------------------------------------------------------------------
    // Delete node handler
    // ---------------------------------------------------------------------------

    const handleDeleteNode = useCallback((nodeId: string) => {
        setRfNodes((nds) => nds.filter((n) => n.id !== nodeId));
        setRfEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
        setSelectedNode((prev) => (prev?.id === nodeId ? null : prev));
    }, [setRfNodes, setRfEdges]);

    // ---------------------------------------------------------------------------
    // Load draft on mount
    // ---------------------------------------------------------------------------

    useEffect(() => {
        let active = true;
        async function load() {
            const [flowRes, draftRes] = await Promise.all([
                getFlow(flowId),
                getDraft(flowId),
            ]);

            if (!active) return;

            if (flowRes.success && flowRes.data) {
                setFlowName(flowRes.data.name);
            }

            if (draftRes.success && draftRes.data?.builder_graph_json) {
                const graph = draftRes.data.builder_graph_json;
                const nodes = builderNodesToRF(graph.nodes, new Set(), handleDeleteNode);
                setRfNodes(nodes);
                setRfEdges(graph.edges as Edge[]);
                // Restore validation errors if any
                const errs = draftRes.data.last_validation_errors?.errors ?? [];
                setErrors(errs);
            }
            setLoading(false);
        }
        load();
        return () => { active = false; };
    }, [flowId, setRfNodes, setRfEdges, handleDeleteNode]);

    // ---------------------------------------------------------------------------
    // Autosave (debounced)
    // ---------------------------------------------------------------------------

    const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    const triggerAutosave = useCallback(
        (nodes: Node[], edges: Edge[]) => {
            if (saveTimer.current) clearTimeout(saveTimer.current);
            setSaveStatus("saving");
            saveTimer.current = setTimeout(async () => {
                const graph: BuilderGraph = {
                    nodes: rfNodesToBuilder(nodes),
                    edges: rfEdgesToBuilder(edges),
                };
                const res = await saveDraft(flowId, graph);
                setSaveStatus(res.success ? "saved" : "error");
                // Reset to idle after 3s
                setTimeout(() => setSaveStatus("idle"), 3000);
            }, 2000);
        },
        [flowId]
    );

    const handleNodesChange: typeof onNodesChange = useCallback(
        (changes) => {
            onNodesChange(changes);
            setRfNodes((nds) => {
                triggerAutosave(nds, rfEdges);
                return nds;
            });
        },
        [onNodesChange, setRfNodes, triggerAutosave, rfEdges]
    );

    const handleEdgesChange: typeof onEdgesChange = useCallback(
        (changes) => {
            onEdgesChange(changes);
            setRfEdges((eds) => {
                triggerAutosave(rfNodes, eds);
                return eds;
            });
        },
        [onEdgesChange, setRfEdges, triggerAutosave, rfNodes]
    );

    // ---------------------------------------------------------------------------
    // Connect handler
    // ---------------------------------------------------------------------------

    const onConnect: OnConnect = useCallback(
        (connection) => {
            const newEdges = addEdge({ ...connection, id: `e-${Date.now()}` }, rfEdges);
            setRfEdges(newEdges);
            triggerAutosave(rfNodes, newEdges);
        },
        [rfEdges, setRfEdges, rfNodes, triggerAutosave]
    );

    // ---------------------------------------------------------------------------
    // Drop handler (from palette)
    // ---------------------------------------------------------------------------

    const onDrop = useCallback(
        (event) => {
            event.preventDefault();
            const raw = event.dataTransfer.getData("application/reactflow-node");
            if (!raw) return;
            let parsed: { nodeType: string; isTrigger: boolean };
            try { parsed = JSON.parse(raw); } catch { return; }

            if (parsed.isTrigger && hasTrigger) return; // Only one trigger

            const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });

            const newNode: Node = {
                id: generateNodeId(),
                type: parsed.isTrigger ? "triggerNode" : "actionNode",
                position,
                data: {
                    nodeType: parsed.nodeType,
                    platform: parsed.isTrigger ? "whatsapp" : undefined,
                    config: {},
                    onDelete: !parsed.isTrigger ? handleDeleteNode : undefined,
                },
            };

            setRfNodes((nds) => {
                const updated = [...nds, newNode];
                triggerAutosave(updated, rfEdges);
                return updated;
            });
        },
        [hasTrigger, screenToFlowPosition, handleDeleteNode, setRfNodes, rfEdges, triggerAutosave]
    );

    const onDragOver = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
    }, []);

    // ---------------------------------------------------------------------------
    // Node selection
    // ---------------------------------------------------------------------------

    const onNodeClick = useCallback(
        (_: React.MouseEvent, node: Node) => {
            setSelectedNode({
                id: node.id,
                type: node.type as "triggerNode" | "actionNode",
                position: node.position,
                data: {
                    nodeType: node.data.nodeType as string,
                    platform: node.data.platform as string | undefined,
                    config: (node.data.config as Record<string, any>) ?? {},
                },
            });
        },
        []
    );

    const onPaneClick = useCallback(() => setSelectedNode(null), []);

    // ---------------------------------------------------------------------------
    // Update node config (from config panel)
    // ---------------------------------------------------------------------------

    const handleUpdateConfig = useCallback(
        (nodeId: string, config: Record<string, any>) => {
            setRfNodes((nds) => {
                const updated = nds.map((n) =>
                    n.id === nodeId ? { ...n, data: { ...n.data, config } } : n
                );
                triggerAutosave(updated, rfEdges);
                return updated;
            });
            setSelectedNode((prev) =>
                prev?.id === nodeId ? { ...prev, data: { ...prev.data, config } } : prev
            );
        },
        [setRfNodes, rfEdges, triggerAutosave]
    );

    // ---------------------------------------------------------------------------
    // Validate
    // ---------------------------------------------------------------------------

    const handleValidate = useCallback(async () => {
        setValidating(true);
        setPublishResult(null);
        // First save latest state
        const graph: BuilderGraph = {
            nodes: rfNodesToBuilder(rfNodes),
            edges: rfEdgesToBuilder(rfEdges),
        };
        await saveDraft(flowId, graph);
        const res = await validateDraft(flowId);
        setValidating(false);
        if (res.success && res.data) {
            setErrors(res.data.errors);
            // Update node error state
            const errorSet = new Set(res.data.errors.map((e) => e.node_id));
            setRfNodes((nds) =>
                nds.map((n) => ({ ...n, data: { ...n.data, hasError: errorSet.has(n.id) } }))
            );
        }
    }, [flowId, rfNodes, rfEdges, setRfNodes]);

    // ---------------------------------------------------------------------------
    // Publish
    // ---------------------------------------------------------------------------

    const handlePublish = useCallback(async () => {
        setPublishing(true);
        setPublishResult(null);
        // Save first
        const graph: BuilderGraph = {
            nodes: rfNodesToBuilder(rfNodes),
            edges: rfEdgesToBuilder(rfEdges),
        };
        await saveDraft(flowId, graph);
        const res = await publishDraft(flowId);
        setPublishing(false);
        if (res.success && res.data) {
            if (res.data.success && res.data.published) {
                setErrors([]);
                setRfNodes((nds) =>
                    nds.map((n) => ({ ...n, data: { ...n.data, hasError: false } }))
                );
                setPublishResult({
                    success: true,
                    version_number: res.data.version_number,
                    message: `Published as v${res.data.version_number}`,
                });
            } else {
                setErrors(res.data.errors ?? []);
                const errorSet = new Set((res.data.errors ?? []).map((e) => e.node_id));
                setRfNodes((nds) =>
                    nds.map((n) => ({ ...n, data: { ...n.data, hasError: errorSet.has(n.id) } }))
                );
                setPublishResult({
                    success: false,
                    message: `${res.data.errors?.length ?? 0} error(s) must be fixed before publishing.`,
                });
            }
        }
    }, [flowId, rfNodes, rfEdges, setRfNodes]);

    // ---------------------------------------------------------------------------
    // Render
    // ---------------------------------------------------------------------------

    if (loading) {
        return (
            <div className="flex h-full items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            {/* ── Top Bar ── */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-background z-10 shrink-0">
                <div className="flex items-center gap-3">
                    <Link
                        href="/automations"
                        className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground transition-colors"
                    >
                        <ArrowLeft className="w-4 h-4" />
                    </Link>
                    <div>
                        <h1 className="text-sm font-semibold text-foreground leading-tight">{flowName}</h1>
                        <p className="text-xs text-muted-foreground">Canvas Editor</p>
                    </div>
                    <SaveBadge status={saveStatus} />
                </div>

                <div className="flex items-center gap-2">
                    {/* Validate */}
                    <button
                        onClick={handleValidate}
                        disabled={validating}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border hover:border-teal-400 text-sm font-medium text-foreground transition-colors disabled:opacity-50"
                    >
                        {validating ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <CheckCircle2 className="w-4 h-4" />
                        )}
                        Validate
                    </button>

                    {/* Simulate */}
                    <button
                        onClick={() => setShowSimulate((s) => !s)}
                        className={cn(
                            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors",
                            showSimulate
                                ? "border-teal-500 bg-teal-50 dark:bg-teal-950 text-teal-700 dark:text-teal-300"
                                : "border-border hover:border-teal-400 text-foreground"
                        )}
                    >
                        <Play className="w-4 h-4" />
                        Simulate
                    </button>

                    {/* Versions */}
                    <VersionsDropdown
                        flowId={flowId}
                        onRollback={(vn) =>
                            setPublishResult({ success: true, message: `Rolled back — now on v${vn}` })
                        }
                    />

                    {/* Publish */}
                    <button
                        onClick={handlePublish}
                        disabled={publishing}
                        className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors disabled:opacity-50 shadow-sm"
                    >
                        {publishing ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <Rocket className="w-4 h-4" />
                        )}
                        Publish
                    </button>
                </div>
            </div>

            {/* ── Publish / Error Banner ── */}
            {(publishResult || errors.length > 0) && (
                <div
                    className={cn(
                        "px-4 py-2.5 text-sm border-b flex items-start gap-2 shrink-0",
                        publishResult?.success
                            ? "bg-teal-50 dark:bg-teal-950/30 border-teal-200 dark:border-teal-800 text-teal-700 dark:text-teal-300"
                            : "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300"
                    )}
                >
                    {publishResult?.success ? (
                        <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                    ) : (
                        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1 space-y-0.5">
                        {publishResult?.message && <p className="font-medium">{publishResult.message}</p>}
                        {errors.length > 0 && !publishResult && (
                            <p className="font-medium">{errors.length} validation issue(s) found</p>
                        )}
                        {errors.length > 0 && (
                            <ul className="text-xs space-y-0.5 mt-1">
                                {errors.slice(0, 5).map((e, i) => (
                                    <li key={i}>
                                        <span className="font-mono">{e.node_id}</span>: {e.message}
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                    <button
                        onClick={() => { setPublishResult(null); setErrors([]); }}
                        className="p-0.5 hover:opacity-70"
                    >
                        <X className="w-3.5 h-3.5" />
                    </button>
                </div>
            )}

            {/* ── Three-Panel Layout ── */}
            <div className="flex flex-1 overflow-hidden relative">
                {/* Left: Palette */}
                <NodePalette hasTrigger={hasTrigger} />

                {/* Center: Canvas */}
                <div className="flex-1 h-full" onDragOver={onDragOver}>
                    <ReactFlow
                        nodes={rfNodes.map((n) => ({
                            ...n,
                            data: {
                                ...n.data,
                                hasError: errorNodeIds.has(n.id),
                                onDelete: n.type === "actionNode" ? handleDeleteNode : undefined,
                            },
                        }))}
                        edges={rfEdges}
                        onNodesChange={handleNodesChange}
                        onEdgesChange={handleEdgesChange}
                        onConnect={onConnect}
                        onDrop={onDrop}
                        onDragOver={onDragOver}
                        onNodeClick={onNodeClick}
                        onPaneClick={onPaneClick}
                        nodeTypes={nodeTypes}
                        fitView
                        deleteKeyCode="Delete"
                        className="bg-[#fafafa] dark:bg-[#0a0a0a]"
                    >
                        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
                        <Controls />
                        <MiniMap nodeStrokeWidth={3} />
                    </ReactFlow>
                </div>

                {/* Right: Config Panel or Simulate Drawer */}
                {showSimulate ? (
                    <SimulateDrawer flowId={flowId} onClose={() => setShowSimulate(false)} />
                ) : (
                    <NodeConfigPanel
                        node={selectedNode}
                        onClose={() => setSelectedNode(null)}
                        onUpdateConfig={handleUpdateConfig}
                    />
                )}
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Page wrapper (provides ReactFlow context)
// ---------------------------------------------------------------------------

export default function FlowDetailPage() {
    const params = useParams();
    const flowId = params.id as string;

    return (
        <div className="h-screen flex flex-col overflow-hidden">
            <ReactFlowProvider>
                <CanvasEditor flowId={flowId} />
            </ReactFlowProvider>
        </div>
    );
}
