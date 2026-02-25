"use client";

import { useState, useEffect } from "react";
import {
    Save,
    History,
    Sparkles,
    AlertCircle,
    CheckCircle2,
    ChevronRight,
    Shield,
    Target,
    UserCircle,
    Briefcase,
    Zap,
    Loader2,
    FileText,
    Trash2,
    Plus,
    Upload
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiClient } from "@/lib/api";

export default function PromptStudioPage() {
    const [activeTab, setActiveTab] = useState("editor");
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [lastSaved, setLastSaved] = useState<string | null>(null);
    const [versionHistory, setVersionHistory] = useState<any[]>([]);
    const [knowledgeFiles, setKnowledgeFiles] = useState<any[]>([]);
    const [isUploading, setIsUploading] = useState(false);

    // Form State
    const [formData, setFormData] = useState({
        basics: {
            business_name: "",
            industry: "",
            services: [] as string[],
            supported_channels: [] as string[]
        },
        behavior: {
            assistant_role: "",
            tone: "Professional",
            primary_goal: "",
            always_do: "",
            never_do: ""
        },
        qualification: {
            required_details: [] as string[],
            max_questions_at_once: 1
        },
        escalation: {
            escalate_on_human_request: true,
            escalation_message: "I'll hand you over to a human team member who can help you further. Please wait a moment."
        },
        pricing: {
            never_invent_pricing: true,
            pricing_policy_text: "Please refer to our official website or wait for a sales representative for pricing details."
        }
    });

    const [compiledPreview, setCompiledPreview] = useState("");

    const fetchKnowledgeFiles = async () => {
        const res = await apiClient.get("/knowledge/files");
        if (res.success && res.data) {
            setKnowledgeFiles(res.data);
        }
    };

    const fetchConfig = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const res = await apiClient.get("/prompt-config");
            if (res.success && res.data) {
                const versions = res.data.versions || [];
                const activeVersion = versions[0]; // Get latest
                if (activeVersion && activeVersion.structured_data) {
                    setFormData(activeVersion.structured_data);
                    setCompiledPreview(activeVersion.compiled_system_instruction || "");
                }
                setVersionHistory(versions);
            } else {
                setError(res.error || "Failed to load prompt configuration.");
            }
            await fetchKnowledgeFiles();
        } catch (err: any) {
            setError("Connectivity error. Please check your internet or try again.");
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchConfig();
    }, []);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append("file", file);

        const res = await apiClient.post("/knowledge/files", formData);
        if (res.success) {
            await fetchKnowledgeFiles();
        } else {
            alert("Upload failed: " + res.error);
        }
        setIsUploading(false);
    };

    const handleDeleteFile = async (id: string) => {
        if (!confirm("Are you sure you want to delete this file?")) return;
        const res = await apiClient.delete(`/knowledge/files/${id}`);
        if (res.success) {
            setKnowledgeFiles(knowledgeFiles.filter(f => f.id !== id));
        }
    };

    const handleSave = async () => {
        setIsSaving(true);
        const res = await apiClient.post("/prompt-config", {
            structured_data: formData,
            temperature: 0.7,
            max_tokens_per_execution: 1000
        });

        if (res.success) {
            setLastSaved(new Date().toLocaleTimeString());
            setCompiledPreview(res.data.compiled_system_instruction);
            setVersionHistory([res.data, ...versionHistory.slice(0, 9)]);
        } else {
            alert("Error saving: " + res.error);
        }
        setIsSaving(false);
    };

    const updateNested = (section: keyof typeof formData, field: string, value: any) => {
        setFormData(prev => ({
            ...prev,
            [section]: {
                ...(prev[section] as any),
                [field]: value
            }
        }));
    };

    const toggleListItem = (section: keyof typeof formData, field: string, item: string) => {
        const currentList = (formData[section] as any)[field] as string[];
        const newList = currentList.includes(item)
            ? currentList.filter(i => i !== item)
            : [...currentList, item];
        updateNested(section, field, newList);
    };

    // Tab buttons
    const tabs = [
        { id: "editor", label: "Assistant Configuration", icon: UserCircle },
        { id: "knowledge", label: "Knowledge Base", icon: FileText },
        { id: "history", label: "Version History", icon: History }
    ];

    return (
        <div className="flex flex-col h-[calc(100vh-120px)]">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-800">Prompt Studio</h1>
                    <p className="text-slate-500 text-sm">Configure your AI's personality and business rules via structured forms.</p>
                </div>
                <div className="flex items-center gap-3">
                    {lastSaved && (
                        <span className="text-xs text-emerald-600 flex items-center gap-1 font-medium bg-emerald-50 px-2 py-1 rounded-full">
                            <CheckCircle2 className="w-3 h-3" />
                            Saved at {lastSaved}
                        </span>
                    )}
                    <button
                        onClick={handleSave}
                        disabled={isSaving}
                        className="bg-teal-700 text-white px-5 py-2.5 rounded-lg text-sm font-bold hover:bg-teal-800 transition-all flex items-center gap-2 shadow-sm disabled:opacity-50"
                    >
                        {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        Save Version
                    </button>
                </div>
            </div>

            <div className="flex-1 flex gap-6 overflow-hidden">
                {error ? (
                    <div className="flex-1 flex flex-col items-center justify-center bg-white border border-slate-200 rounded-2xl shadow-sm p-12 text-center">
                        <AlertCircle className="w-12 h-12 text-rose-500 mb-4" />
                        <h2 className="text-lg font-bold text-slate-800">Unable to load configuration</h2>
                        <p className="text-slate-500 text-sm max-w-md mt-2 mb-6">{error}</p>
                        <button
                            onClick={fetchConfig}
                            className="bg-teal-700 text-white px-6 py-2 rounded-lg font-bold hover:bg-teal-800 transition-all shadow-sm"
                        >
                            Try Again
                        </button>
                    </div>
                ) : (
                    <>
                        {/* Left Panel: Form Sections */}
                        <div className="flex-1 flex flex-col bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                            <div className="flex border-b border-slate-100 bg-slate-50/50">
                                {tabs.map(tab => (
                                    <button
                                        key={tab.id}
                                        onClick={() => setActiveTab(tab.id)}
                                        className={cn(
                                            "px-8 py-4 text-sm font-bold border-b-2 transition-all flex items-center gap-2",
                                            activeTab === tab.id ? "border-teal-600 text-teal-700 bg-white" : "border-transparent text-slate-400 hover:text-slate-600"
                                        )}
                                    >
                                        <tab.icon className="w-4 h-4" />
                                        {tab.label}
                                        {tab.id === "knowledge" && knowledgeFiles.length > 0 && (
                                            <span className="ml-2 bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded-full text-[10px]">
                                                {knowledgeFiles.length}
                                            </span>
                                        )}
                                    </button>
                                ))}
                            </div>

                            <div className="flex-1 overflow-y-auto p-8 space-y-10 custom-scrollbar">
                                {activeTab === "editor" ? (
                                    <>
                                        {/* Section 1: Business Basics */}
                                        <section className="space-y-4">
                                            <div className="flex items-center gap-2 text-slate-800 border-b pb-2 border-slate-100">
                                                <Briefcase className="w-4 h-4 text-teal-600" />
                                                <h2 className="text-sm font-bold uppercase tracking-wider">Business Basics</h2>
                                            </div>
                                            <div className="grid grid-cols-2 gap-6">
                                                <div className="space-y-1.5">
                                                    <label className="text-xs font-semibold text-slate-500">Business Name</label>
                                                    <input
                                                        type="text"
                                                        value={formData.basics.business_name}
                                                        onChange={(e) => updateNested("basics", "business_name", e.target.value)}
                                                        placeholder="e.g. LeadPilot Systems"
                                                        className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 outline-none transition-all"
                                                    />
                                                </div>
                                                <div className="space-y-1.5">
                                                    <label className="text-xs font-semibold text-slate-500">Industry</label>
                                                    <input
                                                        type="text"
                                                        value={formData.basics.industry}
                                                        onChange={(e) => updateNested("basics", "industry", e.target.value)}
                                                        placeholder="e.g. Marketing Technology"
                                                        className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 outline-none transition-all"
                                                    />
                                                </div>
                                            </div>
                                            <div className="space-y-1.5">
                                                <label className="text-xs font-semibold text-slate-500">Key Services (comma separated)</label>
                                                <input
                                                    type="text"
                                                    value={formData.basics.services.join(", ")}
                                                    onChange={(e) => updateNested("basics", "services", e.target.value.split(",").map(s => s.trim()))}
                                                    placeholder="e.g. Lead Generation, CRM, Automation"
                                                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 outline-none transition-all"
                                                />
                                            </div>
                                        </section>

                                        {/* Section 2: Assistant Behavior */}
                                        <section className="space-y-4">
                                            <div className="flex items-center gap-2 text-slate-800 border-b pb-2 border-slate-100">
                                                <UserCircle className="w-4 h-4 text-teal-600" />
                                                <h2 className="text-sm font-bold uppercase tracking-wider">Assistant Behavior</h2>
                                            </div>
                                            <div className="grid grid-cols-2 gap-6">
                                                <div className="space-y-1.5">
                                                    <label className="text-xs font-semibold text-slate-500">Assistant Role</label>
                                                    <input
                                                        type="text"
                                                        value={formData.behavior.assistant_role}
                                                        onChange={(e) => updateNested("behavior", "assistant_role", e.target.value)}
                                                        placeholder="e.g. Senior Concierge"
                                                        className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 outline-none transition-all"
                                                    />
                                                </div>
                                                <div className="space-y-1.5">
                                                    <label className="text-xs font-semibold text-slate-500">Tone</label>
                                                    <select
                                                        value={formData.behavior.tone}
                                                        onChange={(e) => updateNested("behavior", "tone", e.target.value)}
                                                        className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 outline-none transition-all"
                                                    >
                                                        <option>Professional</option>
                                                        <option>Friendly</option>
                                                        <option>Direct</option>
                                                    </select>
                                                </div>
                                            </div>
                                            <div className="space-y-1.5">
                                                <label className="text-xs font-semibold text-slate-500">Primary Goal</label>
                                                <textarea
                                                    value={formData.behavior.primary_goal}
                                                    onChange={(e) => updateNested("behavior", "primary_goal", e.target.value)}
                                                    placeholder="What should the assistant always try to achieve?"
                                                    className="w-full h-20 p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 outline-none transition-all resize-none"
                                                />
                                            </div>
                                            <div className="grid grid-cols-2 gap-6">
                                                <div className="space-y-1.5">
                                                    <label className="text-xs font-bold text-emerald-600 uppercase tracking-tighter">Always do</label>
                                                    <textarea
                                                        value={formData.behavior.always_do}
                                                        onChange={(e) => updateNested("behavior", "always_do", e.target.value)}
                                                        className="w-full h-24 p-2.5 bg-emerald-50/30 border border-emerald-100 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none transition-all resize-none"
                                                    />
                                                </div>
                                                <div className="space-y-1.5">
                                                    <label className="text-xs font-bold text-rose-600 uppercase tracking-tighter">Never do</label>
                                                    <textarea
                                                        value={formData.behavior.never_do}
                                                        onChange={(e) => updateNested("behavior", "never_do", e.target.value)}
                                                        className="w-full h-24 p-2.5 bg-rose-50/30 border border-rose-100 rounded-lg text-sm focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 outline-none transition-all resize-none"
                                                    />
                                                </div>
                                            </div>
                                        </section>

                                        {/* Section 3: Lead Qualification */}
                                        <section className="space-y-4">
                                            <div className="flex items-center gap-2 text-slate-800 border-b pb-2 border-slate-100">
                                                <Target className="w-4 h-4 text-teal-600" />
                                                <h2 className="text-sm font-bold uppercase tracking-wider">Lead Qualification</h2>
                                            </div>
                                            <div className="space-y-3">
                                                <label className="text-xs font-semibold text-slate-500">Collect the Following Details</label>
                                                <div className="flex flex-wrap gap-2">
                                                    {["Full Name", "Company Email", "Budget Range", "Current Location", "Selected Service", "Project Timeline"].map(detail => (
                                                        <button
                                                            key={detail}
                                                            onClick={() => toggleListItem("qualification", "required_details", detail)}
                                                            className={cn(
                                                                "px-4 py-1.5 rounded-full text-xs font-medium border transition-all",
                                                                formData.qualification.required_details.includes(detail)
                                                                    ? "bg-teal-600 border-teal-600 text-white shadow-sm"
                                                                    : "bg-white border-slate-200 text-slate-500 hover:border-teal-500"
                                                            )}
                                                        >
                                                            {detail}
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                            <div className="space-y-1.5">
                                                <label className="text-xs font-semibold text-slate-500">Max Questions per Message</label>
                                                <input
                                                    type="number"
                                                    min="1"
                                                    max="3"
                                                    value={formData.qualification.max_questions_at_once}
                                                    onChange={(e) => updateNested("qualification", "max_questions_at_once", parseInt(e.target.value))}
                                                    className="w-24 p-2 bg-slate-50 border border-slate-200 rounded-lg text-sm outline-none"
                                                />
                                            </div>
                                        </section>

                                        {/* Section 4: Escalation & Pricing */}
                                        <div className="grid grid-cols-2 gap-8">
                                            <section className="space-y-4">
                                                <div className="flex items-center gap-2 text-slate-800 border-b pb-2 border-slate-100">
                                                    <Zap className="w-4 h-4 text-teal-600" />
                                                    <h2 className="text-sm font-bold uppercase tracking-wider">Escalation</h2>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <input
                                                        type="checkbox"
                                                        checked={formData.escalation.escalate_on_human_request}
                                                        onChange={(e) => updateNested("escalation", "escalate_on_human_request", e.target.checked)}
                                                        className="w-4 h-4 accent-teal-600"
                                                    />
                                                    <span className="text-xs font-medium text-slate-600">Auto-escalate human requests</span>
                                                </div>
                                                <textarea
                                                    value={formData.escalation.escalation_message}
                                                    onChange={(e) => updateNested("escalation", "escalation_message", e.target.value)}
                                                    className="w-full h-20 p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs outline-none focus:border-teal-500 transition-all resize-none"
                                                />
                                            </section>
                                            <section className="space-y-4">
                                                <div className="flex items-center gap-2 text-slate-800 border-b pb-2 border-slate-100">
                                                    <Shield className="w-4 h-4 text-teal-600" />
                                                    <h2 className="text-sm font-bold uppercase tracking-wider">Pricing Guardrail</h2>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <input
                                                        type="checkbox"
                                                        checked={formData.pricing.never_invent_pricing}
                                                        onChange={(e) => updateNested("pricing", "never_invent_pricing", e.target.checked)}
                                                        className="w-4 h-4 accent-teal-600"
                                                    />
                                                    <span className="text-xs font-medium text-slate-600">Never invent pricing</span>
                                                </div>
                                                <textarea
                                                    value={formData.pricing.pricing_policy_text}
                                                    onChange={(e) => updateNested("pricing", "pricing_policy_text", e.target.value)}
                                                    className="w-full h-20 p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs outline-none focus:border-teal-500 transition-all resize-none"
                                                />
                                            </section>
                                        </div>
                                    </>
                                ) : activeTab === "knowledge" ? (
                                    <div className="space-y-6">
                                        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                                            <div>
                                                <h2 className="text-lg font-bold text-slate-800">Workspace Knowledge</h2>
                                                <p className="text-xs text-slate-500">Upload documents (PDFs, TXT, CSV) to provide AI with business context.</p>
                                            </div>
                                            <label className="cursor-pointer bg-teal-600 text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-teal-700 transition-all flex items-center gap-2 shadow-sm">
                                                {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                                                Upload File
                                                <input type="file" className="hidden" onChange={handleFileUpload} disabled={isUploading} />
                                            </label>
                                        </div>

                                        <div className="grid grid-cols-1 gap-4">
                                            {knowledgeFiles.length === 0 ? (
                                                <div className="py-20 flex flex-col items-center justify-center border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50 text-slate-400">
                                                    <Upload className="w-10 h-10 mb-4 opacity-20" />
                                                    <p className="text-sm font-medium">No files uploaded yet.</p>
                                                    <p className="text-[10px] mt-1">Upload pricing docs, FAQs, or service guides.</p>
                                                </div>
                                            ) : (
                                                knowledgeFiles.map(file => (
                                                    <div key={file.id} className="p-4 bg-white border border-slate-200 rounded-xl shadow-sm flex items-center justify-between group hover:border-teal-500 transition-all">
                                                        <div className="flex items-center gap-4">
                                                            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center text-slate-400">
                                                                <FileText className="w-5 h-5" />
                                                            </div>
                                                            <div>
                                                                <h3 className="text-sm font-bold text-slate-800">{file.filename}</h3>
                                                                <div className="flex items-center gap-3 mt-0.5 text-[10px] text-slate-400 font-medium">
                                                                    <span className="uppercase">{file.mime_type.split("/")[1]}</span>
                                                                    <span>•</span>
                                                                    <span>{(file.size_bytes / 1024).toFixed(1)} KB</span>
                                                                    <span>•</span>
                                                                    <span>{new Date(file.created_at).toLocaleDateString()}</span>
                                                                </div>
                                                            </div>
                                                        </div>
                                                        <button
                                                            onClick={() => handleDeleteFile(file.id)}
                                                            className="p-2 text-slate-300 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                                                        >
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                ))
                                            )}
                                        </div>

                                        <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 flex gap-3">
                                            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                                            <p className="text-[11px] text-amber-800 leading-normal">
                                                <strong>Pro Tip:</strong> Files like TXT and CSV are indexed automatically. For PDFs, make sure to add a summary in the "Notes" field (coming soon) or ensure they are text-searchable.
                                            </p>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        {versionHistory.map((v, i) => (
                                            <div key={v.id} className="p-5 border border-slate-200 rounded-2xl bg-white hover:border-teal-500 transition-all cursor-pointer group shadow-sm flex items-center justify-between">
                                                <div>
                                                    <div className="flex items-center gap-3">
                                                        <span className="font-bold text-slate-800">Version {v.version_number}</span>
                                                        {i === 0 && <span className="text-[10px] bg-emerald-100 text-emerald-700 font-bold px-2 py-0.5 rounded-full uppercase">Active</span>}
                                                    </div>
                                                    <p className="text-xs text-slate-500 mt-1">
                                                        Compiled instruction length: {v.compiled_system_instruction?.length || 0} chars
                                                    </p>
                                                </div>
                                                <span className="text-xs text-slate-400 font-medium">
                                                    {new Date(v.created_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Right Panel: Live Preview */}
                        <div className="w-[480px] flex flex-col bg-slate-50 border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                            <div className="px-6 py-4 bg-white border-b border-slate-100 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Sparkles className="w-4 h-4 text-teal-600" />
                                    <span className="text-sm font-bold text-slate-700 uppercase tracking-widest">Compiler Preview</span>
                                </div>
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter bg-slate-100 px-2 py-1 rounded">Read Only</span>
                            </div>
                            <div className="flex-1 overflow-y-auto p-6 space-y-4">
                                <div className="p-6 bg-white border border-slate-100 rounded-xl shadow-sm ring-1 ring-slate-900/5 min-h-64">
                                    <div className="text-sm text-slate-600 whitespace-pre-wrap leading-relaxed font-manrope">
                                        {compiledPreview || "Your compiled prompt will appear here as you fill out the form..."}
                                    </div>
                                </div>

                                <div className="bg-teal-50/50 p-4 border border-teal-100 rounded-xl flex gap-3">
                                    <AlertCircle className="w-4 h-4 text-teal-600 shrink-0" />
                                    <p className="text-[11px] text-teal-700 leading-normal">
                                        This block represents the consolidated "System Instructions" sent to Gemini.
                                        It is automatically generated by the LeadPilot Engine based on your form inputs above.
                                    </p>
                                </div>
                            </div>
                            <div className="p-4 bg-white border-t border-slate-100 flex justify-center">
                                <div className="flex items-center gap-6">
                                    <div className="flex items-center gap-1.5">
                                        <div className="w-2 h-2 rounded-full bg-teal-500 shadow-[0_0_8px_rgba(20,184,166,0.6)]"></div>
                                        <span className="text-[10px] font-bold text-slate-500 uppercase">Engine: Google Gemini</span>
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                        <div className="w-2 h-2 rounded-full bg-slate-300"></div>
                                        <span className="text-[10px] font-bold text-slate-500 uppercase">Temp: 0.7</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
