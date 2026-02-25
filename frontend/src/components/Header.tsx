import { Bell, Search, AlertCircle, Mail } from "lucide-react";
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import Link from "next/link";

export function Header() {
    const [user, setUser] = useState<any>(null);

    useEffect(() => {
        const fetchUser = async () => {
            const res = await apiClient.get("/auth/me");
            if (res.success) {
                setUser(res.data);
            }
        };
        fetchUser();
    }, []);

    return (
        <header className="flex flex-col sticky top-0 z-20">
            {/* Verification Banner */}
            {user?.requires_email_verification && (
                <div className="bg-amber-50 border-b border-amber-200 py-2.5 px-8 flex items-center justify-between text-amber-800 animate-in fade-in slide-in-from-top duration-500">
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

            <div className="h-16 bg-white border-b border-border flex items-center justify-between px-8">
                <div className="flex items-center gap-4 flex-1">
                    <div className="relative max-w-md w-full">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search anything..."
                            className="w-full bg-slate-50 border border-border rounded-md pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
                        />
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <button className="p-2 hover:bg-slate-50 rounded-full transition-colors relative">
                        <Bell className="w-5 h-5 text-slate-600" />
                        <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
                    </button>

                    <div className="h-8 w-px bg-border mx-2"></div>

                    <div className="flex items-center gap-3">
                        <div className="text-right hidden sm:block">
                            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Current Workspace</p>
                            <p className="text-sm font-bold text-slate-700">Acme Corporation</p>
                        </div>
                        <div className="w-8 h-8 rounded bg-primary text-white flex items-center justify-center font-bold text-xs shadow-sm">
                            AC
                        </div>
                    </div>
                </div>
            </div>
        </header>
    );
}
