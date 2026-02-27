"use client";

import { useState, useEffect, useRef } from "react";
import {
    Search,
    Filter,
    MoreVertical,
    Send,
    Smartphone,
    Facebook,
    User,
    Check,
    CheckCheck,
    AlertCircle,
    Bot,
    UserCircle,
    Archive,
    CloudUpload,
    Clock
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";
import { apiClient } from "@/lib/api";
import { useSearchParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import TimelinePanel from "@/components/inbox/TimelinePanel";

// --- Types ---

type Message = {
    id: string;
    direction: "inbound" | "outbound";
    content: string;
    platform: string;
    created_at: string;
    delivery_status: "pending" | "sending" | "sent" | "failed" | "delivered";
    last_error?: string;
};

type Conversation = {
    conversation_id: string;
    contact: {
        id: string;
        display_name: string;
    };
    last_message_preview: string;
    platform: string;
    status: "bot_active" | "human_takeover" | "closed";
    updated_at: string;
    unread_count: number;
};

// --- Components ---

export default function InboxPage() {
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [thread, setThread] = useState<{ messages: Message[], status: string, contact: any } | null>(null);
    const [loadingConversations, setLoadingConversations] = useState(true);
    const [loadingThread, setLoadingThread] = useState(false);
    const [replyContent, setReplyContent] = useState("");
    const [sending, setSending] = useState(false);
    const [syncingZoho, setSyncingZoho] = useState(false);
    const [showTimeline, setShowTimeline] = useState(false);

    // Filters
    const [searchQuery, setSearchQuery] = useState("");
    const [statusFilter, setStatusFilter] = useState("all");
    const [platformFilter, setPlatformFilter] = useState("all");

    const scrollRef = useRef<HTMLDivElement>(null);

    // Initial Load
    useEffect(() => {
        fetchConversations();
    }, [statusFilter, platformFilter, searchQuery]);

    // Thread Load & Polling
    useEffect(() => {
        if (selectedId) {
            fetchThread(selectedId);
            const interval = setInterval(() => fetchThread(selectedId, true), 5000);
            return () => clearInterval(interval);
        }
    }, [selectedId]);

    // Scroll to bottom on new messages
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [thread?.messages]);

    const fetchConversations = async () => {
        setLoadingConversations(true);
        try {
            let url = `/inbox/conversations?limit=50`;
            if (statusFilter !== "all") url += `&status=${statusFilter}`;
            if (searchQuery) url += `&q=${searchQuery}`;

            const res = await apiClient.get<Conversation[]>(url);
            setConversations(res.data || []);
        } catch (err) {
            toast.error("Failed to load conversations");
        } finally {
            setLoadingConversations(false);
        }
    };

    const fetchThread = async (id: string, quiet = false) => {
        if (!quiet) setLoadingThread(true);
        try {
            const res = await apiClient.get<{ messages: Message[], status: string, contact: any }>(`/inbox/conversations/${id}`);
            setThread(res.data || null);
        } catch (err) {
            if (!quiet) toast.error("Failed to load thread");
        } finally {
            if (!quiet) setLoadingThread(false);
        }
    };

    const handleSendReply = async () => {
        if (!selectedId || !replyContent.trim() || sending) return;

        setSending(true);
        try {
            await apiClient.post(`/inbox/conversations/${selectedId}/reply`, { content: replyContent });
            setReplyContent("");
            // Refresh thread immediately
            fetchThread(selectedId, true);
        } catch (err) {
            toast.error("Failed to send reply");
        } finally {
            setSending(false);
        }
    };

    const handleUpdateStatus = async (id: string, status: string) => {
        try {
            await apiClient.patch(`/inbox/conversations/${id}/status`, { status });
            toast.success(`Status updated to ${status.replace("_", " ")}`);
            fetchThread(id, true);
            fetchConversations();
        } catch (err) {
            toast.error("Failed to update status");
        }
    };

    const handleSyncZoho = async () => {
        const contactId = thread?.contact?.id;
        if (!selectedId || !contactId || syncingZoho) return;
        setSyncingZoho(true);
        try {
            const res = await apiClient.post(`/zoho/contacts/${contactId}/sync`);
            if (res.success) {
                toast.success("Contact synced to Zoho CRM");
            } else {
                toast.error(res.error || "Failed to sync to Zoho");
            }
        } catch (err) {
            toast.error("An unexpected error occurred during sync");
        } finally {
            setSyncingZoho(false);
        }
    };

    return (
        <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-slate-50">
            {/* Left Panel: Conversation List */}
            <div className="w-80 border-r border-slate-200 bg-white flex flex-col">
                <div className="p-4 border-b border-slate-100 space-y-3">
                    <h1 className="text-xl font-bold text-slate-900">Inbox</h1>
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search contacts..."
                            className="w-full pl-9 pr-4 py-2 bg-slate-100 border-none rounded-lg text-sm focus:ring-2 focus:ring-emerald-500/20 transition-all"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                    <div className="flex gap-2">
                        <select
                            className="flex-1 bg-white border border-slate-200 rounded-md text-xs px-2 py-1 text-slate-600 focus:outline-none"
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                        >
                            <option value="all">All Status</option>
                            <option value="bot_active">AI Active</option>
                            <option value="human_takeover">Human</option>
                            <option value="closed">Closed</option>
                        </select>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto">
                    {loadingConversations ? (
                        <div className="p-8 text-center text-slate-400 text-sm">Loading...</div>
                    ) : conversations.length === 0 ? (
                        <div className="p-8 text-center text-slate-400 text-sm">No conversations found</div>
                    ) : (
                        conversations.map((conv) => (
                            <button
                                key={conv.conversation_id}
                                onClick={() => setSelectedId(conv.conversation_id)}
                                className={cn(
                                    "w-full p-4 border-b border-slate-50 flex gap-3 text-left transition-all hover:bg-slate-50",
                                    selectedId === conv.conversation_id ? "bg-emerald-50 border-emerald-100" : ""
                                )}
                            >
                                <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center flex-shrink-0">
                                    <User className="w-5 h-5 text-slate-400" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-start mb-1">
                                        <span className="font-semibold text-sm text-slate-900 truncate">
                                            {conv.contact.display_name}
                                        </span>
                                        <span className="text-[10px] text-slate-400 whitespace-nowrap">
                                            {formatDistanceToNow(new Date(conv.updated_at), { addSuffix: false })}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-1 mb-1">
                                        {conv.platform === "whatsapp" ? (
                                            <Smartphone className="w-3 h-3 text-emerald-500" />
                                        ) : (
                                            <Facebook className="w-3 h-3 text-blue-500" />
                                        )}
                                        <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                                            {conv.platform}
                                        </span>
                                    </div>
                                    <p className="text-xs text-slate-500 truncate leading-relaxed">
                                        {conv.last_message_preview || "No messages yet"}
                                    </p>
                                </div>
                            </button>
                        ))
                    )}
                </div>
            </div>

            {/* Right Panel: Thread & Composer */}
            <div className={cn("flex flex-col bg-white", showTimeline ? "flex-1 min-w-0" : "flex-1")}>
                {selectedId && thread ? (
                    <>
                        {/* Header */}
                        <div className="h-16 px-6 border-b border-slate-100 flex items-center justify-between bg-white z-10">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center">
                                    <User className="w-4 h-4 text-slate-500" />
                                </div>
                                <div>
                                    <h2 className="text-sm font-bold text-slate-900">{thread.contact.display_name}</h2>
                                    <div className="flex items-center gap-2">
                                        <StatusBadge status={thread.status as any} />
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                {thread.status === "bot_active" ? (
                                    <button
                                        onClick={() => handleUpdateStatus(selectedId, "human_takeover")}
                                        className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 text-amber-700 rounded-md text-xs font-semibold hover:bg-amber-100 transition-colors"
                                    >
                                        <UserCircle className="w-3.5 h-3.5" />
                                        Take Over
                                    </button>
                                ) : (
                                    <button
                                        onClick={() => handleUpdateStatus(selectedId, "bot_active")}
                                        className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-md text-xs font-semibold hover:bg-emerald-100 transition-colors"
                                    >
                                        <Bot className="w-3.5 h-3.5" />
                                        Return to AI
                                    </button>
                                )}
                                <button
                                    onClick={() => setShowTimeline(!showTimeline)}
                                    className={cn(
                                        "flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors",
                                        showTimeline
                                            ? "bg-blue-100 text-blue-700 border border-blue-200"
                                            : "bg-slate-50 text-slate-600 hover:bg-slate-100"
                                    )}
                                >
                                    <Clock className="w-3.5 h-3.5" />
                                    Timeline
                                </button>
                                <button
                                    onClick={() => handleUpdateStatus(selectedId, thread.status === "closed" ? "bot_active" : "closed")}
                                    className={cn(
                                        "flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors",
                                        thread.status === "closed"
                                            ? "bg-slate-100 text-slate-600 hover:bg-slate-200"
                                            : "bg-slate-50 text-slate-600 hover:bg-slate-100"
                                    )}
                                >
                                    <Archive className="w-3.5 h-3.5" />
                                    {thread.status === "closed" ? "Re-open" : "Close"}
                                </button>
                            </div>
                        </div>

                        {/* Messages Area */}
                        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/50" ref={scrollRef}>
                            {thread.messages.map((msg, i) => (
                                <div
                                    key={msg.id}
                                    className={cn(
                                        "flex flex-col max-w-[75%]",
                                        msg.direction === "outbound" ? "ml-auto items-end" : "mr-auto items-start"
                                    )}
                                >
                                    <div
                                        className={cn(
                                            "px-4 py-2.5 rounded-2xl text-sm shadow-sm",
                                            msg.direction === "outbound"
                                                ? "bg-emerald-600 text-white rounded-tr-none"
                                                : "bg-white border border-slate-200 text-slate-800 rounded-tl-none"
                                        )}
                                    >
                                        {msg.content}
                                    </div>
                                    <div className="mt-1.5 flex items-center gap-2 px-1">
                                        <span className="text-[10px] text-slate-400">
                                            {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                        {msg.direction === "outbound" && (
                                            <DeliveryStatusBadge status={msg.delivery_status} error={msg.last_error} />
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Composer */}
                        <div className="p-4 border-t border-slate-100 bg-white">
                            {thread.status === "closed" ? (
                                <div className="p-3 bg-slate-50 rounded-lg text-center text-xs text-slate-500 font-medium border border-slate-100">
                                    This conversation is closed. Re-open to send messages.
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {thread.status === "bot_active" && (
                                        <div className="flex items-center gap-2 text-[10px] text-emerald-600 font-bold uppercase tracking-wider px-1">
                                            <Bot className="w-3 h-3" />
                                            AI is currently active
                                        </div>
                                    )}
                                    <div className="flex items-end gap-2 bg-slate-50 border border-slate-200 rounded-xl p-2 transition-all focus-within:ring-2 focus-within:ring-emerald-500/10 focus-within:border-emerald-500/30">
                                        <textarea
                                            placeholder="Type your reply..."
                                            rows={1}
                                            className="flex-1 bg-transparent border-none focus:ring-0 text-sm py-2 resize-none max-h-32 text-slate-800 placeholder:text-slate-400"
                                            value={replyContent}
                                            onChange={(e) => setReplyContent(e.target.value)}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter' && !e.shiftKey) {
                                                    e.preventDefault();
                                                    handleSendReply();
                                                }
                                            }}
                                        />
                                        <button
                                            disabled={!replyContent.trim() || sending}
                                            onClick={handleSendReply}
                                            className="p-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:bg-slate-300 transition-all shadow-sm active:scale-95"
                                        >
                                            <Send className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-slate-400 gap-4">
                        <div className="w-16 h-16 rounded-full bg-slate-50 flex items-center justify-center border border-slate-100 shadow-inner">
                            <MessageSquare className="w-8 h-8 opacity-20" />
                        </div>
                        <p className="text-sm font-medium">Select a conversation to start chatting</p>
                    </div>
                )}
            </div>

            {/* Timeline Side Panel */}
            {showTimeline && selectedId && (
                <div className="w-80 border-l border-slate-200 bg-white overflow-y-auto">
                    <TimelinePanel conversationId={selectedId} />
                </div>
            )}
        </div>
    );
}

// --- Subcomponents ---

function StatusBadge({ status }: { status: "bot_active" | "human_takeover" | "closed" }) {
    switch (status) {
        case "bot_active":
            return <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full text-[10px] font-bold border border-emerald-200 uppercase">AI Active</div>;
        case "human_takeover":
            return <div className="flex items-center gap-1.5 px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full text-[10px] font-bold border border-amber-200 uppercase">Human Control</div>;
        case "closed":
            return <div className="flex items-center gap-1.5 px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full text-[10px] font-bold border border-slate-200 uppercase">Closed</div>;
    }
}

function DeliveryStatusBadge({ status, error }: { status: string, error?: string }) {
    switch (status) {
        case "pending":
        case "sending":
            return <div className="w-3 h-3 border-2 border-slate-300 border-t-transparent rounded-full animate-spin" />;
        case "sent":
            return <Check className="w-3 h-3 text-slate-400" />;
        case "delivered":
            return <CheckCheck className="w-3 h-3 text-emerald-400" />;
        case "failed":
            return (
                <div className="group relative">
                    <AlertCircle className="w-3 h-3 text-red-400 cursor-help" />
                    {error && (
                        <div className="absolute bottom-full right-0 mb-1 hidden group-hover:block w-48 p-2 bg-slate-800 text-white text-[10px] rounded-md shadow-lg pointer-events-none">
                            {error}
                        </div>
                    )}
                </div>
            );
        default:
            return null;
    }
}

function MessageSquare(props: any) {
    return (
        <svg
            {...props}
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
    )
}
