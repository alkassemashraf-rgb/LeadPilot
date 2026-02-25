"use client";

import { useState } from "react";
import { CheckCircle, AlertCircle, Loader2 } from "lucide-react";

type State = "idle" | "loading" | "success" | "error";
interface FormData { fullName: string; workEmail: string; company: string; website: string; message: string; }
const empty: FormData = { fullName: "", workEmail: "", company: "", website: "", message: "" };

export default function ContactForm({ dark = false }: { dark?: boolean }) {
  const [data, setData] = useState<FormData>(empty);
  const [errors, setErrors] = useState<Partial<FormData>>({});
  const [state, setState] = useState<State>("idle");

  const inputStyle = {
    background: dark ? "rgba(255,255,255,0.05)" : "#FFFFFF",
    border: `1px solid ${dark ? "rgba(255,255,255,0.1)" : "#E2E8F0"}`,
    color: dark ? "#F1F5F9" : "#334155",
    outline: "none",
  };

  function validate() {
    const e: Partial<FormData> = {};
    if (!data.fullName.trim()) e.fullName = "Required.";
    if (!data.workEmail.trim()) e.workEmail = "Required.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.workEmail)) e.workEmail = "Enter a valid email.";
    if (!data.company.trim()) e.company = "Required.";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    setState("loading");
    // TODO: replace with real API call — e.g. POST /api/contact
    await new Promise(r => setTimeout(r, 1200));
    setState("success");
    setData(empty);
  }

  function change(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    const { name, value } = e.target;
    setData(p => ({ ...p, [name]: value }));
    if (errors[name as keyof FormData]) setErrors(p => ({ ...p, [name]: undefined }));
  }

  function focusStyle(e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) {
    e.currentTarget.style.borderColor = "#0F766E";
    e.currentTarget.style.boxShadow = "0 0 0 3px rgba(15,118,110,0.15)";
  }
  function blurStyle(e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>, hasErr?: boolean) {
    if (!hasErr) e.currentTarget.style.borderColor = dark ? "rgba(255,255,255,0.1)" : "#E2E8F0";
    e.currentTarget.style.boxShadow = "none";
  }

  if (state === "success") {
    return (
      <div
        className="rounded-2xl p-10 flex flex-col items-center text-center gap-4"
        style={dark ? { background: "rgba(15,118,110,0.1)", border: "1px solid rgba(20,184,166,0.25)" } : { background: "#F0FDF9", border: "1px solid #A7F3D0" }}
        role="alert"
      >
        <CheckCircle className="w-12 h-12" style={{ color: "#14B8A6" }} />
        <h3 className="text-xl font-bold" style={{ color: dark ? "#F1F5F9" : "#0F766E" }}>
          Message received — we&apos;ll be in touch soon.
        </h3>
        <p className="text-sm" style={{ color: dark ? "#94A3B8" : "#334155" }}>Expect a reply within one business day.</p>
        <button className="mt-2 text-sm font-medium underline underline-offset-2" style={{ color: "#14B8A6" }} onClick={() => setState("idle")}>
          Send another message
        </button>
      </div>
    );
  }

  const labelColor = dark ? "rgba(148,163,184,0.9)" : "#334155";
  const ph = dark ? "placeholder:text-slate-600" : "placeholder:text-slate-400";

  const field = (id: keyof FormData, label: string, type = "text", required = true, ac = "") => (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium" style={{ color: labelColor }}>
        {label} {required && <span aria-hidden="true" style={{ color: "#EF4444" }}>*</span>}
        {!required && <span className="text-xs ml-1" style={{ color: dark ? "#475569" : "#94A3B8" }}>(optional)</span>}
      </label>
      <input
        id={id} name={id} type={type} autoComplete={ac}
        value={data[id]} onChange={change} required={required}
        aria-required={required} aria-invalid={!!errors[id]}
        className={`px-4 py-2.5 rounded-lg text-sm w-full transition-all duration-150 ${ph}`}
        style={{ ...inputStyle, borderColor: errors[id] ? "#EF4444" : undefined }}
        onFocus={focusStyle}
        onBlur={(e) => blurStyle(e, !!errors[id])}
      />
      {errors[id] && <p className="text-xs" style={{ color: "#EF4444" }} role="alert">{errors[id]}</p>}
    </div>
  );

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        {field("fullName", "Full Name", "text", true, "name")}
        {field("workEmail", "Work Email", "email", true, "email")}
        {field("company", "Company", "text", true, "organization")}
        {field("website", "Website", "url", false, "url")}
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <label htmlFor="message" className="text-sm font-medium" style={{ color: labelColor }}>
            Message <span className="text-xs ml-1" style={{ color: dark ? "#475569" : "#94A3B8" }}>(optional)</span>
          </label>
          <textarea
            id="message" name="message" rows={4} value={data.message} onChange={change}
            placeholder="Tell us about your team size, current lead volume, or what you're trying to solve…"
            className={`px-4 py-2.5 rounded-lg text-sm w-full resize-y transition-all duration-150 ${ph}`}
            style={inputStyle}
            onFocus={focusStyle}
            onBlur={(e) => blurStyle(e)}
          />
        </div>
      </div>

      {state === "error" && (
        <div className="mt-4 flex items-center gap-2 p-3 rounded-lg" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)" }} role="alert">
          <AlertCircle className="w-4 h-4 shrink-0" style={{ color: "#EF4444" }} />
          <p className="text-sm" style={{ color: "#FCA5A5" }}>Something went wrong. Please try again or email us directly.</p>
        </div>
      )}

      <button
        type="submit" disabled={state === "loading"}
        className="mt-6 w-full px-6 py-3.5 rounded-xl font-semibold text-white text-sm flex items-center justify-center gap-2 mk-btn-primary"
        style={{ opacity: state === "loading" ? 0.7 : 1, cursor: state === "loading" ? "not-allowed" : "pointer" }}
      >
        {state === "loading" && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />}
        {state === "loading" ? "Sending…" : "Send Message"}
      </button>
      <p className="mt-3 text-xs text-center" style={{ color: dark ? "#475569" : "#94A3B8" }}>
        We respond within one business day.
      </p>
    </form>
  );
}
