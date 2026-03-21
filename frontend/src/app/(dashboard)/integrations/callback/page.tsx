"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { CheckCircle2, XCircle, ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";

function CallbackContent() {
    const params = useSearchParams();
    const status = params.get("status");
    const provider = params.get("provider") || "provider";
    const reason = params.get("reason");
    const redirectAfter = params.get("redirect_after") || "/integrations";

    const displayName = provider.charAt(0).toUpperCase() + provider.slice(1);

    if (!status) {
        return (
            <div className="flex flex-col items-center gap-4 text-center">
                <Loader2 className="w-10 h-10 animate-spin text-white/40" />
                <p className="text-white/60">Processing…</p>
            </div>
        );
    }

    const isSuccess = status === "success";

    return (
        <div className="flex flex-col items-center gap-6 text-center max-w-md">
            {isSuccess ? (
                <CheckCircle2 className="w-16 h-16 text-emerald-400" />
            ) : (
                <XCircle className="w-16 h-16 text-red-400" />
            )}

            <div className="space-y-2">
                <h1 className="text-2xl font-semibold text-white">
                    {isSuccess
                        ? `${displayName} connected`
                        : `${displayName} connection failed`}
                </h1>
                <p className="text-white/60 text-sm">
                    {isSuccess
                        ? `Your ${displayName} account has been successfully connected.`
                        : reason
                        ? `Something went wrong: ${reason.replace(/_/g, " ")}.`
                        : "Something went wrong. Please try again."}
                </p>
            </div>

            <Link
                href={redirectAfter}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-white/10 hover:bg-white/15 border border-white/10 text-sm text-white transition-colors"
            >
                <ArrowLeft className="w-4 h-4" />
                Return to Integrations
            </Link>
        </div>
    );
}

export default function OAuthCallbackPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-[#0A0A0B]">
            <Suspense
                fallback={
                    <div className="flex flex-col items-center gap-4">
                        <Loader2 className="w-10 h-10 animate-spin text-white/40" />
                        <p className="text-white/60 text-sm">Loading…</p>
                    </div>
                }
            >
                <CallbackContent />
            </Suspense>
        </div>
    );
}
