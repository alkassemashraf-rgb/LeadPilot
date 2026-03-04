"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

type Theme = "dark" | "light" | "system";

type ThemeProviderProps = {
    children: React.ReactNode;
    defaultTheme?: Theme;
    storageKey?: string;
};

type ThemeProviderState = {
    theme: Theme;
    setTheme: (theme: Theme) => void;
};

const initialState: ThemeProviderState = {
    theme: "system",
    setTheme: () => null,
};

const ThemeProviderContext = createContext<ThemeProviderState>(initialState);

export function DashboardThemeProvider({
    children,
    defaultTheme = "system",
    storageKey = "leadpilot-ui-theme",
    ...props
}: ThemeProviderProps) {
    const [theme, setTheme] = useState<Theme>(defaultTheme);
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        const savedTheme = localStorage.getItem(storageKey) as Theme;
        if (savedTheme) {
            setTheme(savedTheme);
        }
    }, [storageKey]);

    useEffect(() => {
        if (!mounted) return;

        const root = window.document.documentElement;

        // Remove class from root if it was set globally, we want to isolate it
        root.classList.remove("dark");

        if (theme === "system") {
            const systemTheme = window.matchMedia("(prefers-color-scheme: dark)")
                .matches
                ? "dark"
                : "light";

            // Only update local state, not the DOM global class
        }

        // Actually save the preference
        localStorage.setItem(storageKey, theme);
    }, [theme, mounted, storageKey]);

    const value = {
        theme,
        setTheme: (theme: Theme) => {
            setTheme(theme);
        },
    };

    // Determine actual resolved theme to apply the class to the wrapper wrapper
    let resolvedTheme = theme;
    if (theme === "system" && mounted) {
        resolvedTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }

    // Wrap the children in a div that toggles the "dark" class.
    return (
        <ThemeProviderContext.Provider {...props} value={value}>
            <div className={resolvedTheme === "dark" ? "dark" : ""}>
                <div className="min-h-screen bg-background text-foreground transition-colors duration-200">
                    {children}
                </div>
            </div>
        </ThemeProviderContext.Provider>
    );
}

export const useTheme = () => {
    const context = useContext(ThemeProviderContext);

    if (context === undefined)
        throw new Error("useTheme must be used within a DashboardThemeProvider");

    return context;
};
