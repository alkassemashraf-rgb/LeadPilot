/**
 * LeadPilot Robust API Client
 * - Handles JSON vs Text response detection
 * - Automatic Authorization header injection
 * - Workspace context management
 * - Consistent error handling
 */

import { auth } from "./auth";

const getBaseUrl = () => {
    if (process.env.NEXT_PUBLIC_API_BASE_URL) return process.env.NEXT_PUBLIC_API_BASE_URL;
    if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;

    if (typeof window !== "undefined") {
        // Browser context: localhost dev hits backend directly; production uses
        // relative paths so nginx can proxy /api/* to the backend.
        if (window.location.hostname === "localhost") {
            return "http://localhost:8000";
        }
        return ""; // relative URLs — works in any production deployment (HF, Docker, etc.)
    }
    // Server-side (SSR inside Docker): backend is accessible at 127.0.0.1:8000 internally.
    return "http://127.0.0.1:8000";
};

const API_BASE_URL = getBaseUrl();

if (!API_BASE_URL && typeof window !== "undefined" && window.location.hostname === "localhost") {
    console.warn("WARNING: NEXT_PUBLIC_API_BASE_URL not defined. Falling back to http://localhost:8000");
}

export interface ApiResponse<T = any> {
    success: boolean;
    data?: T;
    error?: string;
}

class ApiClient {
    private getToken(): string | null {
        return auth.getToken();
    }

    private getWorkspaceId(): string | null {
        return auth.getWorkspaceId();
    }

    async request<T = any>(
        path: string,
        options: RequestInit = {}
    ): Promise<ApiResponse<T>> {
        // If API_BASE_URL is empty, it defaults to relative paths (e.g., /api/v1/...)

        // Safe base URL with /api/v1 prefix - ALWAYS absolute
        const base = API_BASE_URL.replace(/\/$/, "");
        const cleanPath = path.startsWith("/") ? path : `/${path}`;
        const url = `${base}/api/v1${cleanPath}`;

        const method = options.method || "GET";
        console.log(`[API] ${method} ${url}`);

        const token = this.getToken();
        const workspaceId = this.getWorkspaceId();

        const headers = new Headers(options.headers || {});

        // Always inject Authorization if token exists
        if (token) {
            headers.set("Authorization", `Bearer ${token}`);
        }

        // Always inject X-Workspace-ID
        if (workspaceId) {
            headers.set("X-Workspace-ID", workspaceId);
        }

        if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
            headers.set("Content-Type", "application/json");
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers,
            });

            // Handle 401 (expired/invalid session) → logout
            if (response.status === 401) {
                if (typeof window !== "undefined") {
                    auth.logout();
                }
                return { success: false, error: "Session expired. Please login again." };
            }

            // Handle 403 (forbidden / module disabled / insufficient role) → surface error, don't logout
            if (response.status === 403) {
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.includes("application/json")) {
                    const json = await response.json();
                    return { success: false, error: json.error || json.detail || "Access denied (403)." };
                }
                return { success: false, error: "Access denied (403)." };
            }

            const contentType = response.headers.get("content-type");

            if (contentType && contentType.includes("application/json")) {
                const json = await response.json();
                if (!response.ok) {
                    return {
                        success: false,
                        error: json.error || json.detail || `API Error (${response.status})`
                    };
                }
                if (json.hasOwnProperty("success")) {
                    return json as ApiResponse<T>;
                }
                return { success: true, data: json as T };
            } else {
                const text = await response.text();
                if (!response.ok) {
                    console.error("Non-JSON Error Response:", text.substring(0, 200));
                    return {
                        success: false,
                        error: `Backend Error (${response.status}): ${text.substring(0, 50)}...`
                    };
                }
                return { success: true, data: text as any };
            }
        } catch (error: any) {
            console.error("API Connectivity Error:", error);
            return {
                success: false,
                error: `Backend unreachable (${error.message || 'Network Error'}). Check API base URL or server status.`
            };
        }
    }

    get<T = any>(path: string, options?: RequestInit) {
        return this.request<T>(path, { ...options, method: "GET" });
    }

    post<T = any>(path: string, body?: any, options?: RequestInit) {
        return this.request<T>(path, {
            ...options,
            method: "POST",
            body: body instanceof FormData ? body : JSON.stringify(body),
        });
    }

    put<T = any>(path: string, body?: any, options?: RequestInit) {
        return this.request<T>(path, {
            ...options,
            method: "PUT",
            body: body instanceof FormData ? body : JSON.stringify(body),
        });
    }

    patch<T = any>(path: string, body?: any, options?: RequestInit) {
        return this.request<T>(path, {
            ...options,
            method: "PATCH",
            body: body instanceof FormData ? body : JSON.stringify(body),
        });
    }

    delete<T = any>(path: string, options?: RequestInit) {
        return this.request<T>(path, { ...options, method: "DELETE" });
    }
}

export const apiClient = new ApiClient();

// ── Marketing Website Functions ──

export interface CatalogPlan {
    id: string;
    name: string;
    display_name: string;
    description: string | null;
    sort_order: number;
    entitlements: any[];
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

export const APP_URL = "http://localhost:3000";

export async function getPlans(): Promise<CatalogPlan[]> {
    try {
        const res = await fetch(`${API_BASE_URL}/api/v1/catalog/plans`, { next: { revalidate: 60 } });
        const json = await res.json();
        return json.success ? json.data : [];
    } catch { return []; }
}

export async function getModules(): Promise<CatalogModule[]> {
    try {
        const res = await fetch(`${API_BASE_URL}/api/v1/catalog/modules`, { next: { revalidate: 60 } });
        const json = await res.json();
        return json.success ? json.data : [];
    } catch { return []; }
}

export async function getIntegrationProviders(): Promise<CatalogProvider[]> {
    try {
        const res = await fetch(`${API_BASE_URL}/api/v1/catalog/integration-providers`, { next: { revalidate: 60 } });
        const json = await res.json();
        return json.success ? json.data : [];
    } catch { return []; }
}

export async function getPublicTemplates(category?: string): Promise<CatalogTemplate[]> {
    const params = category ? `?category=${encodeURIComponent(category)}` : "";
    try {
        const res = await fetch(`${API_BASE_URL}/api/v1/catalog/templates${params}`, { next: { revalidate: 60 } });
        const json = await res.json();
        return json.success ? json.data : [];
    } catch { return []; }
}

export interface CatalogEnum {
    key: string;
    label: string;
}

export async function getTemplateCategories(): Promise<CatalogEnum[]> {
    try {
        const res = await fetch(`${API_BASE_URL}/api/v1/catalog/template-categories`, { next: { revalidate: 60 } });
        const json = await res.json();
        return json.success ? json.data : [];
    } catch { return []; }
}

export async function getTemplatePlatforms(): Promise<CatalogEnum[]> {
    try {
        const res = await fetch(`${API_BASE_URL}/api/v1/catalog/template-platforms`, { next: { revalidate: 60 } });
        const json = await res.json();
        return json.success ? json.data : [];
    } catch { return []; }
}
