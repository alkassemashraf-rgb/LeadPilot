"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
    LayoutDashboard,
    Users,
    Zap,
    Sparkles,
    Plug,
    FileText,
    Settings,
    ShieldCheck,
    MessageSquare,
    LogOut,
    SendHorizontal,
    Inbox,
    Landmark,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiClient } from "@/lib/api";

const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Inbox", href: "/inbox", icon: Inbox },
    { name: "Contacts", href: "/contacts", icon: Users },
    { name: "Automations", href: "/automations", icon: Zap },
    { name: "Outbound Queue", href: "/dispatch", icon: SendHorizontal },
    { name: "Prompt Studio", href: "/prompt-studio", icon: Sparkles },
    { name: "Test Chat", href: "/test-chat", icon: MessageSquare },
    { name: "Integrations", href: "/integrations", icon: Plug },
    { name: "Logs", href: "/logs", icon: FileText },
    { name: "Settings", href: "/settings", icon: Settings },
    { name: "Team", href: "/team", icon: ShieldCheck },
    { name: "Agency", href: "/agency", icon: Landmark },
];

function getInitials(name: string | null): string {
    if (!name) return "?";
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return parts[0].substring(0, 2).toUpperCase();
}

export function Sidebar() {
    const pathname = usePathname();
    const [userName, setUserName] = useState<string | null>(null);

    useEffect(() => {
        apiClient.get("/auth/me").then((res) => {
            if (res.success && res.data) {
                setUserName(res.data.full_name || res.data.email);
            }
        });
    }, []);

    const handleLogout = () => {
        const { auth } = require("@/lib/auth");
        auth.logout();
    };

    return (
        <div className="fixed inset-y-0 left-0 w-64 bg-white border-r border-border flex flex-col">
            <div className="h-16 flex items-center px-6 border-bottom border-border">
                <span className="text-primary font-bold text-xl tracking-tight">LeadPilot</span>
            </div>

            <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
                {navItems.map((item) => {
                    const isActive = pathname.startsWith(item.href);
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm font-medium",
                                isActive
                                    ? "bg-primary/10 text-primary"
                                    : "text-foreground hover:bg-background hover:text-primary"
                            )}
                        >
                            <item.icon className="w-4 h-4" />
                            {item.name}
                        </Link>
                    );
                })}
            </nav>

            <div className="p-4 border-t border-border">
                <div className="flex items-center gap-3 px-3 py-2">
                    <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 text-xs font-bold">
                        {getInitials(userName)}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold truncate">{userName || "Loading..."}</p>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="p-1.5 rounded-md text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                        title="Log out"
                    >
                        <LogOut className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </div>
    );
}
