"use client";

import React, { useEffect, useState } from "react";
import { auth } from "@/lib/auth";
import { ShieldAlert, LogOut } from "lucide-react";

export function ImpersonationBanner() {
    const [isImpersonating, setIsImpersonating] = useState(false);
    const [adminName, setAdminName] = useState<string | null>(null);

    useEffect(() => {
        const checkImpersonation = () => {
            const impersonating = auth.isImpersonating();
            setIsImpersonating(impersonating);

            if (impersonating) {
                const decoded = auth.getDecodedToken();
                // We'd need to fetch admin name or pass it in token if we want it here
                // For now, just show ID or generic message
                setAdminName(decoded.impersonated_by_admin_id);
            }
        };

        checkImpersonation();
        // Check periodically or on focus
        window.addEventListener("focus", checkImpersonation);
        return () => window.removeEventListener("focus", checkImpersonation);
    }, []);

    if (!isImpersonating) return null;

    const handleStop = () => {
        auth.logout(); // Simple way to stop: logout and let them re-login as themselves
        // In a more advanced flow, we'd clear just the token and redirect to admin
    };

    return (
        <div className="bg-amber-600 text-white px-4 py-2 flex items-center justify-between sticky top-0 z-[100] shadow-md">
            <div className="flex items-center gap-3">
                <ShieldAlert className="h-5 w-5 animate-pulse" />
                <span className="text-sm font-medium">
                    <strong className="uppercase mr-2">Impersonation Mode:</strong>
                    You are currently viewing this workspace as a user for support purposes.
                </span>
            </div>

            <button
                onClick={handleStop}
                className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-3 py-1 rounded text-xs font-semibold transition-colors border border-white/20"
            >
                <LogOut className="h-3 w-3" />
                Stop Impersonating
            </button>
        </div>
    );
}
