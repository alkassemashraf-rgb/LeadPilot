/**
 * Catalog API client — fetches public data from the LeadPilot backend.
 * Used by Server Components with ISR (revalidate every 60s).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Base URL for the product app (login, signup, dashboard). */
export const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

// ── Types ────────────────────────────────────────────────────────────

export interface CatalogPlan {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  sort_order: number;
  entitlements: CatalogEntitlement[];
}

export interface CatalogEntitlement {
  module_key: string;
  hard_limit: number | null; // null = unlimited
}

export interface CatalogModule {
  key: string;
  label: string;
  is_enabled: boolean;
}

export interface CatalogProvider {
  key: string;
  label: string;
  description: string;
  icon_hint: string;
  fields: { name: string; label: string; type: string }[];
}

export interface CatalogTemplate {
  id: string;
  slug: string;
  name: string;
  description: string;
  category: string;
  industry_tags: string[];
  platforms: string[];
  required_integrations: string[];
  is_featured: boolean;
  clone_count: number;
}

export interface CatalogEnum {
  key: string;
  label: string;
}

// ── Generic fetcher ──────────────────────────────────────────────────

interface Envelope<T> {
  success: boolean;
  data: T;
  error: string | null;
}

async function fetchCatalog<T>(path: string): Promise<T> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/catalog${path}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return [] as unknown as T;
    const json: Envelope<T> = await res.json();
    return json.success ? json.data : ([] as unknown as T);
  } catch {
    return [] as unknown as T;
  }
}

// ── Typed fetchers ───────────────────────────────────────────────────

export async function getPlans(): Promise<CatalogPlan[]> {
  return fetchCatalog<CatalogPlan[]>("/plans");
}

export async function getModules(): Promise<CatalogModule[]> {
  return fetchCatalog<CatalogModule[]>("/modules");
}

export async function getIntegrationProviders(): Promise<CatalogProvider[]> {
  return fetchCatalog<CatalogProvider[]>("/integration-providers");
}

export async function getPublicTemplates(category?: string): Promise<CatalogTemplate[]> {
  const params = category ? `?category=${encodeURIComponent(category)}` : "";
  return fetchCatalog<CatalogTemplate[]>(`/templates${params}`);
}

export async function getTemplateCategories(): Promise<CatalogEnum[]> {
  return fetchCatalog<CatalogEnum[]>("/template-categories");
}

export async function getTemplatePlatforms(): Promise<CatalogEnum[]> {
  return fetchCatalog<CatalogEnum[]>("/template-platforms");
}
