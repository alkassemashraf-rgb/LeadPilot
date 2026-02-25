"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiClient } from "@/lib/api";
import { auth } from "@/lib/auth";

export default function GoogleCallbackPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [status, setStatus] = useState("Authenticating...");
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const code = searchParams.get("code");
        const state = searchParams.get("state");

        if (!code || !state) {
            setError("Missing authorization code or state from Google.");
            return;
        }

        const handleCallback = async () => {
            try {
                const response = await apiClient.post("/auth/google/callback", {
                    code,
                    state,
                });

                if (response.success && response.data?.access_token) {
                    auth.setToken(response.data.access_token);

                    // Fetch user's workspaces and set the first one as active (Mirroring Login page)
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
                setError("An unexpected error occurred during Google authentication.");
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
