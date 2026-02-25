"use client";

import { useState } from "react";
import { CheckCircle, AlertCircle, Loader2 } from "lucide-react";

type FormState = "idle" | "loading" | "success" | "error";

interface FormData {
  fullName: string;
  workEmail: string;
  company: string;
  website: string;
  message: string;
}

const initialData: FormData = {
  fullName: "",
  workEmail: "",
  company: "",
  website: "",
  message: "",
};

function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default function ContactForm({ dark = false }: { dark?: boolean }) {
  const [formData, setFormData] = useState<FormData>(initialData);
  const [errors, setErrors] = useState<Partial<FormData>>({});
  const [formState, setFormState] = useState<FormState>("idle");

  const inputBase = dark
    ? {
        background: "rgba(255,255,255,0.05)",
        border: "1px solid rgba(255,255,255,0.1)",
        color: "#F1F5F9",
        outline: "none",
      }
    : {
        background: "#FFFFFF",
        border: "1px solid #E2E8F0",
        color: "#334155",
        outline: "none",
      };

  const labelColor = dark ? "rgba(148,163,184,0.9)" : "#334155";
  const placeholderClass = dark ? "placeholder:text-slate-600" : "placeholder:text-slate-400";

  function validate(): boolean {
    const newErrors: Partial<FormData> = {};
    if (!formData.fullName.trim()) newErrors.fullName = "Full name is required.";
    if (!formData.workEmail.trim()) {
      newErrors.workEmail = "Work email is required.";
    } else if (!validateEmail(formData.workEmail)) {
      newErrors.workEmail = "Please enter a valid email address.";
    }
    if (!formData.company.trim()) newErrors.company = "Company name is required.";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setFormState("loading");

    // TODO: Replace with real API endpoint integration
    // e.g. POST /api/contact or third-party form service
    await new Promise((r) => setTimeout(r, 1200));

    try {
      // Placeholder: simulate successful submission
      setFormState("success");
      setFormData(initialData);
    } catch {
      setFormState("error");
    }
  }

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name as keyof FormData]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  }

  if (formState === "success") {
    return (
      <div
        className="rounded-2xl p-10 flex flex-col items-center text-center gap-4"
        style={
          dark
            ? { background: "rgba(15,118,110,0.08)", border: "1px solid rgba(20,184,166,0.25)" }
            : { background: "#F0FDF9", border: "1px solid #A7F3D0" }
        }
        role="alert"
      >
        <CheckCircle className="w-12 h-12" style={{ color: "#14B8A6" }} aria-hidden="true" />
        <h3 className="text-xl font-bold" style={{ color: dark ? "#F1F5F9" : "#0F766E" }}>
          Message received — we&apos;ll be in touch soon.
        </h3>
        <p className="text-sm" style={{ color: dark ? "#94A3B8" : "#334155" }}>
          Expect a reply within one business day.
        </p>
        <button
          className="mt-2 text-sm font-medium underline underline-offset-2"
          style={{ color: "#14B8A6" }}
          onClick={() => setFormState("idle")}
        >
          Send another message
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate aria-label="Contact form">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        {/* Full Name */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="fullName"
            className="text-sm font-medium"
            style={{ color: labelColor }}
          >
            Full Name <span aria-hidden="true" style={{ color: "#EF4444" }}>*</span>
          </label>
          <input
            id="fullName"
            name="fullName"
            type="text"
            autoComplete="name"
            value={formData.fullName}
            onChange={handleChange}
            required
            aria-required="true"
            aria-describedby={errors.fullName ? "fullName-error" : undefined}
            aria-invalid={!!errors.fullName}
            placeholder="Jane Smith"
            className={`px-4 py-2.5 rounded-lg text-sm w-full transition-all duration-200 ${placeholderClass}`}
            style={{
              ...inputBase,
              borderColor: errors.fullName ? "#EF4444" : undefined,
            }}
            onFocus={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = "#0F766E";
              (e.currentTarget as HTMLElement).style.boxShadow =
                "0 0 0 3px rgba(15,118,110,0.15)";
            }}
            onBlur={(e) => {
              if (!errors.fullName) {
                (e.currentTarget as HTMLElement).style.borderColor = dark
                  ? "rgba(255,255,255,0.1)"
                  : "#E2E8F0";
              }
              (e.currentTarget as HTMLElement).style.boxShadow = "none";
            }}
          />
          {errors.fullName && (
            <p id="fullName-error" className="text-xs" style={{ color: "#EF4444" }} role="alert">
              {errors.fullName}
            </p>
          )}
        </div>

        {/* Work Email */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="workEmail"
            className="text-sm font-medium"
            style={{ color: labelColor }}
          >
            Work Email <span aria-hidden="true" style={{ color: "#EF4444" }}>*</span>
          </label>
          <input
            id="workEmail"
            name="workEmail"
            type="email"
            autoComplete="email"
            value={formData.workEmail}
            onChange={handleChange}
            required
            aria-required="true"
            aria-describedby={errors.workEmail ? "workEmail-error" : undefined}
            aria-invalid={!!errors.workEmail}
            placeholder="jane@company.com"
            className={`px-4 py-2.5 rounded-lg text-sm w-full transition-all duration-200 ${placeholderClass}`}
            style={{
              ...inputBase,
              borderColor: errors.workEmail ? "#EF4444" : undefined,
            }}
            onFocus={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = "#0F766E";
              (e.currentTarget as HTMLElement).style.boxShadow =
                "0 0 0 3px rgba(15,118,110,0.15)";
            }}
            onBlur={(e) => {
              if (!errors.workEmail) {
                (e.currentTarget as HTMLElement).style.borderColor = dark
                  ? "rgba(255,255,255,0.1)"
                  : "#E2E8F0";
              }
              (e.currentTarget as HTMLElement).style.boxShadow = "none";
            }}
          />
          {errors.workEmail && (
            <p id="workEmail-error" className="text-xs" style={{ color: "#EF4444" }} role="alert">
              {errors.workEmail}
            </p>
          )}
        </div>

        {/* Company */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="company"
            className="text-sm font-medium"
            style={{ color: labelColor }}
          >
            Company <span aria-hidden="true" style={{ color: "#EF4444" }}>*</span>
          </label>
          <input
            id="company"
            name="company"
            type="text"
            autoComplete="organization"
            value={formData.company}
            onChange={handleChange}
            required
            aria-required="true"
            aria-describedby={errors.company ? "company-error" : undefined}
            aria-invalid={!!errors.company}
            placeholder="Acme Corp"
            className={`px-4 py-2.5 rounded-lg text-sm w-full transition-all duration-200 ${placeholderClass}`}
            style={{
              ...inputBase,
              borderColor: errors.company ? "#EF4444" : undefined,
            }}
            onFocus={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = "#0F766E";
              (e.currentTarget as HTMLElement).style.boxShadow =
                "0 0 0 3px rgba(15,118,110,0.15)";
            }}
            onBlur={(e) => {
              if (!errors.company) {
                (e.currentTarget as HTMLElement).style.borderColor = dark
                  ? "rgba(255,255,255,0.1)"
                  : "#E2E8F0";
              }
              (e.currentTarget as HTMLElement).style.boxShadow = "none";
            }}
          />
          {errors.company && (
            <p id="company-error" className="text-xs" style={{ color: "#EF4444" }} role="alert">
              {errors.company}
            </p>
          )}
        </div>

        {/* Website */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="website"
            className="text-sm font-medium"
            style={{ color: labelColor }}
          >
            Website{" "}
            <span className="text-xs" style={{ color: dark ? "#475569" : "#94A3B8" }}>
              (optional)
            </span>
          </label>
          <input
            id="website"
            name="website"
            type="url"
            autoComplete="url"
            value={formData.website}
            onChange={handleChange}
            placeholder="https://yourcompany.com"
            className={`px-4 py-2.5 rounded-lg text-sm w-full transition-all duration-200 ${placeholderClass}`}
            style={inputBase}
            onFocus={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = "#0F766E";
              (e.currentTarget as HTMLElement).style.boxShadow =
                "0 0 0 3px rgba(15,118,110,0.15)";
            }}
            onBlur={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = dark
                ? "rgba(255,255,255,0.1)"
                : "#E2E8F0";
              (e.currentTarget as HTMLElement).style.boxShadow = "none";
            }}
          />
        </div>

        {/* Message */}
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <label
            htmlFor="message"
            className="text-sm font-medium"
            style={{ color: labelColor }}
          >
            Message{" "}
            <span className="text-xs" style={{ color: dark ? "#475569" : "#94A3B8" }}>
              (optional)
            </span>
          </label>
          <textarea
            id="message"
            name="message"
            rows={4}
            value={formData.message}
            onChange={handleChange}
            placeholder="Tell us about your team size, current lead volume, or what you're trying to solve…"
            className={`px-4 py-2.5 rounded-lg text-sm w-full resize-y transition-all duration-200 ${placeholderClass}`}
            style={inputBase}
            onFocus={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = "#0F766E";
              (e.currentTarget as HTMLElement).style.boxShadow =
                "0 0 0 3px rgba(15,118,110,0.15)";
            }}
            onBlur={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = dark
                ? "rgba(255,255,255,0.1)"
                : "#E2E8F0";
              (e.currentTarget as HTMLElement).style.boxShadow = "none";
            }}
          />
        </div>
      </div>

      {formState === "error" && (
        <div
          className="mt-4 flex items-center gap-2 p-3 rounded-lg"
          style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)" }}
          role="alert"
        >
          <AlertCircle className="w-4 h-4 shrink-0" style={{ color: "#EF4444" }} />
          <p className="text-sm" style={{ color: "#FCA5A5" }}>
            Something went wrong. Please try again or email us directly.
          </p>
        </div>
      )}

      <button
        type="submit"
        disabled={formState === "loading"}
        className="mt-6 w-full px-6 py-3.5 rounded-xl font-semibold text-white text-sm transition-all duration-200 flex items-center justify-center gap-2"
        style={{
          background: formState === "loading"
            ? "rgba(15,118,110,0.6)"
            : "linear-gradient(135deg, #0F766E, #14B8A6)",
          cursor: formState === "loading" ? "not-allowed" : "pointer",
        }}
        onMouseEnter={(e) => {
          if (formState !== "loading") {
            (e.currentTarget as HTMLElement).style.boxShadow =
              "0 0 25px rgba(15,118,110,0.4)";
          }
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLElement).style.boxShadow = "none";
        }}
      >
        {formState === "loading" && (
          <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
        )}
        {formState === "loading" ? "Sending…" : "Send Message"}
      </button>

      <p className="mt-3 text-xs text-center" style={{ color: dark ? "#475569" : "#94A3B8" }}>
        We respond within one business day.
      </p>
    </form>
  );
}
