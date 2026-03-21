"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiClient } from "@/lib/api";
import { auth } from "@/lib/auth";

export default function SocialCallbackPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [status, setStatus] = useState("Authenticating...");
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const code = searchParams.get("code");
        const state = searchParams.get("state");
        const providerError = searchParams.get("error");

        // Provider reported an error
        if (providerError) {
            setError(`Authorization was denied: ${providerError}`);
            return;
        }

        if (!code || !state) {
            setError("Missing authorization code or state from provider.");
            return;
        }

        // Retrieve the provider stored before the redirect
        const provider = sessionStorage.getItem("social_auth_provider");
        if (!provider) {
            setError("Could not determine which provider to complete authentication with. Please try again.");
            return;
        }

        const handleCallback = async () => {
            try {
                const response = await apiClient.get(
                    `/auth/oauth/${provider}/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`
                );

                if (response.success && response.data?.access_token) {
                    sessionStorage.removeItem("social_auth_provider");
                    auth.setToken(response.data.access_token);

                    // Fetch workspaces and activate the first one
                    const wsRes = await apiClient.get("/workspaces");
                    if (wsRes.success && wsRes.data && wsRes.data.length > 0) {
                        auth.setWorkspaceId(wsRes.data[0].id);
                    }

                    setStatus("Authenticated! Redirecting...");
                    router.push("/dashboard");
                } else {
                    setError(response.error || "Failed to complete authentication.");
                }
            } catch (err: any) {
                setError("An unexpected error occurred during authentication.");
            }
        };

        handleCallback();
    }, [searchParams, router]);

    return (
        <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
            {!error ? (
                <>
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0F766E]"></div>
                    <p className="text-[#334155] font-medium">{status}</p>
                </>
            ) : (
                <div className="text-center space-y-4">
                    <div className="bg-red-50 text-red-700 p-4 rounded-md border border-red-200">
                        <p className="font-medium">Authentication Error</p>
                        <p className="text-sm mt-1">{error}</p>
                    </div>
                    <button
                        onClick={() => router.push("/login")}
                        className="text-[#0F766E] hover:text-[#14B8A6] font-medium text-sm"
                    >
                        Return to login
                    </button>
                </div>
            )}
        </div>
    );
}
