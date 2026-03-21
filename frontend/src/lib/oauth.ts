/**
 * OAuth connect utility — reusable across all providers.
 * Usage: await initiateOAuth("hubspot", "/integrations")
 */
import { apiClient } from "@/lib/api";

export async function initiateOAuth(
    providerCode: string,
    redirectAfter?: string
): Promise<void> {
    const qs = redirectAfter ? `?redirect_after=${encodeURIComponent(redirectAfter)}` : "";
    const res = await apiClient.get<{ authorization_url: string }>(
        `/oauth/${providerCode}/authorize${qs}`
    );
    if (res.success && res.data?.authorization_url) {
        window.location.href = res.data.authorization_url;
    } else {
        throw new Error(res.error || `Failed to initiate ${providerCode} OAuth flow`);
    }
}

export interface OAuthConnection {
    id: string;
    workspace_id: string | null;
    user_id: string | null;
    provider_code: string;
    external_account_id: string | null;
    external_account_name: string | null;
    expires_at: string | null;
    token_type: string | null;
    scopes_json: string | null;
    status: "active" | "expired" | "revoked" | "failed";
    created_at: string;
    updated_at: string;
}

export async function listOAuthConnections(): Promise<OAuthConnection[]> {
    const res = await apiClient.get<OAuthConnection[]>("/oauth/connections");
    return res.success ? (res.data ?? []) : [];
}

export async function disconnectOAuth(connectionId: string): Promise<void> {
    await apiClient.delete(`/oauth/connections/${connectionId}`);
}

export async function refreshOAuth(connectionId: string): Promise<OAuthConnection | null> {
    const res = await apiClient.post<OAuthConnection>(
        `/oauth/connections/${connectionId}/refresh`
    );
    return res.success ? (res.data ?? null) : null;
}
