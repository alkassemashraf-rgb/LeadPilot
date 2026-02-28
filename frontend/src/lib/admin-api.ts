/**
 * Admin API client for LeadPilot Admin Portal.
 * Uses the admin JWT (stored separately from the product JWT).
 * Do NOT use apiClient from api.ts here — that sends the product token.
 */
import { adminAuth } from "./admin-auth";

// ---- Standalone admin fetch client ----------------------------------------

const getBaseUrl = () => {
    if (process.env.NEXT_PUBLIC_API_BASE_URL) return process.env.NEXT_PUBLIC_API_BASE_URL;
    if (typeof window !== "undefined" && window.location.hostname === "localhost") {
        return "http://localhost:8000";
    }
    return "";
};

interface ApiResponse<T = any> {
    success: boolean;
    data?: T;
    error?: string;
}

async function adminRequest<T = any>(
    path: string,
    options: RequestInit = {}
): Promise<ApiResponse<T>> {
    const base = getBaseUrl().replace(/\/$/, "");
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    const url = `${base}/api/v1${cleanPath}`;

    const token = adminAuth.getToken();
    const headers = new Headers(options.headers || {});
    if (token) headers.set("Authorization", `Bearer ${token}`);
    if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
        headers.set("Content-Type", "application/json");
    }

    try {
        const response = await fetch(url, { ...options, headers });

        if (response.status === 401 || response.status === 403) {
            adminAuth.logout();
            return { success: false, error: "Admin session expired. Please log in again." };
        }

        const contentType = response.headers.get("content-type");
        if (contentType?.includes("application/json")) {
            const json = await response.json();
            if (!response.ok) {
                return { success: false, error: json.error || json.detail || `Error (${response.status})` };
            }
            if ("success" in json) return json as ApiResponse<T>;
            return { success: true, data: json as T };
        }
        const text = await response.text();
        if (!response.ok) return { success: false, error: `Error (${response.status}): ${text.substring(0, 80)}` };
        return { success: true, data: text as any };
    } catch (err: any) {
        return { success: false, error: `Admin API unreachable: ${err.message || "Network error"}` };
    }
}

const adminClient = {
    get: <T = any>(path: string) => adminRequest<T>(path, { method: "GET" }),
    post: <T = any>(path: string, body?: any) =>
        adminRequest<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
    put: <T = any>(path: string, body?: any) =>
        adminRequest<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
    patch: <T = any>(path: string, body?: any) =>
        adminRequest<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
    delete: <T = any>(path: string) => adminRequest<T>(path, { method: "DELETE" }),
};

// ---- Type definitions -------------------------------------------------------

export interface ModuleConfig {
    module_name: string;
    is_enabled: boolean;
    config_json?: Record<string, unknown> | null;
    updated_at?: string | null;
}

export interface SystemOverview {
    platform: string;
    python_version: string;
    users_total: number;
    workspaces_total: number;
    audit_log_entries: number;
    modules: Record<string, boolean>;
}

export interface AuditLogEntry {
    id: string;
    actor_user_id?: string | null;
    actor_type?: string | null;
    action: string;
    entity_type: string;
    entity_id: string;
    outcome?: string | null;
    workspace_id?: string | null;
    agency_id?: string | null;
    metadata_json?: Record<string, unknown> | null;
    correlation_id?: string | null;
    ip_address?: string | null;
    user_agent?: string | null;
    request_path?: string | null;
    request_method?: string | null;
    error_code?: string | null;
    error_message?: string | null;
    created_at: string;
}

export interface RuntimeEventEntry {
    id: string;
    workspace_id?: string | null;
    event_type: string;
    source: string;
    correlation_id?: string | null;
    related_ids?: Record<string, string> | null;
    actor_user_id?: string | null;
    payload?: Record<string, unknown> | null;
    outcome?: string | null;
    error_message?: string | null;
    duration_ms?: number | null;
    created_at: string;
}

// ---- Admin API methods ------------------------------------------------------

export const adminApi = {
    // Auth
    login: (email: string, password: string) =>
        adminClient.post<{ access_token: string; token_type: string }>("/admin_auth/login", { email, password }),

    me: () =>
        adminClient.get<{ id: string; email: string; full_name: string; is_superuser: boolean; role?: any }>("/admin_auth/me"),

    // System overview
    getOverview: () => adminClient.get<SystemOverview>("/admin/overview"),

    // Modules (global)
    getModules: () => adminClient.get<ModuleConfig[]>("/admin/modules"),
    toggleModule: (module_name: string, enabled: boolean) =>
        adminClient.patch<ModuleConfig>(`/admin/modules/${module_name}`, { enabled }),

    // Modules (per workspace)
    getWorkspaceModules: (workspaceId: string) =>
        adminClient.get<{ module_name: string; is_enabled: boolean; overridden: boolean }[]>(
            `/admin/workspaces/${workspaceId}/modules`
        ),
    setWorkspaceModule: (workspaceId: string, moduleName: string, isEnabled: boolean) =>
        adminClient.patch(`/admin/workspaces/${workspaceId}/modules/${moduleName}`, { is_enabled: isEnabled }),

    // Users
    getUsers: (params?: { skip?: number; limit?: number; query?: string }) => {
        const qs = new URLSearchParams();
        if (params?.skip !== undefined) qs.set("skip", String(params.skip));
        if (params?.limit !== undefined) qs.set("limit", String(params.limit));
        if (params?.query) qs.set("query", params.query);
        return adminClient.get<{ items: any[]; total: number }>(`/admin/users?${qs.toString()}`);
    },
    toggleUserStatus: (userId: string, isActive: boolean) =>
        adminClient.post(`/admin/users/${userId}/toggle`, { is_active: isActive }),
    impersonateUser: (userId: string) =>
        adminClient.post<{ access_token: string }>(`/admin/users/${userId}/impersonate`, {}),

    // Workspaces
    getWorkspaces: (params?: { skip?: number; limit?: number; query?: string }) => {
        const qs = new URLSearchParams();
        if (params?.skip !== undefined) qs.set("skip", String(params.skip));
        if (params?.limit !== undefined) qs.set("limit", String(params.limit));
        if (params?.query) qs.set("query", params.query);
        return adminClient.get<{ items: any[]; total: number }>(`/admin/workspaces?${qs.toString()}`);
    },
    getWorkspaceDetail: (workspaceId: string) =>
        adminClient.get<any>(`/admin/workspaces/${workspaceId}`),

    // Audit log
    getAuditLog: (params?: {
        skip?: number; limit?: number; action?: string; entity_type?: string;
        actor_type?: string; outcome?: string; workspace_id?: string;
        agency_id?: string; date_from?: string; date_to?: string;
        correlation_id?: string;
    }) => {
        const qs = new URLSearchParams();
        if (params?.skip !== undefined) qs.set("skip", String(params.skip));
        if (params?.limit !== undefined) qs.set("limit", String(params.limit));
        if (params?.action) qs.set("action", params.action);
        if (params?.entity_type) qs.set("entity_type", params.entity_type);
        if (params?.actor_type) qs.set("actor_type", params.actor_type);
        if (params?.outcome) qs.set("outcome", params.outcome);
        if (params?.workspace_id) qs.set("workspace_id", params.workspace_id);
        if (params?.agency_id) qs.set("agency_id", params.agency_id);
        if (params?.date_from) qs.set("date_from", params.date_from);
        if (params?.date_to) qs.set("date_to", params.date_to);
        if (params?.correlation_id) qs.set("correlation_id", params.correlation_id);
        return adminClient.get<{ items: AuditLogEntry[]; total: number; skip: number; limit: number }>(
            `/admin/audit-log?${qs.toString()}`
        );
    },
    getAuditLogDetail: (logId: string) =>
        adminClient.get<AuditLogEntry>(`/admin/audit-log/${logId}`),

    // Runtime events (Mission 18)
    getRuntimeEvents: (params?: {
        skip?: number; limit?: number; source?: string; event_type?: string;
        outcome?: string; workspace_id?: string; correlation_id?: string;
        date_from?: string; date_to?: string;
    }) => {
        const qs = new URLSearchParams();
        if (params?.skip !== undefined) qs.set("skip", String(params.skip));
        if (params?.limit !== undefined) qs.set("limit", String(params.limit));
        if (params?.source) qs.set("source", params.source);
        if (params?.event_type) qs.set("event_type", params.event_type);
        if (params?.outcome) qs.set("outcome", params.outcome);
        if (params?.workspace_id) qs.set("workspace_id", params.workspace_id);
        if (params?.correlation_id) qs.set("correlation_id", params.correlation_id);
        if (params?.date_from) qs.set("date_from", params.date_from);
        if (params?.date_to) qs.set("date_to", params.date_to);
        return adminClient.get<{ items: RuntimeEventEntry[]; total: number; skip: number; limit: number }>(
            `/admin/runtime-events?${qs.toString()}`
        );
    },
    getRuntimeEventDetail: (eventId: string) =>
        adminClient.get<RuntimeEventEntry>(`/admin/runtime-events/${eventId}`),

    // Email logs + retry
    getEmailLogs: (params?: { status?: string; email_type?: string; skip?: number; limit?: number }) => {
        const qs = new URLSearchParams();
        if (params?.status) qs.set("status", params.status);
        if (params?.email_type) qs.set("email_type", params.email_type);
        if (params?.skip !== undefined) qs.set("skip", String(params.skip));
        if (params?.limit !== undefined) qs.set("limit", String(params.limit));
        return adminClient.get<{ items: any[]; total: number }>(`/admin/email-logs?${qs.toString()}`);
    },
    retryEmail: (outboxId: string) =>
        adminClient.post(`/admin/email-logs/${outboxId}/retry`),

    // Webhooks + replay
    getWebhooks: (params?: { provider?: string; status?: string; skip?: number; limit?: number }) => {
        const qs = new URLSearchParams();
        if (params?.provider) qs.set("provider", params.provider);
        if (params?.status) qs.set("status", params.status);
        if (params?.skip !== undefined) qs.set("skip", String(params.skip));
        if (params?.limit !== undefined) qs.set("limit", String(params.limit));
        return adminClient.get<{ items: any[] }>(`/admin/webhooks?${qs.toString()}`);
    },
    replayWebhook: (eventLogId: string) =>
        adminClient.post(`/admin/webhooks/${eventLogId}/replay`),

    // Dispatch
    getDispatchQueue: (params?: { skip?: number; limit?: number }) => {
        const qs = new URLSearchParams();
        if (params?.skip !== undefined) qs.set("skip", String(params.skip));
        if (params?.limit !== undefined) qs.set("limit", String(params.limit));
        return adminClient.get<{ items: any[]; total: number }>(`/admin/dispatch?${qs.toString()}`);
    },
    retryDispatch: (messageId: string) =>
        adminClient.patch(`/admin/dispatch/${messageId}/retry`),
    deadLetterDispatch: (messageId: string) =>
        adminClient.patch(`/admin/dispatch/${messageId}/dead-letter`),

    // Automations
    getAdminAutomations: (params?: { skip?: number; limit?: number }) => {
        const qs = new URLSearchParams();
        if (params?.skip !== undefined) qs.set("skip", String(params.skip));
        if (params?.limit !== undefined) qs.set("limit", String(params.limit));
        return adminClient.get<{ items: any[]; total: number }>(`/admin/automations?${qs.toString()}`);
    },
    disableFlow: (flowId: string) =>
        adminClient.patch(`/admin/automations/${flowId}/disable`),

    // Prompt configs
    getPromptConfigs: (params?: { skip?: number; limit?: number }) => {
        const qs = new URLSearchParams();
        if (params?.skip !== undefined) qs.set("skip", String(params.skip));
        if (params?.limit !== undefined) qs.set("limit", String(params.limit));
        return adminClient.get<{ items: any[]; total: number }>(`/admin/prompt-configs?${qs.toString()}`);
    },

    // Zoho health
    getZohoHealth: () =>
        adminClient.get<{ items: any[] }>("/admin/zoho-health"),

    // Monitoring (legacy)
    getIntegrations: () => adminClient.get<{ items: any[] }>("/admin/integrations"),
    getExecutions: () => adminClient.get<{ items: any[] }>("/admin/executions"),

    // Plans (Mission 14)
    getPlans: () => adminClient.get<{ items: any[] }>("/admin/plans"),
    createPlan: (data: { name: string; display_name: string; description?: string; sort_order?: number }) =>
        adminClient.post("/admin/plans", data),
    getPlanDetail: (planId: string) => adminClient.get<any>(`/admin/plans/${planId}`),
    updatePlan: (planId: string, data: { display_name?: string; description?: string; is_active?: boolean; sort_order?: number }) =>
        adminClient.put(`/admin/plans/${planId}`, data),
    setPlanEntitlements: (planId: string, entitlements: { module_key: string; hard_limit: number | null }[]) =>
        adminClient.put(`/admin/plans/${planId}/entitlements`, { entitlements }),

    // Workspace plan & usage (Mission 14)
    getWorkspacePlan: (workspaceId: string) =>
        adminClient.get<any>(`/admin/workspaces/${workspaceId}/plan`),
    assignWorkspacePlan: (workspaceId: string, planId: string) =>
        adminClient.put(`/admin/workspaces/${workspaceId}/plan`, { plan_id: planId }),
    getWorkspaceUsage: (workspaceId: string) =>
        adminClient.get<any>(`/admin/workspaces/${workspaceId}/usage`),
    setWorkspaceOverrides: (workspaceId: string, overrides: { module_key: string; hard_limit: number | null }[]) =>
        adminClient.put(`/admin/workspaces/${workspaceId}/overrides`, { overrides }),
    removeWorkspaceOverride: (workspaceId: string, moduleKey: string) =>
        adminClient.delete(`/admin/workspaces/${workspaceId}/overrides/${moduleKey}`),

    // Agencies (Mission 15)
    getAgencies: (params?: { skip?: number; limit?: number; query?: string }) => {
        const qs = new URLSearchParams();
        if (params?.skip !== undefined) qs.set("skip", String(params.skip));
        if (params?.limit !== undefined) qs.set("limit", String(params.limit));
        if (params?.query) qs.set("query", params.query);
        return adminClient.get<{ items: any[]; total: number }>(`/admin/agencies?${qs.toString()}`);
    },
    getAgencyDetail: (agencyId: string) =>
        adminClient.get<any>(`/admin/agencies/${agencyId}`),
    updateAgencyStatus: (agencyId: string, status: "active" | "suspended") =>
        adminClient.patch(`/admin/agencies/${agencyId}/status`, { status }),
    assignAgencyPlan: (agencyId: string, planId: string) =>
        adminClient.put(`/admin/agencies/${agencyId}/plan`, { plan_id: planId }),
};

// Canonical source: GET /api/v1/catalog/modules — prefer useCatalog("modules") for dynamic labels
export const MODULE_LABELS: Record<string, string> = {
    auth: "Authentication",
    email_engine: "Email Engine",
    email_verification: "Email Verification",
    prompt_studio: "Prompt Studio",
    knowledge_files: "Knowledge Files",
    integrations_hub: "Integrations Hub",
    integrations_connect: "Integration Connect",
    webhooks_ingestion: "Webhook Ingestion",
    runtime_engine: "Runtime Engine",
    dispatch_engine: "Dispatch Engine",
    inbox: "Inbox",
    zoho_sync: "Zoho Sync",
    analytics: "Analytics",
    automations: "Automations",
    diagnostics: "Diagnostics",
    admin_portal: "Admin Portal",
    support_impersonation_enabled: "Support Impersonation",
    dangerous_actions_enabled: "Dangerous Actions",
};

export const LOCKED_MODULES = new Set(["admin_portal"]);

// ---- System Settings -------------------------------------------------------

export async function getSystemSettings() {
    return adminRequest("/admin/system-settings");
}

export async function patchSystemSettings(settings: Record<string, any>) {
    return adminRequest("/admin/system-settings", {
        method: "PATCH",
        body: JSON.stringify({ settings }),
    });
}

// ---- Template Catalog Admin (Mission 27) -----------------------------------

export interface AdminTemplateItem {
    id: string;
    slug: string;
    name: string;
    description: string | null;
    category: string;
    industry_tags: string[];
    platforms: string[];
    required_integrations: string[];
    is_featured: boolean;
    is_active: boolean;
    created_at: string;
}

export interface AdminTemplateVersionItem {
    id: string;
    version_number: number;
    changelog: string | null;
    is_published: boolean;
    published_at: string | null;
    created_at: string;
}

export async function getAdminTemplates(skip = 0, limit = 50) {
    return adminRequest<{ items: AdminTemplateItem[]; total: number }>(
        `/admin/templates?skip=${skip}&limit=${limit}`
    );
}

export async function createAdminTemplate(payload: {
    slug: string;
    name: string;
    description?: string;
    category?: string;
    industry_tags?: string[];
    platforms?: string[];
    required_integrations?: string[];
    is_featured?: boolean;
}) {
    return adminRequest<{ id: string; slug: string; name: string }>("/admin/templates", {
        method: "POST",
        body: JSON.stringify(payload),
    });
}

export async function patchAdminTemplate(
    templateId: string,
    payload: {
        name?: string;
        description?: string;
        category?: string;
        is_featured?: boolean;
        is_active?: boolean;
        industry_tags?: string[];
        platforms?: string[];
        required_integrations?: string[];
    }
) {
    return adminRequest<{ id: string; updated: boolean }>(`/admin/templates/${templateId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
    });
}

export async function createTemplateVersion(
    templateId: string,
    payload: { builder_graph_json: Record<string, any>; changelog?: string }
) {
    return adminRequest<{ valid: boolean; id?: string; version_number?: number; errors?: any[] }>(
        `/admin/templates/${templateId}/versions`,
        {
            method: "POST",
            body: JSON.stringify(payload),
        }
    );
}

export async function publishTemplateVersion(templateId: string) {
    return adminRequest<{ published: boolean; version_number: number; published_at: string }>(
        `/admin/templates/${templateId}/publish`,
        { method: "POST" }
    );
}

export async function getTemplateVersions(templateId: string) {
    return adminRequest<AdminTemplateVersionItem[]>(`/admin/templates/${templateId}/versions`);
}
