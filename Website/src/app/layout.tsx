import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import MarketingHeader from "@/components/Header";
import MarketingFooter from "@/components/Footer";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: {
    default: "LeadPilot — AI-Native Lead Capture, Qualification & Routing",
    template: "%s | LeadPilot",
  },
  description:
    "LeadPilot is the AI-native platform that captures, qualifies, and routes leads to the right rep automatically. Close more deals without growing headcount.",
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: "LeadPilot",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-inter antialiased`}>
        <div className="flex flex-col min-h-screen">
          <MarketingHeader />
          <main className="flex-1">{children}</main>
          <MarketingFooter />
        </div>
      </body>
    </html>
  );
}
