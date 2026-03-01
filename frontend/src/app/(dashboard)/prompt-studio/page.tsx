"use client";

import { useState, useEffect } from "react";
import {
    Save,
    History,
    Sparkles,
    AlertCircle,
    CheckCircle2,
    Shield,
    Target,
    UserCircle,
    Briefcase,
    Zap,
    Loader2,
    FileText,
    Trash2,
    Plus,
    Upload,
    Download,
    ArrowUp,
    ArrowDown,
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

    // Qualification state
    const [qualQuestions, setQualQuestions] = useState<any[]>([]);
    const [qualStatuses, setQualStatuses] = useState<any[]>([]);
    const [qualVersion, setQualVersion] = useState(1);
    const [isSavingQual, setIsSavingQual] = useState(false);

    // Qualification criteria state (Mission 29)
    const [criteria, setCriteria] = useState<any[]>([]);
    const [savingCriterionId, setSavingCriterionId] = useState<string | null>(null);

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

    const fetchQualificationConfig = async () => {
        const res = await apiClient.get("/qualification-config");
        if (res.success && res.data) {
            setQualQuestions(res.data.qualification_questions || []);
            setQualStatuses(res.data.qualification_statuses || []);
            setQualVersion(res.data.version || 1);
        }
    };

    const fetchCriteria = async () => {
        const res = await apiClient.get("/prompt-studio/qualification");
        if (res.success && res.data) {
            setCriteria(res.data);
        }
    };

    const handleCreateCriterion = async () => {
        setSavingCriterionId("new");
        const res = await apiClient.post("/prompt-studio/qualification", {
            label: "New Criterion",
            criterion_type: "boolean",
            sort_order: criteria.length,
        });
        if (res.success && res.data) {
            setCriteria([...criteria, res.data]);
        }
        setSavingCriterionId(null);
    };

    const handleUpdateCriterion = async (id: string, updates: Record<string, any>) => {
        setSavingCriterionId(id);
        const res = await apiClient.patch(`/prompt-studio/qualification/${id}`, updates);
        if (res.success && res.data) {
            setCriteria(criteria.map(c => c.id === id ? res.data : c));
        }
        setSavingCriterionId(null);
    };

    const handleDeleteCriterion = async (id: string) => {
        if (!confirm("Delete this qualification criterion?")) return;
        const res = await apiClient.delete(`/prompt-studio/qualification/${id}`);
        if (res.success) {
            setCriteria(criteria.filter(c => c.id !== id));
        }
    };

    const handleSaveQualification = async () => {
        setIsSavingQual(true);
        const res = await apiClient.post("/qualification-config", {
            qualification_questions: qualQuestions,
            qualification_statuses: qualStatuses,
        });
        if (res.success && res.data) {
            setQualVersion(res.data.version || qualVersion + 1);
        } else {
            alert("Error saving qualification config: " + res.error);
        }
        setIsSavingQual(false);
    };

    const addQuestion = () => {
        setQualQuestions([
            ...qualQuestions,
            { label: "", enabled: true, order: qualQuestions.length },
        ]);
    };

    const removeQuestion = (index: number) => {
        setQualQuestions(qualQuestions.filter((_, i) => i !== index));
    };

    const updateQuestion = (index: number, field: string, value: any) => {
        setQualQuestions(qualQuestions.map((q, i) => i === index ? { ...q, [field]: value } : q));
    };

    const moveQuestion = (index: number, direction: "up" | "down") => {
        const target = direction === "up" ? index - 1 : index + 1;
        if (target < 0 || target >= qualQuestions.length) return;
        const next = [...qualQuestions];
        [next[index], next[target]] = [next[target], next[index]];
        next.forEach((q, i) => (q.order = i));
        setQualQuestions(next);
    };

    const addStatus = () => {
        setQualStatuses([
            ...qualStatuses,
            { label: "", color: "#94a3b8", enabled: true },
        ]);
    };

    const removeStatus = (index: number) => {
        setQualStatuses(qualStatuses.filter((_, i) => i !== index));
    };

    const updateStatus = (index: number, field: string, value: any) => {
        setQualStatuses(qualStatuses.map((s, i) => i === index ? { ...s, [field]: value } : s));
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
            await fetchQualificationConfig();
            await fetchCriteria();
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
        { id: "qualification", label: "Lead Qualification", icon: Target },
        { id: "history", label: "Version History", icon: History },
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
                                        {tab.id === "qualification" && qualQuestions.filter(q => q.enabled !== false).length > 0 && (
                                            <span className="ml-2 bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded-full text-[10px]">
                                                {qualQuestions.filter(q => q.enabled !== false).length}
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
                                                <p className="text-xs text-slate-500">Upload documents (PDF, DOCX, XLSX, TXT, CSV) to provide AI with business context.</p>
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
                                                                    <span>•</span>
                                                                    {file.status === "READY" ? (
                                                                        <span className="text-emerald-600 flex items-center gap-0.5">
                                                                            <CheckCircle2 className="w-3 h-3" /> Indexed
                                                                        </span>
                                                                    ) : (
                                                                        <span className="text-rose-500 flex items-center gap-0.5">
                                                                            <AlertCircle className="w-3 h-3" /> Failed
                                                                        </span>
                                                                    )}
                                                                    {file.extracted && (
                                                                        <>
                                                                            <span>•</span>
                                                                            <span className="text-teal-600">Text extracted</span>
                                                                        </>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all">
                                                            <a
                                                                href={`${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/knowledge/files/${file.id}/download`}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="p-2 text-slate-300 hover:text-teal-600 hover:bg-teal-50 rounded-lg transition-all"
                                                                title="Download"
                                                            >
                                                                <Download className="w-4 h-4" />
                                                            </a>
                                                            <button
                                                                onClick={() => handleDeleteFile(file.id)}
                                                                className="p-2 text-slate-300 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all"
                                                                title="Delete"
                                                            >
                                                                <Trash2 className="w-4 h-4" />
                                                            </button>
                                                        </div>
                                                    </div>
                                                ))
                                            )}
                                        </div>

                                        <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 flex gap-3">
                                            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                                            <p className="text-[11px] text-amber-800 leading-normal">
                                                <strong>Pro Tip:</strong> Uploaded files (TXT, CSV, PDF, DOCX, XLSX) are automatically extracted, chunked, and indexed. The AI retrieves the most relevant knowledge snippets when responding to leads.
                                            </p>
                                        </div>
                                    </div>
                                ) : activeTab === "qualification" ? (
                                    <div className="space-y-8">
                                        {/* Header */}
                                        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                                            <div>
                                                <h2 className="text-lg font-bold text-slate-800">Lead Qualification</h2>
                                                <p className="text-xs text-slate-500">Configure questions the AI collects from leads, and qualification statuses. <span className="text-slate-400">(v{qualVersion})</span></p>
                                            </div>
                                            <button
                                                onClick={handleSaveQualification}
                                                disabled={isSavingQual}
                                                className="bg-teal-700 text-white px-5 py-2 rounded-lg text-sm font-bold hover:bg-teal-800 transition-all flex items-center gap-2 shadow-sm disabled:opacity-50"
                                            >
                                                {isSavingQual ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                                Save Qualification
                                            </button>
                                        </div>

                                        {/* Questions Section */}
                                        <section className="space-y-4">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-2 text-slate-800">
                                                    <Target className="w-4 h-4 text-teal-600" />
                                                    <h3 className="text-sm font-bold uppercase tracking-wider">Qualification Questions</h3>
                                                </div>
                                                <button
                                                    onClick={addQuestion}
                                                    className="text-xs font-bold text-teal-600 hover:text-teal-700 flex items-center gap-1 transition-all"
                                                >
                                                    <Plus className="w-3.5 h-3.5" /> Add Question
                                                </button>
                                            </div>
                                            <p className="text-[11px] text-slate-400">The AI will attempt to collect these details from each lead during conversation.</p>

                                            {qualQuestions.length === 0 ? (
                                                <div className="py-10 flex flex-col items-center justify-center border-2 border-dashed border-slate-200 rounded-xl bg-slate-50 text-slate-400">
                                                    <Target className="w-8 h-8 mb-3 opacity-20" />
                                                    <p className="text-sm font-medium">No questions configured</p>
                                                    <p className="text-[10px] mt-1">Click &quot;Add Question&quot; to start building your qualification form.</p>
                                                </div>
                                            ) : (
                                                <div className="space-y-2">
                                                    {qualQuestions.map((q, i) => (
                                                        <div key={i} className="flex items-center gap-3 p-3 bg-white border border-slate-200 rounded-xl group hover:border-teal-400 transition-all">
                                                            <div className="flex flex-col gap-0.5">
                                                                <button
                                                                    onClick={() => moveQuestion(i, "up")}
                                                                    disabled={i === 0}
                                                                    className="p-0.5 text-slate-300 hover:text-slate-600 disabled:opacity-20 transition-all"
                                                                >
                                                                    <ArrowUp className="w-3 h-3" />
                                                                </button>
                                                                <button
                                                                    onClick={() => moveQuestion(i, "down")}
                                                                    disabled={i === qualQuestions.length - 1}
                                                                    className="p-0.5 text-slate-300 hover:text-slate-600 disabled:opacity-20 transition-all"
                                                                >
                                                                    <ArrowDown className="w-3 h-3" />
                                                                </button>
                                                            </div>
                                                            <input
                                                                type="text"
                                                                value={q.label}
                                                                onChange={(e) => updateQuestion(i, "label", e.target.value)}
                                                                placeholder="e.g. Budget Range"
                                                                className="flex-1 p-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 outline-none transition-all"
                                                            />
                                                            <label className="flex items-center gap-1.5 cursor-pointer select-none">
                                                                <input
                                                                    type="checkbox"
                                                                    checked={q.enabled !== false}
                                                                    onChange={(e) => updateQuestion(i, "enabled", e.target.checked)}
                                                                    className="w-4 h-4 accent-teal-600"
                                                                />
                                                                <span className="text-[10px] font-medium text-slate-500">Enabled</span>
                                                            </label>
                                                            <button
                                                                onClick={() => removeQuestion(i)}
                                                                className="p-1.5 text-slate-300 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                                                            >
                                                                <Trash2 className="w-3.5 h-3.5" />
                                                            </button>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </section>

                                        {/* Statuses Section */}
                                        <section className="space-y-4">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-2 text-slate-800">
                                                    <Shield className="w-4 h-4 text-teal-600" />
                                                    <h3 className="text-sm font-bold uppercase tracking-wider">Qualification Statuses</h3>
                                                </div>
                                                <button
                                                    onClick={addStatus}
                                                    className="text-xs font-bold text-teal-600 hover:text-teal-700 flex items-center gap-1 transition-all"
                                                >
                                                    <Plus className="w-3.5 h-3.5" /> Add Status
                                                </button>
                                            </div>
                                            <p className="text-[11px] text-slate-400">Define the lifecycle stages for your leads. These statuses will appear in the Contacts page.</p>

                                            {qualStatuses.length === 0 ? (
                                                <div className="py-10 flex flex-col items-center justify-center border-2 border-dashed border-slate-200 rounded-xl bg-slate-50 text-slate-400">
                                                    <Shield className="w-8 h-8 mb-3 opacity-20" />
                                                    <p className="text-sm font-medium">No statuses configured</p>
                                                    <p className="text-[10px] mt-1">Click &quot;Add Status&quot; to define lead lifecycle stages.</p>
                                                </div>
                                            ) : (
                                                <div className="space-y-2">
                                                    {qualStatuses.map((s, i) => (
                                                        <div key={i} className="flex items-center gap-3 p-3 bg-white border border-slate-200 rounded-xl group hover:border-teal-400 transition-all">
                                                            <input
                                                                type="color"
                                                                value={s.color || "#94a3b8"}
                                                                onChange={(e) => updateStatus(i, "color", e.target.value)}
                                                                className="w-8 h-8 rounded-lg border border-slate-200 cursor-pointer p-0.5"
                                                                title="Pick color"
                                                            />
                                                            <input
                                                                type="text"
                                                                value={s.label}
                                                                onChange={(e) => updateStatus(i, "label", e.target.value)}
                                                                placeholder="e.g. Qualified"
                                                                className="flex-1 p-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 outline-none transition-all"
                                                            />
                                                            <span
                                                                className="px-3 py-1 rounded-full text-[10px] font-bold text-white"
                                                                style={{ backgroundColor: s.color || "#94a3b8" }}
                                                            >
                                                                {s.label || "Preview"}
                                                            </span>
                                                            <label className="flex items-center gap-1.5 cursor-pointer select-none">
                                                                <input
                                                                    type="checkbox"
                                                                    checked={s.enabled !== false}
                                                                    onChange={(e) => updateStatus(i, "enabled", e.target.checked)}
                                                                    className="w-4 h-4 accent-teal-600"
                                                                />
                                                                <span className="text-[10px] font-medium text-slate-500">Enabled</span>
                                                            </label>
                                                            <button
                                                                onClick={() => removeStatus(i)}
                                                                className="p-1.5 text-slate-300 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                                                            >
                                                                <Trash2 className="w-3.5 h-3.5" />
                                                            </button>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </section>

                                        {/* Qualification Criteria (Mission 29) */}
                                        <section className="space-y-4">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-2 text-slate-800">
                                                    <Sparkles className="w-4 h-4 text-teal-600" />
                                                    <h3 className="text-sm font-bold uppercase tracking-wider">Qualification Criteria</h3>
                                                </div>
                                                <button
                                                    onClick={handleCreateCriterion}
                                                    disabled={savingCriterionId === "new"}
                                                    className="text-xs font-bold text-teal-600 hover:text-teal-700 flex items-center gap-1 transition-all disabled:opacity-50"
                                                >
                                                    <Plus className="w-3.5 h-3.5" /> Add Criterion
                                                </button>
                                            </div>
                                            <p className="text-[11px] text-slate-400">Define rules for evaluating and scoring leads. The AI uses these to determine lead quality.</p>

                                            {criteria.length === 0 ? (
                                                <div className="py-10 flex flex-col items-center justify-center border-2 border-dashed border-slate-200 rounded-xl bg-slate-50 text-slate-400">
                                                    <Sparkles className="w-8 h-8 mb-3 opacity-20" />
                                                    <p className="text-sm font-medium">No criteria defined</p>
                                                    <p className="text-[10px] mt-1">Click &quot;Add Criterion&quot; to define lead qualification rules.</p>
                                                </div>
                                            ) : (
                                                <div className="space-y-3">
                                                    {criteria.map((c) => (
                                                        <div key={c.id} className="p-4 bg-white border border-slate-200 rounded-xl group hover:border-teal-400 transition-all space-y-3">
                                                            <div className="flex items-center gap-3">
                                                                <input
                                                                    type="text"
                                                                    value={c.label}
                                                                    onChange={(e) => setCriteria(criteria.map(cr => cr.id === c.id ? { ...cr, label: e.target.value } : cr))}
                                                                    onBlur={() => handleUpdateCriterion(c.id, { label: c.label })}
                                                                    placeholder="Criterion label"
                                                                    className="flex-1 p-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 outline-none transition-all font-medium"
                                                                />
                                                                <select
                                                                    value={c.criterion_type}
                                                                    onChange={(e) => handleUpdateCriterion(c.id, { criterion_type: e.target.value })}
                                                                    className="w-28 p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs outline-none focus:border-teal-500"
                                                                >
                                                                    <option value="boolean">Boolean</option>
                                                                    <option value="enum">Enum</option>
                                                                    <option value="text">Text</option>
                                                                    <option value="score">Score (1-5)</option>
                                                                </select>
                                                                <input
                                                                    type="number"
                                                                    min={0}
                                                                    value={c.weight ?? ""}
                                                                    onChange={(e) => setCriteria(criteria.map(cr => cr.id === c.id ? { ...cr, weight: e.target.value === "" ? null : parseInt(e.target.value) } : cr))}
                                                                    onBlur={() => handleUpdateCriterion(c.id, { weight: c.weight })}
                                                                    placeholder="Wt"
                                                                    title="Weight (priority)"
                                                                    className="w-16 p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs outline-none focus:border-teal-500 text-center"
                                                                />
                                                                <label className="flex items-center gap-1.5 cursor-pointer select-none">
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={c.is_enabled !== false}
                                                                        onChange={(e) => handleUpdateCriterion(c.id, { is_enabled: e.target.checked })}
                                                                        className="w-4 h-4 accent-teal-600"
                                                                    />
                                                                    <span className="text-[10px] font-medium text-slate-500">On</span>
                                                                </label>
                                                                <button
                                                                    onClick={() => handleDeleteCriterion(c.id)}
                                                                    className="p-1.5 text-slate-300 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                                                                >
                                                                    <Trash2 className="w-3.5 h-3.5" />
                                                                </button>
                                                            </div>
                                                            <input
                                                                type="text"
                                                                value={c.description ?? ""}
                                                                onChange={(e) => setCriteria(criteria.map(cr => cr.id === c.id ? { ...cr, description: e.target.value } : cr))}
                                                                onBlur={() => handleUpdateCriterion(c.id, { description: c.description })}
                                                                placeholder="Description (e.g. Lead has budget above $10K)"
                                                                className="w-full p-2 bg-slate-50/50 border border-slate-100 rounded-lg text-xs text-slate-600 outline-none focus:border-teal-500 transition-all"
                                                            />
                                                            {c.criterion_type === "enum" && (
                                                                <input
                                                                    type="text"
                                                                    value={(c.enum_values || []).join(", ")}
                                                                    onChange={(e) => {
                                                                        const vals = e.target.value.split(",").map((v: string) => v.trim()).filter(Boolean);
                                                                        setCriteria(criteria.map(cr => cr.id === c.id ? { ...cr, enum_values: vals } : cr));
                                                                    }}
                                                                    onBlur={() => handleUpdateCriterion(c.id, { enum_values: c.enum_values })}
                                                                    placeholder="Enum values (comma separated)"
                                                                    className="w-full p-2 bg-amber-50/50 border border-amber-100 rounded-lg text-xs text-amber-800 outline-none focus:border-amber-400 transition-all"
                                                                />
                                                            )}
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </section>

                                        <div className="bg-teal-50/50 border border-teal-100 rounded-xl p-4 flex gap-3">
                                            <AlertCircle className="w-4 h-4 text-teal-600 shrink-0" />
                                            <p className="text-[11px] text-teal-700 leading-normal">
                                                <strong>How it works:</strong> Enabled questions are injected into the AI&apos;s system prompt. The AI will naturally ask leads for this information during conversation. Criteria define how the AI evaluates lead quality. Statuses categorize leads in the Contacts page.
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
