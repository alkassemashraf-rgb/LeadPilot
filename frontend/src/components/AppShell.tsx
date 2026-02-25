"use client";

import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { ImpersonationBanner } from "./ImpersonationBanner";

export function AppShell({ children }: { children: React.ReactNode }) {
    return (
        <div className="min-h-screen bg-background">
            <ImpersonationBanner />
            <Sidebar />
            <div className="pl-64 flex flex-col min-h-screen">
                <Header />
                <main className="flex-1 p-8 overflow-y-auto">
                    <div className="max-w-7xl mx-auto">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
}
