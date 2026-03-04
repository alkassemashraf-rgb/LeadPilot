"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/auth";
import { AppShell } from "@/components/AppShell";
import { DashboardThemeProvider } from "@/components/ThemeProvider";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const router = useRouter();
    const [isChecking, setIsChecking] = useState(true);

    useEffect(() => {
        if (!auth.isAuthed()) {
            router.push("/login");
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
        <DashboardThemeProvider>
            <AppShell>{children}</AppShell>
        </DashboardThemeProvider>
    );
}
