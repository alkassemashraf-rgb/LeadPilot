import type { Metadata } from "next";
import { getPlans } from "@/lib/api";
import PlansClientContent from "./PlansClientContent";

export const metadata: Metadata = {
  title: "Plans — Start Free, Scale When Ready",
  description:
    "LeadPilot pricing: a free plan available now, plus Growth and Enterprise tiers coming soon. Join the waitlist for early access.",
};

export default async function PlansPage() {
  const plans = await getPlans();
  return <PlansClientContent plans={plans} />;
}
