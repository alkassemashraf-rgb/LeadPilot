"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/auth";

export default function AuthLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const router = useRouter();
    const [isChecking, setIsChecking] = useState(true);

    useEffect(() => {
        if (auth.isAuthed()) {
            router.push("/dashboard");
        } else {
            setIsChecking(false);
        }
    }, [router]);

    if (isChecking) {
        return (
            <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0F766E]"></div>
            </div>
        );
    }

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
                <div className="bg-white py-8 px-4 shadow-sm border border-[#E2E8F0] sm:rounded-lg sm:px-10">
                    {children}
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
