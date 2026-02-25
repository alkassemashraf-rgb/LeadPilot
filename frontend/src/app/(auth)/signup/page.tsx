"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";

export default function SignupPage() {
    const router = useRouter();
    const [formData, setFormData] = useState({
        fullName: "",
        email: "",
        password: "",
        confirmPassword: "",
    });
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        // Validation
        if (formData.password.length < 8) {
            setError("Password must be at least 8 characters long.");
            setIsLoading(false);
            return;
        }

        if (formData.password !== formData.confirmPassword) {
            setError("Passwords do not match.");
            setIsLoading(false);
            return;
        }

        try {
            const response = await apiClient.post("/auth/signup", {
                full_name: formData.fullName,
                email: formData.email,
                password: formData.password,
            });

            if (response.success) {
                setSuccess(true);
                // Redirect to login after a short delay
                setTimeout(() => router.push("/login"), 3000);
            } else {
                setError(response.error || "Failed to create account. Please try again.");
            }
        } catch (err: any) {
            setError("An unexpected error occurred. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleGoogleLogin = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await apiClient.get("/auth/google/start");
            if (response.success && response.data?.auth_url) {
                window.location.href = response.data.auth_url;
            } else {
                setError(response.error || "Failed to start Google login");
            }
        } catch (err: any) {
            setError("Could not initialize Google login. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    if (success) {
        return (
            <div className="text-center space-y-4">
                <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
                    <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                    </svg>
                </div>
                <h2 className="text-xl font-semibold text-[#334155]">Account created!</h2>
                <p className="text-sm text-[#64748B]">
                    Your account has been successfully created. Redirecting to login...
                </p>
                <Link href="/login" className="text-sm font-medium text-[#0F766E] hover:text-[#14B8A6]">
                    Click here if you're not redirected
                </Link>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-xl font-semibold text-[#334155]">Create an account</h2>
                <p className="text-sm text-[#64748B]">Get started with LeadPilot today</p>
            </div>

            <div className="space-y-4">
                <button
                    onClick={handleGoogleLogin}
                    disabled={isLoading}
                    className="w-full flex items-center justify-center gap-3 py-2 px-4 border border-[#E2E8F0] rounded-md shadow-sm bg-white text-sm font-medium text-[#334155] hover:bg-[#F8FAFC] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#14B8A6] disabled:opacity-50 transition-colors"
                >
                    <svg className="h-5 w-5" viewBox="0 0 24 24">
                        <path
                            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                            fill="#4285F4"
                        />
                        <path
                            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                            fill="#34A853"
                        />
                        <path
                            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
                            fill="#FBBC05"
                        />
                        <path
                            d="M12 5.38c1.62 0 3.06.56 4.21 1.66l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                            fill="#EA4335"
                        />
                        <path d="M1 1h22v22H1z" fill="none" />
                    </svg>
                    Continue with Google
                </button>

                <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                        <div className="w-full border-t border-[#E2E8F0]"></div>
                    </div>
                    <div className="relative flex justify-center text-sm">
                        <span className="px-2 bg-white text-[#64748B]">or continue with email</span>
                    </div>
                </div>
            </div>

            <form className="space-y-4" onSubmit={handleSubmit}>
                {error && (
                    <div className="bg-red-50 border-l-4 border-red-400 p-4 rounded">
                        <p className="text-sm text-red-700">{error}</p>
                    </div>
                )}

                <div>
                    <label htmlFor="fullName" className="block text-sm font-medium text-[#334155]">
                        Full name
                    </label>
                    <div className="mt-1">
                        <input
                            id="fullName"
                            name="fullName"
                            type="text"
                            required
                            value={formData.fullName}
                            onChange={handleChange}
                            className="appearance-none block w-full px-3 py-2 border border-[#E2E8F0] rounded-md shadow-sm placeholder-[#94A3B8] focus:outline-none focus:ring-[#14B8A6] focus:border-[#14B8A6] sm:text-sm text-[#334155]"
                        />
                    </div>
                </div>

                <div>
                    <label htmlFor="email" className="block text-sm font-medium text-[#334155]">
                        Email address
                    </label>
                    <div className="mt-1">
                        <input
                            id="email"
                            name="email"
                            type="email"
                            autoComplete="email"
                            required
                            value={formData.email}
                            onChange={handleChange}
                            className="appearance-none block w-full px-3 py-2 border border-[#E2E8F0] rounded-md shadow-sm placeholder-[#94A3B8] focus:outline-none focus:ring-[#14B8A6] focus:border-[#14B8A6] sm:text-sm text-[#334155]"
                        />
                    </div>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                        <label htmlFor="password" className="block text-sm font-medium text-[#334155]">
                            Password
                        </label>
                        <div className="mt-1">
                            <input
                                id="password"
                                name="password"
                                type="password"
                                autoComplete="new-password"
                                required
                                value={formData.password}
                                onChange={handleChange}
                                className="appearance-none block w-full px-3 py-2 border border-[#E2E8F0] rounded-md shadow-sm placeholder-[#94A3B8] focus:outline-none focus:ring-[#14B8A6] focus:border-[#14B8A6] sm:text-sm text-[#334155]"
                            />
                        </div>
                    </div>

                    <div>
                        <label htmlFor="confirmPassword" className="block text-sm font-medium text-[#334155]">
                            Confirm password
                        </label>
                        <div className="mt-1">
                            <input
                                id="confirmPassword"
                                name="confirmPassword"
                                type="password"
                                autoComplete="new-password"
                                required
                                value={formData.confirmPassword}
                                onChange={handleChange}
                                className="appearance-none block w-full px-3 py-2 border border-[#E2E8F0] rounded-md shadow-sm placeholder-[#94A3B8] focus:outline-none focus:ring-[#14B8A6] focus:border-[#14B8A6] sm:text-sm text-[#334155]"
                            />
                        </div>
                    </div>
                </div>

                <div>
                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#0F766E] hover:bg-[#14B8A6] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0F766E] disabled:opacity-50 transition-colors"
                    >
                        {isLoading ? "Creating account..." : "Create account"}
                    </button>
                </div>
            </form>

            <div className="mt-6 text-center">
                <p className="text-sm text-[#64748B]">
                    Already have an account?{" "}
                    <Link href="/login" className="font-medium text-[#0F766E] hover:text-[#14B8A6]">
                        Sign in
                    </Link>
                </p>
            </div>
        </div>
    );
}
