/**
 * Typed API wrappers for the Automation Builder v2 endpoints (Mission 27).
 * Uses apiClient from api.ts — injects product JWT + X-Workspace-ID automatically.
 */
import { apiClient } from "./api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BuilderNode {
    id: string;
    type: "triggerNode" | "actionNode";
    position: { x: number; y: number };
    data: {
        nodeType: string;
        platform?: string;
        config: Record<string, any>;
        hasError?: boolean;
    };
}

export interface BuilderEdge {
    id: string;
    source: string;
    target: string;
    sourceHandle?: string | null;
}

export interface BuilderGraph {
    nodes: BuilderNode[];
    edges: BuilderEdge[];
}

export interface ValidationError {
    node_id: string;
    field: string;
    message: string;
}

export interface FlowDraft {
    builder_graph_json: BuilderGraph | null;
    last_validation_errors: { errors: ValidationError[]; validated_at: string } | null;
    updated_at: string | null;
}

export interface FlowVersion {
    id: string;
    version_number: number;
    is_published: boolean;
    is_active: boolean;
    created_at: string;
}

export interface SimulateStep {
    node_id: string;
    node_type: string;
    description: string;
    dispatch_blocked: boolean;
    would_send?: string;
    would_dispatch?: boolean;
    mock_payload?: Record<string, any>;
}

export interface SimulateResult {
    valid: boolean;
    steps: SimulateStep[];
    dispatch_blocked: boolean;
    message: string;
    errors?: ValidationError[];
}

export interface Flow {
    id: string;
    name: string;
    description: string;
    status: "draft" | "published" | "archived";
    published_version_id: string | null;
    created_at: string;
    updated_at: string;
}

// ---------------------------------------------------------------------------
// Flow CRUD
// ---------------------------------------------------------------------------

export function createFlow(name: string, description?: string) {
    return apiClient.post<{ flow_id: string }>("/automations", { name, description });
}

export function listFlows() {
    return apiClient.get<Flow[]>("/automations");
}

export function getFlow(flowId: string) {
    return apiClient.get<Flow & { definition: any; version_number: number | null }>(
        `/automations/${flowId}`
    );
}

export function updateFlow(flowId: string, payload: { name?: string; description?: string }) {
    return apiClient.patch<{ id: string; name: string }>(`/automations/${flowId}`, payload);
}

export function deleteFlow(flowId: string) {
    return apiClient.delete<{ deleted: boolean }>(`/automations/${flowId}`);
}

// ---------------------------------------------------------------------------
// Draft
// ---------------------------------------------------------------------------

export function getDraft(flowId: string) {
    return apiClient.get<FlowDraft>(`/automations/${flowId}/draft`);
}

export function saveDraft(flowId: string, graph: BuilderGraph) {
    return apiClient.put<{ saved: boolean; updated_at: string }>(`/automations/${flowId}/draft`, {
        builder_graph_json: graph,
    });
}

export function validateDraft(flowId: string) {
    return apiClient.post<{ valid: boolean; errors: ValidationError[] }>(
        `/automations/${flowId}/draft/validate`
    );
}

// ---------------------------------------------------------------------------
// Publish / Versions / Rollback
// ---------------------------------------------------------------------------

export function publishDraft(flowId: string) {
    return apiClient.post<{
        success: boolean;
        published: boolean;
        version_id?: string;
        version_number?: number;
        published_at?: string;
        errors?: ValidationError[];
    }>(`/automations/${flowId}/publish`);
}

export function getVersions(flowId: string) {
    return apiClient.get<FlowVersion[]>(`/automations/${flowId}/versions`);
}

export function rollbackToVersion(flowId: string, versionId: string) {
    return apiClient.post<{
        new_version_id: string;
        new_version_number: number;
        rolled_back_to: number;
    }>(`/automations/${flowId}/rollback/${versionId}`);
}

// ---------------------------------------------------------------------------
// Simulate
// ---------------------------------------------------------------------------

export function simulate(flowId: string, mockPayload?: Record<string, any>) {
    return apiClient.post<SimulateResult>(`/automations/${flowId}/simulate`, {
        mock_payload: mockPayload ?? null,
    });
}
