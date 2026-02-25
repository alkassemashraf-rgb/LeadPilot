"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { adminAuth } from "@/lib/admin-auth";
import { adminApi } from "@/lib/admin-api";
import { AdminSidebar } from "@/components/AdminSidebar";

interface AdminUserCtx {
    id: string;
    email: string;
    full_name: string;
    is_superuser: boolean;
}

const AdminContext = createContext<AdminUserCtx | null>(null);
export const useAdminUser = () => useContext(AdminContext);

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const [status, setStatus] = useState<"checking" | "authorized" | "denied">("checking");
    const [adminUser, setAdminUser] = useState<AdminUserCtx | null>(null);

    useEffect(() => {
        // Login page is always accessible — don't redirect-loop
        if (pathname === "/admin/login") {
            setStatus("authorized");
            return;
        }

        if (!adminAuth.isAuthed()) {
            router.push("/admin/login");
            return;
        }

        adminApi.me().then((res) => {
            if (res.success && res.data) {
                setAdminUser(res.data);
                setStatus("authorized");
            } else {
                adminAuth.clearToken();
                router.push("/admin/login");
            }
        });
    }, [router, pathname]);

    if (status === "checking") {
        return (
            <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="animate-spin rounded-full h-8 w-8 border-2 border-violet-500/20 border-t-violet-500" />
                    <p className="text-sm text-slate-500">Verifying admin access…</p>
                </div>
            </div>
        );
    }

    // Login page renders without sidebar
    if (pathname === "/admin/login") {
        return <>{children}</>;
    }

    return (
        <AdminContext.Provider value={adminUser}>
            <div className="min-h-screen bg-[#0F172A]">
                <AdminSidebar adminUser={adminUser} />
                <div className="pl-64 flex flex-col min-h-screen">
                    <main className="flex-1 p-8 overflow-y-auto">
                        <div className="max-w-5xl mx-auto">
                            {children}
                        </div>
                    </main>
                </div>
            </div>
        </AdminContext.Provider>
    );
}
