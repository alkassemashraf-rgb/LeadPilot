"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import {
    Landmark, Building2, Users, Plus, Loader2, AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { auth } from "@/lib/auth";

export default function AgencyConsolePage() {
    const [agency, setAgency] = useState<any>(null);
    const [members, setMembers] = useState<any[]>([]);
    const [workspaces, setWorkspaces] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState(false);
    const [newWsName, setNewWsName] = useState("");
    const [showCreate, setShowCreate] = useState(false);

    const load = async () => {
        setLoading(true);
        const agencyRes = await apiClient.get("/agency/me");
        if (agencyRes.success && agencyRes.data) {
            setAgency(agencyRes.data);
            // Load members and workspaces
            const [memRes, wsRes] = await Promise.all([
                apiClient.get("/agency/members"),
                apiClient.get("/agency/workspaces"),
            ]);
            if (memRes.success && memRes.data) setMembers(memRes.data.items || []);
            if (wsRes.success && wsRes.data) setWorkspaces(wsRes.data.items || []);
        }
        setLoading(false);
    };

    useEffect(() => { load(); }, []);

    const handleCreateWorkspace = async () => {
        if (!newWsName.trim()) return;
        setCreating(true);
        const res = await apiClient.post("/agency/workspaces", { name: newWsName.trim() });
        if (res.success) {
            setNewWsName("");
            setShowCreate(false);
            await load();
        }
        setCreating(false);
    };

    const handleSwitchToWorkspace = (wsId: string) => {
        auth.setWorkspaceId(wsId);
        window.location.href = "/dashboard";
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-64 gap-4">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
                <p className="text-sm text-slate-500">Loading agency...</p>
            </div>
        );
    }

    if (!agency) {
        return (
            <div className="max-w-lg mx-auto mt-20 text-center space-y-4">
                <Landmark className="w-12 h-12 text-slate-300 mx-auto" />
                <h2 className="text-xl font-bold text-slate-700">No Agency Account</h2>
                <p className="text-slate-500 text-sm">
                    You are not part of an agency. Create one to manage multiple client workspaces.
                </p>
                <CreateAgencyForm onCreated={load} />
            </div>
        );
    }

    const atLimit = agency.max_workspaces !== null && agency.workspace_count >= agency.max_workspaces;

    return (
        <div className="space-y-6">
            {/* Agency Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-3">
                        <Landmark className="w-6 h-6 text-primary" />
                        {agency.name}
                    </h1>
                    <p className="text-slate-500 text-sm mt-1">
                        {agency.workspace_count} workspace{agency.workspace_count !== 1 ? "s" : ""}
                        {agency.max_workspaces !== null && ` / ${agency.max_workspaces} max`}
                        {" \u00b7 "}
                        {agency.member_count} member{agency.member_count !== 1 ? "s" : ""}
                        {" \u00b7 "}
                        Role: <span className="font-medium capitalize">{agency.my_role?.replace("agency_", "")}</span>
                    </p>
                </div>
                {(agency.my_role === "agency_owner" || agency.my_role === "agency_admin") && (
                    <button
                        onClick={() => setShowCreate(true)}
                        disabled={atLimit}
                        className={cn(
                            "flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
                            atLimit
                                ? "bg-slate-100 text-slate-400 cursor-not-allowed"
                                : "bg-primary text-white hover:bg-primary/90"
                        )}
                    >
                        <Plus className="w-4 h-4" />
                        New Workspace
                    </button>
                )}
            </div>

            {atLimit && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-3">
                    <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5" />
                    <p className="text-sm text-amber-800">
                        You have reached the workspace limit ({agency.max_workspaces}) for your plan. Upgrade to create more workspaces.
                    </p>
                </div>
            )}

            {/* Create workspace modal */}
            {showCreate && (
                <div className="bg-white border border-border rounded-lg p-5 space-y-3">
                    <h3 className="font-semibold text-slate-700">Create Client Workspace</h3>
                    <input
                        type="text"
                        placeholder="Workspace name..."
                        value={newWsName}
                        onChange={(e) => setNewWsName(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleCreateWorkspace()}
                        className="w-full border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <div className="flex gap-2">
                        <button
                            onClick={handleCreateWorkspace}
                            disabled={creating || !newWsName.trim()}
                            className="px-4 py-2 bg-primary text-white text-sm rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
                        >
                            {creating ? "Creating..." : "Create"}
                        </button>
                        <button
                            onClick={() => { setShowCreate(false); setNewWsName(""); }}
                            className="px-4 py-2 bg-slate-100 text-slate-600 text-sm rounded-md hover:bg-slate-200 transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {/* Workspaces Grid */}
            <section>
                <h2 className="text-lg font-semibold text-slate-700 flex items-center gap-2 mb-4">
                    <Building2 className="w-5 h-5 text-primary" />
                    Client Workspaces
                </h2>
                {workspaces.length === 0 ? (
                    <div className="text-center py-12 text-slate-400 text-sm">No workspaces yet. Create one above.</div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {workspaces.map((ws) => (
                            <div
                                key={ws.id}
                                className="bg-white border border-border rounded-xl p-5 hover:border-primary/30 transition-colors cursor-pointer"
                                onClick={() => handleSwitchToWorkspace(ws.id)}
                            >
                                <div className="flex items-center gap-3 mb-3">
                                    <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-bold text-sm">
                                        {ws.name.split(" ").map((w: string) => w[0]).join("").toUpperCase().slice(0, 2)}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="font-semibold text-slate-700 truncate">{ws.name}</p>
                                        <p className="text-[10px] text-slate-400 capitalize">{ws.subscription_tier || "free"}</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4 text-xs text-slate-500">
                                    <span>{ws.member_count} member{ws.member_count !== 1 ? "s" : ""}</span>
                                    <span>{ws.created_at ? new Date(ws.created_at).toLocaleDateString() : ""}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* Members */}
            <section>
                <h2 className="text-lg font-semibold text-slate-700 flex items-center gap-2 mb-4">
                    <Users className="w-5 h-5 text-primary" />
                    Agency Members
                </h2>
                <div className="bg-white border border-border rounded-xl overflow-hidden">
                    {members.length === 0 ? (
                        <div className="p-6 text-center text-slate-400 text-sm">No members.</div>
                    ) : (
                        <table className="w-full text-left text-sm">
                            <thead className="bg-slate-50 text-slate-500 font-medium">
                                <tr>
                                    <th className="px-5 py-3">Name</th>
                                    <th className="px-5 py-3">Email</th>
                                    <th className="px-5 py-3">Role</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 text-slate-600">
                                {members.map((m) => (
                                    <tr key={m.id} className="hover:bg-slate-50/50 transition-colors">
                                        <td className="px-5 py-3 font-medium text-slate-700">{m.full_name || "—"}</td>
                                        <td className="px-5 py-3">{m.email}</td>
                                        <td className="px-5 py-3">
                                            <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded capitalize">
                                                {m.role?.replace("agency_", "")}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </section>
        </div>
    );
}

// Inline sub-component for creating an agency when none exists
function CreateAgencyForm({ onCreated }: { onCreated: () => void }) {
    const [name, setName] = useState("");
    const [creating, setCreating] = useState(false);

    const handleCreate = async () => {
        if (!name.trim()) return;
        setCreating(true);
        const res = await apiClient.post("/agency/create", { name: name.trim() });
        if (res.success) {
            onCreated();
        }
        setCreating(false);
    };

    return (
        <div className="space-y-3 mt-4">
            <input
                type="text"
                placeholder="Agency name..."
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                className="w-full border border-border rounded-md px-3 py-2 text-sm text-center focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <button
                onClick={handleCreate}
                disabled={creating || !name.trim()}
                className="px-6 py-2.5 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
                {creating ? "Creating..." : "Create Agency"}
            </button>
        </div>
    );
}
