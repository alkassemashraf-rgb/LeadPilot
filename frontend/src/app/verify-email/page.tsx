"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { apiClient } from "@/lib/api";
import { auth } from "@/lib/auth";

function VerifyEmailContent() {
    const searchParams = useSearchParams();
    const token = searchParams.get("token");

    const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
    const [message, setMessage] = useState("");

    useEffect(() => {
        if (!token) {
            setStatus("error");
            setMessage("Invalid verification link. No token provided.");
            return;
        }

        const verify = async () => {
            const res = await apiClient.get(`/auth/verify-email?token=${token}`);
            if (res.success && res.data) {
                setStatus("success");
                setMessage(res.data.message || "Email verified successfully!");
            } else {
                setStatus("error");
                setMessage(res.error || "Verification failed. The link may be invalid or expired.");
            }
        };

        verify();
    }, [token]);

    return (
        <div className="min-h-screen bg-[#F8FAFC] flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-inter">
            <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
                <Link href="/" className="inline-block">
                    <h1 className="text-3xl font-bold tracking-tight text-[#334155]">
                        Lead<span className="text-[#0F766E]">Pilot</span>
                    </h1>
                </Link>
                <p className="mt-2 text-sm text-[#64748B]">
                    Automate your lead engagement with precision.
                </p>
            </div>

            <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
                <div className="bg-white py-8 px-4 shadow-sm border border-[#E2E8F0] sm:rounded-lg sm:px-10 text-center">
                    {status === "loading" && (
                        <div className="space-y-4">
                            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#0F766E] mx-auto"></div>
                            <p className="text-sm text-[#64748B]">Verifying your email...</p>
                        </div>
                    )}

                    {status === "success" && (
                        <div className="space-y-4">
                            <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mx-auto">
                                <svg className="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                            <h2 className="text-xl font-semibold text-[#334155]">Email Verified</h2>
                            <p className="text-sm text-[#64748B]">{message}</p>
                            <Link
                                href={auth.isAuthed() ? "/dashboard" : "/login"}
                                className="inline-block mt-4 px-6 py-2 bg-[#0F766E] text-white rounded-md text-sm font-medium hover:bg-[#14B8A6] transition-colors"
                            >
                                {auth.isAuthed() ? "Go to Dashboard" : "Sign In"}
                            </Link>
                        </div>
                    )}

                    {status === "error" && (
                        <div className="space-y-4">
                            <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto">
                                <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </div>
                            <h2 className="text-xl font-semibold text-[#334155]">Verification Failed</h2>
                            <p className="text-sm text-[#64748B]">{message}</p>
                            <div className="flex flex-col gap-2 mt-4">
                                <Link
                                    href="/login"
                                    className="inline-block px-6 py-2 bg-[#0F766E] text-white rounded-md text-sm font-medium hover:bg-[#14B8A6] transition-colors"
                                >
                                    Go to Login
                                </Link>
                            </div>
                        </div>
                    )}
                </div>

                <div className="mt-6 text-center">
                    <p className="text-xs text-[#94A3B8]">
                        &copy; {new Date().getFullYear()} LeadPilot. All rights reserved.
                    </p>
                </div>
            </div>
        </div>
    );
}

export default function VerifyEmailPage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0F766E]"></div>
                </div>
            }
        >
            <VerifyEmailContent />
        </Suspense>
    );
}
