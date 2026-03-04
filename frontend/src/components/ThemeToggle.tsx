"use client";

import { useTheme } from "@/components/ThemeProvider";
import { Moon, Sun, Monitor } from "lucide-react";
import { useEffect, useState, useRef } from "react";
import { cn } from "@/lib/utils";

export function ThemeToggle() {
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = useState(false);
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Prevent hydration mismatch
    useEffect(() => {
        setMounted(true);
    }, []);

    // Close on click outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    if (!mounted) {
        return (
            <button className="p-2 rounded-full bg-slate-100/50 text-slate-400">
                <div className="w-5 h-5" />
            </button>
        );
    }

    const toggleDropdown = () => setIsOpen((prev) => !prev);

    // Resolve what icon to show based on system if set to system
    let currentIcon = theme === "dark" ? <Moon className="w-5 h-5 text-indigo-400" /> : <Sun className="w-5 h-5 text-amber-500" />;

    // If the theme is explicitly system, we can show a monitor, or deduce what the system currently is. We'll deduce.
    if (theme === "system") {
        const isSystemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        currentIcon = isSystemDark ? <Moon className="w-5 h-5 text-indigo-400" /> : <Sun className="w-5 h-5 text-amber-500" />;
    }

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={toggleDropdown}
                className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors border-transparent hover:border-slate-200 dark:hover:border-slate-700 border flex items-center justify-center focus:outline-none"
                aria-label="Toggle theme"
            >
                {currentIcon}
            </button>

            {isOpen && (
                <div className="absolute right-0 mt-2 w-36 bg-white dark:bg-slate-900 rounded-xl shadow-xl shadow-slate-200/50 dark:shadow-black/50 border border-slate-100 dark:border-slate-800 overflow-hidden z-50">
                    <div className="p-1">
                        <button
                            onClick={() => { setTheme("light"); setIsOpen(false); }}
                            className={cn(
                                "flex items-center gap-2 w-full px-3 py-2 text-sm font-medium rounded-lg transition-colors",
                                theme === "light"
                                    ? "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                                    : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-slate-200"
                            )}
                        >
                            <Sun className="w-4 h-4" /> Light
                        </button>
                        <button
                            onClick={() => { setTheme("dark"); setIsOpen(false); }}
                            className={cn(
                                "flex items-center gap-2 w-full px-3 py-2 text-sm font-medium rounded-lg transition-colors",
                                theme === "dark"
                                    ? "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                                    : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-slate-200"
                            )}
                        >
                            <Moon className="w-4 h-4" /> Dark
                        </button>
                        <button
                            onClick={() => { setTheme("system"); setIsOpen(false); }}
                            className={cn(
                                "flex items-center gap-2 w-full px-3 py-2 text-sm font-medium rounded-lg transition-colors",
                                theme === "system"
                                    ? "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                                    : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-slate-200"
                            )}
                        >
                            <Monitor className="w-4 h-4" /> System
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
