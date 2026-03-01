/**
 * Typed API wrappers for the Template Catalog workspace endpoints (Mission 27 + 32).
 * Uses apiClient from api.ts — injects product JWT + X-Workspace-ID automatically.
 */
import { apiClient } from "./api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TemplateListItem {
    id: string;
    slug: string;
    name: string;
    description: string | null;
    category: string;
    industry_tags: string[];
    platforms: string[];
    required_integrations: string[];
    is_featured: boolean;
    clone_count?: number;
}

export interface TemplateVersion {
    id: string;
    version_number: number;
    builder_graph_json: Record<string, any>;
    changelog: string | null;
    published_at: string | null;
}

export interface TemplateVariable {
    key: string;
    label: string;
    description: string | null;
    var_type: string;
    required: boolean;
    default_value: string | null;
}

export interface TemplateDetail extends TemplateListItem {
    latest_version: TemplateVersion | null;
    variables: TemplateVariable[];
}

export interface TemplateFilters {
    category?: string;
    platform?: string;
    featured?: boolean;
    sort?: string;
    skip?: number;
    limit?: number;
}

export interface CloneResult {
    flow_id: string;
    flow_name: string;
    redirect_path: string;
    template_slug: string;
    required_integrations: string[];
    variables_applied?: boolean;
}

// ---------------------------------------------------------------------------
// Template Catalog API
// ---------------------------------------------------------------------------

export function listTemplates(filters: TemplateFilters = {}) {
    const params = new URLSearchParams();
    if (filters.category) params.set("category", filters.category);
    if (filters.platform) params.set("platform", filters.platform);
    if (filters.featured !== undefined) params.set("featured", String(filters.featured));
    if (filters.sort) params.set("sort", filters.sort);
    if (filters.skip !== undefined) params.set("skip", String(filters.skip));
    if (filters.limit !== undefined) params.set("limit", String(filters.limit));

    const query = params.toString() ? `?${params.toString()}` : "";
    return apiClient.get<TemplateListItem[]>(`/templates${query}`);
}

export function getTemplate(slug: string) {
    return apiClient.get<TemplateDetail>(`/templates/${slug}`);
}

export function cloneTemplate(
    slug: string,
    name?: string,
    variableValues?: Record<string, string>
) {
    return apiClient.post<CloneResult>(`/templates/${slug}/clone`, {
        name: name || "",
        variable_values: variableValues || null,
    });
}
