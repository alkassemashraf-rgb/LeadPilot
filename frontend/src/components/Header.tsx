import { Bell, Search, AlertCircle, Mail, ChevronDown } from "lucide-react";
import { useEffect, useState, useRef } from "react";
import { apiClient } from "@/lib/api";
import { auth } from "@/lib/auth";
import Link from "next/link";

import { ThemeToggle } from "./ThemeToggle";

export function Header() {
    const [user, setUser] = useState<any>(null);
    const [workspaces, setWorkspaces] = useState<any[]>([]);
    const [activeWs, setActiveWs] = useState<any>(null);
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const fetchData = async () => {
            const [userRes, wsRes] = await Promise.all([
                apiClient.get("/auth/me"),
                apiClient.get("/workspaces"),
            ]);
            if (userRes.success) setUser(userRes.data);
            if (wsRes.success && wsRes.data) {
                const wsList = Array.isArray(wsRes.data) ? wsRes.data : [];
                setWorkspaces(wsList);
                const currentWsId = auth.getWorkspaceId();
                const current = wsList.find((w: any) => String(w.id) === currentWsId);
                setActiveWs(current || wsList[0] || null);
                // Auto-set workspace ID if not set
                if (!currentWsId && wsList.length > 0) {
                    auth.setWorkspaceId(String(wsList[0].id));
                }
            }
        };
        fetchData();
    }, []);

    // Close dropdown on outside click
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setDropdownOpen(false);
            }
        };
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

    const handleSwitch = (ws: any) => {
        auth.setWorkspaceId(String(ws.id));
        setActiveWs(ws);
        setDropdownOpen(false);
        window.location.reload();
    };

    const wsInitials = (name: string) =>
        name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2) || "WS";

    return (
        <header className="flex flex-col sticky top-0 z-20">
            {/* Verification Banner */}
            {user?.requires_email_verification && (
                <div className="bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-900/50 py-2.5 px-8 flex items-center justify-between text-amber-800 dark:text-amber-400 animate-in fade-in slide-in-from-top duration-500">
                    <div className="flex items-center gap-2 text-sm font-medium">
                        <AlertCircle className="w-4 h-4 text-amber-600" />
                        <span>Please verify your email address. You have <strong>{user.verification_grace_remaining_days} days</strong> remaining in your grace period.</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <button
                            onClick={async () => {
                                await apiClient.post("/auth/resend-verification", { email: user.email });
                                alert("Verification email resent!");
                            }}
                            className="text-xs font-bold uppercase tracking-wider text-amber-700 hover:text-amber-900 flex items-center gap-1.5 transition-colors"
                        >
                            <Mail className="w-3.5 h-3.5" />
                            Resend Email
                        </button>
                    </div>
                </div>
            )}

            <div className="h-16 bg-white dark:bg-card border-b border-border flex items-center justify-between px-8 transition-colors">
                <div className="flex items-center gap-4 flex-1">
                    <div className="relative max-w-md w-full">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search anything..."
                            className="w-full bg-slate-50 dark:bg-slate-900/50 border border-border rounded-md pl-10 pr-4 py-2 text-sm text-foreground dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
                        />
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <button className="p-2 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-full transition-colors relative">
                        <Bell className="w-5 h-5 text-slate-600 dark:text-slate-400" />
                        <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
                    </button>

                    <div className="h-8 w-px bg-border mx-2"></div>

                    {/* Theme Toggle - Currently locked out until dark mode UI is fully stable */}
                    {/* <ThemeToggle /> */}

                    {/* <div className="h-8 w-px bg-border mx-2"></div> */}

                    {/* Workspace Switcher */}
                    <div className="relative" ref={dropdownRef}>
                        <button
                            onClick={() => setDropdownOpen(!dropdownOpen)}
                            className="flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg px-2 py-1.5 transition-colors"
                        >
                            <div className="text-right hidden sm:block">
                                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Workspace</p>
                                <p className="text-sm font-bold text-slate-700 dark:text-slate-200 max-w-[160px] truncate">
                                    {activeWs?.name || "Select Workspace"}
                                </p>
                            </div>
                            <div className="w-8 h-8 rounded bg-primary text-white flex items-center justify-center font-bold text-xs shadow-sm">
                                {activeWs ? wsInitials(activeWs.name) : "—"}
                            </div>
                            {workspaces.length > 1 && (
                                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                            )}
                        </button>

                        {dropdownOpen && workspaces.length > 1 && (
                            <div className="absolute right-0 top-full mt-2 w-64 bg-white dark:bg-card border border-border rounded-lg shadow-lg dark:shadow-black/50 z-50 py-1 transition-colors">
                                <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-widest text-slate-400">
                                    Switch Workspace
                                </p>
                                {workspaces.map((ws) => (
                                    <button
                                        key={ws.id}
                                        onClick={() => handleSwitch(ws)}
                                        className={`w-full text-left px-3 py-2.5 flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors ${String(ws.id) === String(activeWs?.id) ? "bg-primary/5 dark:bg-primary/20" : ""
                                            }`}
                                    >
                                        <div className="w-7 h-7 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300 flex items-center justify-center font-bold text-[10px] transition-colors">
                                            {wsInitials(ws.name)}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-slate-700 dark:text-slate-200 truncate">{ws.name}</p>
                                            <p className="text-[10px] text-slate-400 capitalize">{ws.subscription_tier || "free"}</p>
                                        </div>
                                        {String(ws.id) === String(activeWs?.id) && (
                                            <div className="w-2 h-2 rounded-full bg-primary"></div>
                                        )}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </header>
    );
}
