/**
 * Maps DB module keys to marketing-friendly content for the website.
 * Only modules present here appear on the public site.
 * A new DB module without an entry is silently excluded — no fake claims.
 */

export interface ModuleMarketingInfo {
  marketingTitle: string;
  benefit: string;
  description: string;
  iconName: string; // lucide-react icon name
  category: "capture" | "intelligence" | "operations" | "visibility" | "platform";
}

export const MODULE_MARKETING_MAP: Record<string, ModuleMarketingInfo> = {
  prompt_studio: {
    marketingTitle: "AI Prompt Studio",
    benefit: "Qualify at scale",
    description:
      "Custom AI prompts engage every lead the moment they arrive. Scores are assigned based on intent, fit, and urgency — so your reps only work leads worth their time.",
    iconName: "Brain",
    category: "intelligence",
  },
  runtime_engine: {
    marketingTitle: "Runtime Engine",
    benefit: "Always-on execution",
    description:
      "Process and route leads 24/7 with a high-throughput engine that handles qualification, scoring, and dispatch without downtime.",
    iconName: "Zap",
    category: "operations",
  },
  inbox: {
    marketingTitle: "Team Inbox & Handover",
    benefit: "Stay in the loop",
    description:
      "All conversations flow into a shared team inbox. Reps can pick up context instantly, send messages, and mark leads without switching tools.",
    iconName: "Inbox",
    category: "operations",
  },
  analytics: {
    marketingTitle: "Analytics & Conversion Tracking",
    benefit: "Measure what matters",
    description:
      "Track lead volume, qualification rate, response time, conversion by channel and rep, and pipeline velocity — all in real time from a single dashboard.",
    iconName: "BarChart3",
    category: "visibility",
  },
  integrations_hub: {
    marketingTitle: "Integrations Hub",
    benefit: "Connect your stack",
    description:
      "Manage all your connected platforms — WhatsApp, Meta, Zoho CRM — from a single dashboard. Configure, monitor, and troubleshoot in one place.",
    iconName: "Globe",
    category: "platform",
  },
  integrations_connect: {
    marketingTitle: "Integration Connect",
    benefit: "Zero leakage",
    description:
      "Capture leads from web forms, chat widgets, WhatsApp, and more — all routed into one unified pipeline with native integrations.",
    iconName: "Cable",
    category: "capture",
  },
  dispatch_engine: {
    marketingTitle: "Smart Routing & Dispatch",
    benefit: "Right rep, right time",
    description:
      "Route leads by territory, product line, availability, or any custom logic you define. Automated dispatch with instant assignment.",
    iconName: "GitMerge",
    category: "operations",
  },
  knowledge_files: {
    marketingTitle: "Knowledge Base",
    benefit: "AI with context",
    description:
      "Upload product docs, FAQs, and playbooks. Your AI agents reference real business knowledge to give accurate, on-brand answers.",
    iconName: "BookOpen",
    category: "intelligence",
  },
  automations: {
    marketingTitle: "Workflow Automation",
    benefit: "Your rules",
    description:
      "Build trigger-based workflows that act on lead status changes, score thresholds, or time-based events. Automate follow-ups, escalations, and re-routing.",
    iconName: "Settings",
    category: "intelligence",
  },
  webhooks_ingestion: {
    marketingTitle: "Webhook Ingestion",
    benefit: "Any source, any format",
    description:
      "Accept inbound data from any external system via webhooks. Parse, validate, and route payloads directly into your lead pipeline.",
    iconName: "Webhook",
    category: "capture",
  },
  zoho_sync: {
    marketingTitle: "CRM Sync (Zoho)",
    benefit: "Stay connected",
    description:
      "Push qualified leads directly to Zoho CRM. Map fields, set sync rules, and keep your sales stack in perfect alignment without manual exports.",
    iconName: "Database",
    category: "platform",
  },
  email_engine: {
    marketingTitle: "Email Engine",
    benefit: "Reach every inbox",
    description:
      "Send transactional and follow-up emails from your lead pipeline. Templated messages, delivery tracking, and automatic retry on failure.",
    iconName: "Mail",
    category: "operations",
  },
  email_verification: {
    marketingTitle: "Email Verification",
    benefit: "Clean data",
    description:
      "Validate email addresses at capture time to keep your pipeline clean. Reduce bounce rates and improve deliverability automatically.",
    iconName: "ShieldCheck",
    category: "capture",
  },
  diagnostics: {
    marketingTitle: "System Diagnostics",
    benefit: "Full transparency",
    description:
      "Monitor system health, message queues, and integration statuses. Real-time diagnostics help you catch issues before they affect leads.",
    iconName: "Activity",
    category: "visibility",
  },
  admin_portal: {
    marketingTitle: "Admin Portal",
    benefit: "Stay in control",
    description:
      "Role-based access control, user management, and workspace configuration. Know who touched what, and when, with a full audit trail.",
    iconName: "Shield",
    category: "platform",
  },
};

/** Category groupings for the features page */
export const FEATURE_CATEGORIES: {
  key: ModuleMarketingInfo["category"];
  label: string;
  iconName: string;
}[] = [
  { key: "capture", label: "Capture & Intake", iconName: "Zap" },
  { key: "intelligence", label: "Intelligence", iconName: "Brain" },
  { key: "operations", label: "Operations", iconName: "GitMerge" },
  { key: "visibility", label: "Visibility", iconName: "BarChart3" },
  { key: "platform", label: "Platform", iconName: "Shield" },
];
