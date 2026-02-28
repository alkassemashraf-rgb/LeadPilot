/**
 * Typed API wrappers for the Template Catalog workspace endpoints (Mission 27).
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
}

export interface TemplateVersion {
    id: string;
    version_number: number;
    builder_graph_json: Record<string, any>;
    changelog: string | null;
    published_at: string | null;
}

export interface TemplateDetail extends TemplateListItem {
    latest_version: TemplateVersion | null;
}

export interface TemplateFilters {
    category?: string;
    platform?: string;
    featured?: boolean;
    skip?: number;
    limit?: number;
}

export interface CloneResult {
    flow_id: string;
    flow_name: string;
    redirect_path: string;
    template_slug: string;
    required_integrations: string[];
}

// ---------------------------------------------------------------------------
// Template Catalog API
// ---------------------------------------------------------------------------

export function listTemplates(filters: TemplateFilters = {}) {
    const params = new URLSearchParams();
    if (filters.category) params.set("category", filters.category);
    if (filters.platform) params.set("platform", filters.platform);
    if (filters.featured !== undefined) params.set("featured", String(filters.featured));
    if (filters.skip !== undefined) params.set("skip", String(filters.skip));
    if (filters.limit !== undefined) params.set("limit", String(filters.limit));

    const query = params.toString() ? `?${params.toString()}` : "";
    return apiClient.get<TemplateListItem[]>(`/templates${query}`);
}

export function getTemplate(slug: string) {
    return apiClient.get<TemplateDetail>(`/templates/${slug}`);
}

export function cloneTemplate(slug: string, name?: string) {
    return apiClient.post<CloneResult>(`/templates/${slug}/clone`, { name: name || "" });
}
