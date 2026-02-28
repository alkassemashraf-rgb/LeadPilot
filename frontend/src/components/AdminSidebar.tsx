"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard,
    Users,
    Building2,
    Activity,
    ToggleLeft,
    ScrollText,
    LogOut,
    Shield,
    Mail,
    Send,
    Zap,
    FileText,
    Database,
    CreditCard,
    Landmark,
    SlidersHorizontal,
    LayoutTemplate,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { adminAuth } from "@/lib/admin-auth";

const adminNavItems = [
    { name: "Overview",      href: "/admin",               icon: LayoutDashboard, exact: true },
    { name: "Users",         href: "/admin/users",         icon: Users },
    { name: "Workspaces",    href: "/admin/workspaces",    icon: Building2 },
    { name: "Agencies",      href: "/admin/agencies",      icon: Landmark },
    { name: "Plans",         href: "/admin/plans",         icon: CreditCard },
    { name: "Modules",       href: "/admin/modules",       icon: ToggleLeft },
    { name: "System Settings",href: "/admin/system-settings",icon: SlidersHorizontal },
    { name: "Email Logs",    href: "/admin/email-logs",    icon: Mail },
    { name: "Dispatch",      href: "/admin/dispatch",      icon: Send },
    { name: "Automations",   href: "/admin/automations",   icon: Zap },
    { name: "Templates",     href: "/admin/templates",     icon: LayoutTemplate },
    { name: "Prompt Configs",href: "/admin/prompt-configs",icon: FileText },
    { name: "Zoho Health",   href: "/admin/zoho-health",   icon: Database },
    { name: "Monitoring",    href: "/admin/monitoring",    icon: Activity },
    { name: "Audit Log",     href: "/admin/audit-log",     icon: ScrollText },
    { name: "Runtime Events",href: "/admin/runtime-events",icon: Activity },
];

interface AdminSidebarProps {
    adminUser?: { email: string; full_name: string; is_superuser: boolean } | null;
}

export function AdminSidebar({ adminUser }: AdminSidebarProps) {
    const pathname = usePathname();

    const displayName = adminUser?.full_name || "Admin";
    const displayEmail = adminUser?.email || "";
    const initials = displayName
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2) || "SA";

    return (
        <div className="fixed inset-y-0 left-0 w-64 bg-[#0F172A] flex flex-col border-r border-white/5">
            {/* Logo */}
            <div className="h-16 flex items-center px-6 border-b border-white/10">
                <Shield className="w-5 h-5 text-violet-400 mr-2 flex-shrink-0" />
                <div>
                    <span className="text-white font-bold text-sm tracking-tight">LeadPilot</span>
                    <span className="ml-2 text-[10px] font-semibold uppercase tracking-widest text-violet-400 bg-violet-500/10 px-1.5 py-0.5 rounded">
                        Admin
                    </span>
                </div>
            </div>

            <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 px-3 mb-3">
                    Admin Console
                </p>
                {adminNavItems.map((item) => {
                    const isActive = item.exact
                        ? pathname === item.href
                        : pathname.startsWith(item.href);
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm font-medium",
                                isActive
                                    ? "bg-violet-600/20 text-violet-300 border border-violet-500/20"
                                    : "text-slate-400 hover:bg-white/5 hover:text-white"
                            )}
                        >
                            <item.icon className="w-4 h-4 flex-shrink-0" />
                            {item.name}
                        </Link>
                    );
                })}
            </nav>

            <div className="p-4 border-t border-white/10">
                <div className="flex items-center gap-3 px-2 py-2">
                    <div className="w-7 h-7 rounded-full bg-violet-600/30 flex items-center justify-center text-violet-300 text-xs font-bold flex-shrink-0">
                        {initials}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-white truncate">{displayName}</p>
                        <p className="text-[10px] text-slate-500 truncate">{displayEmail}</p>
                    </div>
                    <button
                        onClick={() => adminAuth.logout()}
                        className="p-1.5 rounded-md text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                        title="Log out"
                    >
                        <LogOut className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>
        </div>
    );
}
