"use client";

import { useState } from "react";
import {
    Plus,
    Trash2,
    ChevronRight,
    ChevronLeft,
    Zap,
    Bot,
    Send,
    UserRound,
    Tag as TagIcon,
    CheckCircle2,
    Loader2,
    MessageSquare,
    Facebook,
    Instagram,
    X,
    Sparkles
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiClient } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";

type StepType = "AI_REPLY" | "SEND_MESSAGE" | "HUMAN_HANDOVER" | "TAG_CONTACT";

interface Step {
    id: string;
    type: StepType;
    config: any;
}

export default function NewAutomationPage() {
    const router = useRouter();
    const [currentStep, setCurrentStep] = useState(1);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Builder State
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [trigger, setTrigger] = useState({ type: "MESSAGE_INBOUND", platform: "whatsapp", keywords: [] });
    const [steps, setSteps] = useState<Step[]>([]);

    const addStep = (type: StepType) => {
        const newStep: Step = {
            id: Math.random().toString(36).substr(2, 9),
            type,
            config: type === "AI_REPLY" ? {
                use_workspace_prompt: true,
                max_tokens: 200,
                temperature: 0.7,
                guardrails: { no_pricing: true, one_question: true, escalate_on_human: true }
            } : type === "SEND_MESSAGE" ? {
                source: "ai_output",
                text: ""
            } : type === "HUMAN_HANDOVER" ? {
                text: "A team member will contact you on this number."
            } : {
                tag: ""
            }
        };
        setSteps([...steps, newStep]);
    };

    const removeStep = (id: string) => {
        setSteps(steps.filter(s => s.id !== id));
    };

    const handlePublish = async (publish: boolean = false) => {
        setIsSubmitting(true);
        const res = await apiClient.post("/automations/from-builder", {
            name,
            description,
            trigger,
            steps,
            publish
        });

        if (res.success) {
            router.push("/automations");
        } else {
            alert("Error publishing: " + res.error);
        }
        setIsSubmitting(false);
    };

    return (
        <div className="h-full flex flex-col bg-slate-50/50">
            {/* Wizard Header */}
            <header className="bg-white border-b border-border p-4 sticky top-0 z-10 shadow-sm">
                <div className="max-w-4xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/automations" className="text-slate-400 hover:text-slate-600">
                            <X className="w-5 h-5" />
                        </Link>
                        <h1 className="text-xl font-bold text-slate-900">
                            {name || "New Automation"}
                        </h1>
                    </div>

                    <div className="flex items-center gap-2">
                        {[1, 2, 3, 4].map((s) => (
                            <div
                                key={s}
                                className={cn(
                                    "w-2.5 h-2.5 rounded-full transition-colors",
                                    currentStep === s ? "bg-teal-600" : s < currentStep ? "bg-teal-200" : "bg-slate-200"
                                )}
                            />
                        ))}
                    </div>

                    <div className="flex items-center gap-3">
                        {currentStep > 1 && (
                            <button
                                onClick={() => setCurrentStep(currentStep - 1)}
                                className="flex items-center gap-2 px-4 py-2 text-slate-600 font-medium hover:bg-slate-100 rounded-lg transition-colors"
                            >
                                <ChevronLeft className="w-4 h-4" />
                                Back
                            </button>
                        )}
                        {currentStep < 4 ? (
                            <button
                                onClick={() => setCurrentStep(currentStep + 1)}
                                disabled={currentStep === 1 && !name}
                                className="flex items-center gap-2 px-6 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg font-medium transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Next
                                <ChevronRight className="w-4 h-4" />
                            </button>
                        ) : (
                            <button
                                onClick={() => handlePublish(true)}
                                disabled={isSubmitting}
                                className="flex items-center gap-2 px-6 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg font-medium transition-all shadow-sm disabled:opacity-50"
                            >
                                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                                Publish
                            </button>
                        )}
                    </div>
                </div>
            </header>

            {/* Wizard Body */}
            <main className="flex-1 p-8 max-w-4xl mx-auto w-full">
                {currentStep === 1 && (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
                        <div className="space-y-2">
                            <h2 className="text-2xl font-bold text-slate-900">Automation Basics</h2>
                            <p className="text-muted-foreground">Give your automation a name and description to stay organized.</p>
                        </div>
                        <div className="space-y-4 bg-white p-6 rounded-2xl border border-border shadow-sm">
                            <div className="space-y-2">
                                <label className="text-sm font-semibold text-slate-700">Name</label>
                                <input
                                    type="text"
                                    placeholder="e.g. Welcome Message"
                                    className="w-full px-4 py-2 border border-border rounded-lg outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-semibold text-slate-700">Description (Optional)</label>
                                <textarea
                                    placeholder="Describe what this flow does..."
                                    className="w-full px-4 py-2 border border-border rounded-lg h-24 outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all resize-none"
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                />
                            </div>
                        </div>
                    </div>
                )}

                {currentStep === 2 && (
                    <div className="space-y-6 animate-in fade-in slide-in-from-right-2">
                        <div className="space-y-2">
                            <h2 className="text-2xl font-bold text-slate-900">Select Trigger</h2>
                            <p className="text-muted-foreground">What event should start this automation?</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {[
                                { id: "whatsapp", name: "WhatsApp Message", type: "MESSAGE_INBOUND", icon: MessageSquare, color: "text-green-600", bg: "bg-green-50" },
                                { id: "meta-msg", name: "Messenger/Instagram", type: "MESSAGE_INBOUND", icon: Facebook, color: "text-blue-600", bg: "bg-blue-50" },
                                { id: "leadgen", name: "Meta Lead Ads", type: "LEAD_AD_SUBMIT", icon: Zap, color: "text-orange-600", bg: "bg-orange-50" }
                            ].map((t) => (
                                <button
                                    key={t.id}
                                    onClick={() => setTrigger({ ...trigger, type: t.type, platform: t.id === "whatsapp" ? "whatsapp" : "meta" })}
                                    className={cn(
                                        "flex items-start gap-4 p-5 rounded-2xl border transition-all text-left group hover:scale-[1.02]",
                                        (trigger.type === t.type && (t.id === "whatsapp" ? trigger.platform === "whatsapp" : trigger.platform === "meta"))
                                            ? "border-teal-500 bg-teal-50/50 ring-2 ring-teal-500/10"
                                            : "border-border bg-white hover:border-teal-200"
                                    )}
                                >
                                    <div className={cn("p-3 rounded-xl", t.bg, t.color)}>
                                        <t.icon className="w-6 h-6" />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-slate-900">{t.name}</h3>
                                        <p className="text-xs text-muted-foreground mt-1">Starts when a new {t.name.toLowerCase()} is received.</p>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {currentStep === 3 && (
                    <div className="space-y-6 animate-in fade-in slide-in-from-right-2">
                        <div className="flex justify-between items-end">
                            <div className="space-y-2">
                                <h2 className="text-2xl font-bold text-slate-900">Automation Steps</h2>
                                <p className="text-muted-foreground">Define the sequence of actions for this flow.</p>
                            </div>
                            <div className="relative group">
                                <button className="flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-lg font-medium hover:bg-slate-800 transition-colors">
                                    <Plus className="w-4 h-4" />
                                    Add Step
                                </button>
                                <div className="absolute right-0 top-full mt-2 w-56 bg-white border border-border shadow-xl rounded-xl p-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-20">
                                    {[
                                        { type: "AI_REPLY", name: "AI Reply", icon: Bot },
                                        { type: "SEND_MESSAGE", name: "Send Message", icon: Send },
                                        { type: "HUMAN_HANDOVER", name: "Human Handover", icon: UserRound },
                                        { type: "TAG_CONTACT", name: "Tag Contact", icon: TagIcon }
                                    ].map(action => (
                                        <button
                                            key={action.type}
                                            onClick={() => addStep(action.type as StepType)}
                                            className="w-full flex items-center gap-3 p-2.5 hover:bg-teal-50 hover:text-teal-600 rounded-lg text-sm font-medium transition-colors"
                                        >
                                            <action.icon className="w-4 h-4" />
                                            {action.name}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="space-y-3">
                            {steps.length === 0 ? (
                                <div className="py-20 border-2 border-dashed border-border rounded-2xl flex flex-col items-center justify-center text-muted-foreground gap-3">
                                    <Zap className="w-10 h-10 opacity-20" />
                                    <p>No steps added yet. Start by adding an AI Reply or Message.</p>
                                </div>
                            ) : (
                                steps.map((step, index) => (
                                    <div key={step.id} className="bg-white border border-border rounded-2xl p-5 shadow-sm group hover:border-teal-200 transition-all relative">
                                        <button
                                            onClick={() => removeStep(step.id)}
                                            className="absolute top-4 right-4 text-slate-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                        <div className="flex items-center gap-3 mb-4">
                                            <span className="w-6 h-6 rounded-full bg-slate-100 text-[10px] font-bold flex items-center justify-center text-slate-500">
                                                {index + 1}
                                            </span>
                                            <div className="flex items-center gap-2 font-bold text-slate-700">
                                                {step.type === "AI_REPLY" && <Bot className="w-4 h-4 text-teal-600" />}
                                                {step.type === "SEND_MESSAGE" && <Send className="w-4 h-4 text-teal-600" />}
                                                {step.type === "HUMAN_HANDOVER" && <UserRound className="w-4 h-4 text-teal-600" />}
                                                {step.type === "TAG_CONTACT" && <TagIcon className="w-4 h-4 text-teal-600" />}
                                                {step.type.replace("_", " ")}
                                            </div>
                                        </div>

                                        {/* Step Specific Forms */}
                                        <div className="space-y-4 pt-2">
                                            {step.type === "AI_REPLY" && (
                                                <div className="space-y-4">
                                                    <div className="space-y-1.5">
                                                        <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Goal for this Step</label>
                                                        <input
                                                            type="text"
                                                            placeholder="e.g. Schedule a demo, Qualify the lead"
                                                            className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 outline-none transition-all"
                                                            value={step.config.goal || ""}
                                                            onChange={(e) => {
                                                                const newSteps = [...steps];
                                                                newSteps[index].config.goal = e.target.value;
                                                                setSteps(newSteps);
                                                            }}
                                                        />
                                                    </div>

                                                    <div className="space-y-2">
                                                        <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Specific Tasks</label>
                                                        <div className="space-y-2">
                                                            {(step.config.tasks || [""]).map((task: string, tIndex: number) => (
                                                                <div key={tIndex} className="flex gap-2">
                                                                    <input
                                                                        type="text"
                                                                        placeholder={`Task ${tIndex + 1}...`}
                                                                        className="flex-1 p-2 bg-slate-50 border border-slate-200 rounded-lg text-sm outline-none"
                                                                        value={task}
                                                                        onChange={(e) => {
                                                                            const newSteps = [...steps];
                                                                            if (!newSteps[index].config.tasks) newSteps[index].config.tasks = [""];
                                                                            newSteps[index].config.tasks[tIndex] = e.target.value;
                                                                            setSteps(newSteps);
                                                                        }}
                                                                    />
                                                                    {(step.config.tasks?.length || 0) > 1 && (
                                                                        <button
                                                                            onClick={() => {
                                                                                const newSteps = [...steps];
                                                                                newSteps[index].config.tasks.splice(tIndex, 1);
                                                                                setSteps(newSteps);
                                                                            }}
                                                                            className="p-2 text-slate-300 hover:text-rose-500"
                                                                        >
                                                                            <Trash2 className="w-4 h-4" />
                                                                        </button>
                                                                    )}
                                                                </div>
                                                            ))}
                                                            <button
                                                                onClick={() => {
                                                                    const newSteps = [...steps];
                                                                    if (!newSteps[index].config.tasks) newSteps[index].config.tasks = [""];
                                                                    newSteps[index].config.tasks.push("");
                                                                    setSteps(newSteps);
                                                                }}
                                                                className="text-[10px] font-bold text-teal-600 uppercase flex items-center gap-1 hover:text-teal-700"
                                                            >
                                                                <Plus className="w-3 h-3" />
                                                                Add Task
                                                            </button>
                                                        </div>
                                                    </div>

                                                    <div className="space-y-1.5 pt-2 border-t border-slate-50">
                                                        <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Extra Instructions</label>
                                                        <textarea
                                                            placeholder="Anything else the AI should know for this specific step?"
                                                            className="w-full h-20 p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm outline-none resize-none"
                                                            value={step.config.extra_instructions || ""}
                                                            onChange={(e) => {
                                                                const newSteps = [...steps];
                                                                newSteps[index].config.extra_instructions = e.target.value;
                                                                setSteps(newSteps);
                                                            }}
                                                        />
                                                    </div>
                                                </div>
                                            )}
                                            {step.type === "SEND_MESSAGE" && (
                                                <div className="space-y-2">
                                                    <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Content Source</label>
                                                    <div className="flex gap-2">
                                                        <button className="flex-1 p-2 bg-teal-50 border border-teal-200 text-teal-700 rounded-lg text-sm font-medium">AI Output</button>
                                                        <button className="flex-1 p-2 border border-border text-slate-600 rounded-lg text-sm hover:bg-slate-50">Custom Text</button>
                                                    </div>
                                                </div>
                                            )}
                                            {step.type === "HUMAN_HANDOVER" && (
                                                <div className="space-y-1">
                                                    <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Announcement Message</label>
                                                    <input type="text" className="w-full p-2 border border-border rounded-lg text-sm bg-slate-50" defaultValue="A team member will contact you on this number." />
                                                </div>
                                            )}
                                            {step.type === "TAG_CONTACT" && (
                                                <div className="space-y-1">
                                                    <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Tag to Apply</label>
                                                    <input type="text" className="w-full p-2 border border-border rounded-lg text-sm bg-slate-50" placeholder="e.g. interested" />
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}

                {currentStep === 4 && (
                    <div className="space-y-6 animate-in fade-in zoom-in-95">
                        <div className="text-center space-y-2 pb-4">
                            <CheckCircle2 className="w-12 h-12 text-teal-600 mx-auto" />
                            <h2 className="text-2xl font-bold text-slate-900">Review & Publish</h2>
                            <p className="text-muted-foreground">Confirm your settings before going live.</p>
                        </div>

                        <div className="space-y-4">
                            <div className="bg-white border border-border rounded-2xl p-6 shadow-sm divide-y divide-slate-100">
                                <div className="py-4 first:pt-0 space-y-2">
                                    <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Trigger</div>
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-teal-50 text-teal-600 rounded-lg">
                                            <Zap className="w-4 h-4 fill-current" />
                                        </div>
                                        <div className="font-semibold text-slate-700">{trigger.type.replace("_", " ")} ({trigger.platform})</div>
                                    </div>
                                </div>
                                <div className="py-4 space-y-3">
                                    <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Steps ({steps.length})</div>
                                    <div className="space-y-2">
                                        {steps.map((s, i) => (
                                            <div key={s.id} className="text-sm flex items-center gap-3 text-slate-600 bg-slate-50 p-3 rounded-xl border border-border/50">
                                                <span className="w-5 h-5 bg-white border border-border text-[10px] flex items-center justify-center rounded-full font-bold">{i + 1}</span>
                                                {s.type.replace("_", " ")}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="p-4 bg-teal-50 border border-teal-100 rounded-xl flex gap-3 text-teal-800 text-sm">
                                <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                                <p>This automation will run for all incoming messages on the selected platform. You can change this later.</p>
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
