"use client";

/**
 * LookupsProvider — Mission 21
 * Fetches all catalog lookups on mount and provides them via React context.
 * Product dashboard pages consume via useLookups() hook.
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchCatalog, type CatalogEntry } from "./catalog";

export interface Lookups {
    timezones: CatalogEntry[];
    languages: CatalogEntry[];
    aiModels: CatalogEntry[];
    dedupeStrategies: CatalogEntry[];
    eventSources: CatalogEntry[];
    eventOutcomes: CatalogEntry[];
    auditActions: CatalogEntry[];
    contactFields: CatalogEntry[];
    triggerTypes: CatalogEntry[];
    nodeTypes: CatalogEntry[];
    loading: boolean;
}

const defaultLookups: Lookups = {
    timezones: [],
    languages: [],
    aiModels: [],
    dedupeStrategies: [],
    eventSources: [],
    eventOutcomes: [],
    auditActions: [],
    contactFields: [],
    triggerTypes: [],
    nodeTypes: [],
    loading: true,
};

const LookupsContext = createContext<Lookups>(defaultLookups);

export function LookupsProvider({ children }: { children: ReactNode }) {
    const [lookups, setLookups] = useState<Lookups>(defaultLookups);

    useEffect(() => {
        Promise.all([
            fetchCatalog("timezones").catch(() => []),
            fetchCatalog("languages").catch(() => []),
            fetchCatalog("ai-models").catch(() => []),
            fetchCatalog("dedupe-strategies").catch(() => []),
            fetchCatalog("event-sources").catch(() => []),
            fetchCatalog("event-outcomes").catch(() => []),
            fetchCatalog("audit-actions").catch(() => []),
            fetchCatalog("contact-fields").catch(() => []),
            fetchCatalog("automation-trigger-types").catch(() => []),
            fetchCatalog("automation-node-types").catch(() => []),
        ]).then(([
            timezones, languages, aiModels, dedupeStrategies,
            eventSources, eventOutcomes, auditActions, contactFields,
            triggerTypes, nodeTypes,
        ]) => {
            setLookups({
                timezones,
                languages,
                aiModels,
                dedupeStrategies,
                eventSources,
                eventOutcomes,
                auditActions,
                contactFields,
                triggerTypes,
                nodeTypes,
                loading: false,
            });
        });
    }, []);

    return (
        <LookupsContext.Provider value={lookups}>
            {children}
        </LookupsContext.Provider>
    );
}

export function useLookups(): Lookups {
    return useContext(LookupsContext);
}
