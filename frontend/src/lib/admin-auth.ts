/**
 * Admin Auth Utility for LeadPilot Admin Portal
 * Stores the admin JWT separately from the product JWT.
 * Do NOT mix with src/lib/auth.ts (product user session).
 */

const ADMIN_TOKEN_KEY = "leadpilot_admin_token";

export interface AdminUser {
    id: string;
    email: string;
    full_name: string;
    is_superuser: boolean;
    role?: { name: string; permissions: string[] } | null;
}

export const adminAuth = {
    getToken: (): string | null => {
        if (typeof window === "undefined") return null;
        return localStorage.getItem(ADMIN_TOKEN_KEY);
    },

    setToken: (token: string): void => {
        if (typeof window === "undefined") return;
        localStorage.setItem(ADMIN_TOKEN_KEY, token);
    },

    clearToken: (): void => {
        if (typeof window === "undefined") return;
        localStorage.removeItem(ADMIN_TOKEN_KEY);
    },

    isAuthed: (): boolean => {
        return !!adminAuth.getToken();
    },

    logout: (): void => {
        adminAuth.clearToken();
        if (typeof window !== "undefined") {
            window.location.href = "/admin/login";
        }
    },
};
