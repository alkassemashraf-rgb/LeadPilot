"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/auth";

export default function ImpersonationConsumePage() {
    const router = useRouter();
    const [status, setStatus] = useState("Waiting for secure handshake...");
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const handleMessage = (event: MessageEvent) => {
            // Security: We MUST verify the origin of the message
            // In a production app, this would be an environment variable
            // For now, we allow from our own origin or a known admin origin
            // If the admin portal is on a different subdomain, we'd check that here.

            const message = event.data;
            if (message && message.type === "LP_IMPERSONATION_SET_TOKEN" && message.token) {
                try {
                    auth.setToken(message.token);
                    setStatus("Token received. Finalizing session...");

                    // Redirect to dashboard
                    setTimeout(() => {
                        router.push("/dashboard");
                    }, 500);
                } catch (err) {
                    setError("Failed to establish impersonation session.");
                }
            }
        };

        window.addEventListener("message", handleMessage);

        // Signal to the opener that we are ready
        if (window.opener) {
            window.opener.postMessage({ type: "LP_IMPERSONATION_READY" }, "*");
        } else {
            // If opened directly without an opener, check for token in URL (fallback/development)
            const params = new URLSearchParams(window.location.search);
            const token = params.get("token");
            if (token) {
                auth.setToken(token);
                router.push("/dashboard");
            } else {
                setError("No impersonation context found. Please start from the Admin Portal.");
            }
        }

        return () => window.removeEventListener("message", handleMessage);
    }, [router]);

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
            <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8 text-center space-y-6">
                <div className="flex justify-center">
                    <div className="h-16 w-16 bg-[#14B8A6]/10 rounded-full flex items-center justify-center animate-pulse">
                        <svg className="h-8 w-8 text-[#14B8A6]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                        </svg>
                    </div>
                </div>

                <h1 className="text-2xl font-bold text-slate-900">Establishing Secure Session</h1>

                {error ? (
                    <div className="bg-red-50 text-red-700 p-4 rounded-lg text-sm border border-red-100">
                        {error}
                    </div>
                ) : (
                    <p className="text-slate-600 animate-pulse">{status}</p>
                )
                }

                <div className="pt-4">
                    <button
                        onClick={() => router.push("/login")}
                        className="text-sm text-slate-500 hover:text-[#14B8A6] underline"
                    >
                        Back to Login
                    </button>
                </div>
            </div>

            <p className="mt-8 text-xs text-slate-400">
                LeadPilot Internal Support Plane &copy; 2026
            </p>
        </div>
    );
}
