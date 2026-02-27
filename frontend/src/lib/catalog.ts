/**
 * Catalog client — Mission 19
 * Provides a useCatalog() hook that fetches and caches catalog data.
 * Uses the product apiClient (no auth required for catalog endpoints).
 */
import { useState, useEffect, useCallback } from "react";
import { apiClient, type ApiResponse } from "./api";

// ── Types ────────────────────────────────────────────────────────────

export interface CatalogEntry {
  key: string;
  label: string;
  description?: string;
  [extra: string]: any;
}

export interface PlanCatalogEntry {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  sort_order: number;
  entitlements: { module_key: string; hard_limit: number | null }[];
}

export type CatalogKey =
  | "plans"
  | "tiers"
  | "modules"
  | "workspace-roles"
  | "admin-roles"
  | "integration-providers"
  | "automation-node-types"
  | "automation-trigger-types"
  | "conversation-statuses"
  | "message-delivery-statuses";

// ── Cache ────────────────────────────────────────────────────────────

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

const CACHE_TTL_MS = 60_000;
const cache = new Map<string, CacheEntry<unknown>>();

function getCached<T>(key: string): T | null {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
    cache.delete(key);
    return null;
  }
  return entry.data as T;
}

function setCache<T>(key: string, data: T): void {
  cache.set(key, { data, timestamp: Date.now() });
}

// ── Fetch ────────────────────────────────────────────────────────────

async function fetchCatalog<T = CatalogEntry[]>(key: CatalogKey): Promise<T> {
  const cached = getCached<T>(key);
  if (cached !== null) return cached;

  const res: ApiResponse<T> = await apiClient.get<T>(`/catalog/${key}`);
  if (res.success && res.data) {
    setCache(key, res.data);
    return res.data;
  }
  throw new Error(res.error || `Failed to fetch catalog: ${key}`);
}

// ── Hook ─────────────────────────────────────────────────────────────

export interface UseCatalogResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useCatalog<T = CatalogEntry[]>(
  key: CatalogKey
): UseCatalogResult<T> {
  const [data, setData] = useState<T | null>(() => getCached<T>(key));
  const [loading, setLoading] = useState<boolean>(data === null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchCatalog<T>(key)
      .then((result) => {
        setData(result);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Catalog fetch failed");
        setLoading(false);
      });
  }, [key]);

  useEffect(() => {
    if (data !== null) {
      setLoading(false);
      return;
    }
    load();
  }, [key, load, data]);

  return { data, loading, error, refetch: load };
}

// ── Helpers ──────────────────────────────────────────────────────────

export function catalogLookup(
  items: CatalogEntry[] | null,
  key: string
): CatalogEntry | undefined {
  return items?.find((item) => item.key === key);
}

export function catalogLabel(
  items: CatalogEntry[] | null,
  key: string,
  fallback?: string
): string {
  return catalogLookup(items, key)?.label ?? fallback ?? key;
}
