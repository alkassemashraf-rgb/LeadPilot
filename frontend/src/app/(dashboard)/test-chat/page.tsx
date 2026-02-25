"use client";

import { useState, useEffect } from "react";
import { Send, Bot, User, Trash2, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiClient } from "@/lib/api";

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
}

export default function TestChatPage() {
    const [messages, setMessages] = useState<Message[]>([
        { id: "1", role: "assistant", content: "Hello! I am your AI agent in test mode. How can I help you today?" }
    ]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    const [sessionId, setSessionId] = useState<string | null>(null);

    const handleSend = async () => {
        if (!input.trim()) return;

        let currentSessionId = sessionId;
        if (!currentSessionId) {
            const sessionRes = await apiClient.post("/test-chat/sessions");
            if (sessionRes.success && sessionRes.data) {
                currentSessionId = sessionRes.data.session_id;
                setSessionId(currentSessionId);
            } else {
                alert("Failed to create chat session: " + sessionRes.error);
                return;
            }
        }

        const userMsg: Message = { id: Date.now().toString(), role: "user", content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput("");
        setIsLoading(true);

        const res = await apiClient.post(`/test-chat/sessions/${currentSessionId}/messages`, {
            text: input
        });

        if (res.success && res.data) {
            const aiReply: Message = {
                id: Date.now().toString(),
                role: "assistant",
                content: res.data.reply
            };
            setMessages(prev => [...prev, aiReply]);
        } else {
            alert("AI Error: " + res.error);
        }
        setIsLoading(false);
    };

    return (
        <div className="max-w-4xl mx-auto h-[calc(100vh-160px)] flex flex-col">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight flex items-center gap-3">
                        Test Chat
                        <span className="px-2 py-0.5 bg-slate-200 text-slate-600 text-[10px] font-bold rounded uppercase tracking-wider">Sandbox</span>
                    </h1>
                    <p className="text-slate-500 text-sm">Preview how your AI agent interacts with customers.</p>
                </div>
                <button
                    onClick={() => setMessages([])}
                    className="text-slate-400 hover:text-red-500 transition-colors p-2"
                    title="Clear session"
                >
                    <Trash2 className="w-5 h-5" />
                </button>
            </div>

            <div className="bg-blue-50 border border-blue-100 p-3 rounded-lg flex items-center gap-3 mb-6">
                <Info className="w-4 h-4 text-blue-500" />
                <p className="text-xs text-blue-700 font-medium italic">
                    Messages in this chat are stored as "test" platform type and do not affect live flows.
                </p>
            </div>

            <div className="flex-1 bg-white border border-border rounded-lg shadow-sm flex flex-col overflow-hidden">
                {/* Message List */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {messages.map((msg) => (
                        <div
                            key={msg.id}
                            className={cn(
                                "flex gap-4",
                                msg.role === "user" ? "flex-row-reverse" : "flex-row"
                            )}
                        >
                            <div className={cn(
                                "w-8 h-8 rounded shrink-0 flex items-center justify-center font-bold text-[10px]",
                                msg.role === "user" ? "bg-slate-100 text-slate-600" : "bg-primary text-white"
                            )}>
                                {msg.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                            </div>
                            <div className={cn(
                                "max-w-[80%] px-4 py-3 rounded-lg text-sm leading-relaxed",
                                msg.role === "user" ? "bg-slate-50 text-slate-800 rounded-tr-none" : "bg-white border border-border text-slate-700 rounded-tl-none shadow-sm"
                            )}>
                                {msg.content}
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="flex gap-4 animate-pulse">
                            <div className="w-8 h-8 rounded bg-slate-100 shrink-0"></div>
                            <div className="bg-slate-50 h-10 w-32 rounded-lg"></div>
                        </div>
                    )}
                </div>

                {/* Input area */}
                <div className="p-4 border-t border-border bg-slate-50/50">
                    <div className="relative">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleSend()}
                            placeholder="Type a message to test your AI..."
                            className="w-full bg-white border border-border rounded-lg pl-4 pr-12 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all shadow-sm"
                        />
                        <button
                            onClick={handleSend}
                            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 shadow-sm"
                        >
                            <Send className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
