import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "LeadPilot — AI-Native Lead Capture, Qualification & Routing",
    template: "%s | LeadPilot",
  },
  description:
    "LeadPilot is the AI-native platform that captures, qualifies, and routes leads to the right rep — automatically. Close more deals without growing headcount.",
  keywords: ["lead capture", "lead qualification", "AI sales", "lead routing", "CRM automation", "B2B sales tools"],
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: "LeadPilot",
    title: "LeadPilot — AI-Native Lead Capture, Qualification & Routing",
    description:
      "The AI platform that turns raw web traffic into qualified, routed pipeline — automatically.",
  },
  twitter: {
    card: "summary_large_image",
    title: "LeadPilot — AI-Native Lead Capture, Qualification & Routing",
    description:
      "The AI platform that turns raw web traffic into qualified, routed pipeline — automatically.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen flex flex-col">
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
