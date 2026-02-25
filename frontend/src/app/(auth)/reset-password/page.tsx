"use client"

import { useState, Suspense } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import Link from "next/link"
import { apiClient } from "@/lib/api"

function ResetPasswordForm() {
    const searchParams = useSearchParams()
    const token = searchParams.get("token")
    const router = useRouter()

    const [password, setPassword] = useState("")
    const [confirmPassword, setConfirmPassword] = useState("")
    const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")
    const [message, setMessage] = useState("")

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setStatus("loading")
        setMessage("")

        if (password !== confirmPassword) {
            setStatus("error")
            setMessage("Passwords do not match")
            return
        }

        if (!token) {
            setStatus("error")
            setMessage("Invalid or missing reset token")
            return
        }

        try {
            const result = await apiClient.post("/auth/reset-password", { token, new_password: password })

            if (result.success) {
                setStatus("success")
                setMessage("Password reset successfully. You can now login.")
            } else {
                setStatus("error")
                setMessage(result.error || "Failed to reset password.")
            }
        } catch (err) {
            setStatus("error")
            setMessage("Failed to connect to the server.")
        }
    }

    if (!token) {
        return (
            <div className="text-center">
                <h2 className="text-xl font-bold text-red-600">Invalid Link</h2>
                <p className="mt-2 text-gray-600">This password reset link is invalid or has expired.</p>
                <Link href="/forgot-password" className="mt-4 inline-block text-indigo-600 hover:text-indigo-500">
                    Request a new link
                </Link>
            </div>
        )
    }

    return (
        <>
            <div>
                <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
                    Set new password
                </h2>
            </div>

            {status === "success" ? (
                <div className="rounded-md bg-green-50 p-4 mt-8">
                    <div className="flex">
                        <div className="ml-3">
                            <h3 className="text-sm font-medium text-green-800">Success</h3>
                            <div className="mt-2 text-sm text-green-700">
                                <p>{message}</p>
                            </div>
                            <div className="mt-4">
                                <div className="-mx-2 -my-1.5 flex">
                                    <Link
                                        href="/login"
                                        className="rounded-md bg-green-50 px-2 py-1.5 text-sm font-medium text-green-800 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-green-600 focus:ring-offset-2 focus:ring-offset-green-50"
                                    >
                                        Go to Login
                                    </Link>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
                    <div className="-space-y-px rounded-md shadow-sm">
                        <div>
                            <label htmlFor="password" className="sr-only">
                                New Password
                            </label>
                            <input
                                id="password"
                                name="password"
                                type="password"
                                required
                                className="relative block w-full rounded-t-md border-0 py-1.5 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:z-10 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6 pl-2"
                                placeholder="New Password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                        </div>
                        <div>
                            <label htmlFor="confirm-password" className="sr-only">
                                Confirm Password
                            </label>
                            <input
                                id="confirm-password"
                                name="confirm-password"
                                type="password"
                                required
                                className="relative block w-full rounded-b-md border-0 py-1.5 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:z-10 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6 pl-2"
                                placeholder="Confirm Password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                            />
                        </div>
                    </div>

                    {status === "error" && (
                        <div className="text-sm text-red-600 text-center">{message}</div>
                    )}

                    <div>
                        <button
                            type="submit"
                            disabled={status === "loading"}
                            className="group relative flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50"
                        >
                            {status === "loading" ? "Resetting..." : "Reset Password"}
                        </button>
                    </div>
                </form>
            )}
        </>
    )
}

export default function ResetPasswordPage() {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
            <div className="w-full max-w-md space-y-8">
                <Suspense fallback={<div>Loading...</div>}>
                    <ResetPasswordForm />
                </Suspense>
            </div>
        </div>
    )
}
