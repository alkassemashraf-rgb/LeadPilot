"use client";

import { ShieldCheck, Mail, MoreVertical, Trash2, Edit } from "lucide-react";

const members = [
    { id: 1, name: "John Doe", email: "john@example.com", role: "Owner", status: "Active" },
    { id: 2, name: "Sarah Smith", email: "sarah@example.com", role: "Member", status: "Active" },
    { id: 3, name: "Mike Jones", email: "mike@example.com", role: "Viewer", status: "Pending" },
];

export default function TeamPage() {
    return (
        <div className="space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Team Management</h1>
                    <p className="text-slate-500">Manage your workspace members and their roles.</p>
                </div>
                <button className="bg-primary text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2 shadow-sm">
                    <Mail className="w-4 h-4" />
                    Invite Member
                </button>
            </div>

            <div className="bg-white rounded-lg border border-border shadow-sm overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-slate-50 border-b border-border">
                        <tr>
                            <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Member</th>
                            <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Role</th>
                            <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                            <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                        {members.map((member) => (
                            <tr key={member.id} className="hover:bg-slate-50 transition-colors">
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 font-bold text-xs">
                                            {member.name.split(" ").map(n => n[0]).join("")}
                                        </div>
                                        <div>
                                            <p className="text-sm font-bold text-slate-700">{member.name}</p>
                                            <p className="text-xs text-slate-500">{member.email}</p>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-2">
                                        <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
                                        <span className="text-sm text-slate-600 font-medium">{member.role}</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${member.status === "Active" ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-400"
                                        }`}>
                                        {member.status}
                                    </span>
                                </td>
                                <td className="px-6 py-4 text-right">
                                    <button className="p-1 hover:bg-slate-100 rounded text-slate-400 trasition-colors">
                                        <MoreVertical className="w-4 h-4" />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
