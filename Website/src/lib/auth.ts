/**
 * Auth Utility for LeadPilot
 * Handles secure storage and retrieval of authentication tokens and active workspace IDs.
 */

const TOKEN_KEY = "leadpilot_auth_token";
const WORKSPACE_KEY = "leadpilot_active_workspace";

export const auth = {
    getToken: (): string | null => {
        if (typeof window === "undefined") return null;
        return localStorage.getItem(TOKEN_KEY);
    },

    setToken: (token: string): void => {
        if (typeof window === "undefined") return;
        localStorage.setItem(TOKEN_KEY, token);
    },

    clearToken: (): void => {
        if (typeof window === "undefined") return;
        localStorage.removeItem(TOKEN_KEY);
    },

    getWorkspaceId: (): string | null => {
        if (typeof window === "undefined") return null;
        return localStorage.getItem(WORKSPACE_KEY);
    },

    setWorkspaceId: (id: string): void => {
        if (typeof window === "undefined") return;
        localStorage.setItem(WORKSPACE_KEY, id);
    },

    isAuthed: (): boolean => {
        return !!auth.getToken();
    },

    logout: (): void => {
        auth.clearToken();
        if (typeof window !== "undefined") {
            localStorage.removeItem(WORKSPACE_KEY);
            window.location.href = "/login";
        }
    },

    getDecodedToken: (): any | null => {
        const token = auth.getToken();
        if (!token) return null;
        try {
            const base64Url = token.split(".")[1];
            const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
            const jsonPayload = decodeURIComponent(
                atob(base64)
                    .split("")
                    .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
                    .join("")
            );
            return JSON.parse(jsonPayload);
        } catch (e) {
            return null;
        }
    },

    isImpersonating: (): boolean => {
        const decoded = auth.getDecodedToken();
        return !!decoded?.impersonated_by_admin_id;
    },
};
