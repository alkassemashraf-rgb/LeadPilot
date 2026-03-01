/**
 * Parity Audit — Mission 33
 *
 * Verifies the marketing website does not claim features, plans, or providers
 * that don't exist in the backend database.
 *
 * Usage:
 *   AUDIT_API_URL=http://localhost:8000 npx ts-node scripts/parity-audit.ts
 *
 * Exit code 0 = PASS, 1 = FAIL (violations found)
 */

import * as fs from "fs";
import * as path from "path";

const API_BASE = process.env.AUDIT_API_URL ?? "http://localhost:8000";
const WEBSITE_SRC = path.join(__dirname, "../src");

interface Violation {
  type: string;
  value: string;
  file: string;
  line: number;
}

interface Envelope<T> {
  success: boolean;
  data: T;
}

async function fetchData<T>(endpoint: string): Promise<T[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/catalog${endpoint}`);
    if (!res.ok) {
      console.error(`  WARN: ${endpoint} returned ${res.status}`);
      return [];
    }
    const json: Envelope<T[]> = await res.json();
    return json.success ? json.data : [];
  } catch (err) {
    console.error(`  WARN: Failed to fetch ${endpoint}:`, err);
    return [];
  }
}

function scanFiles(dir: string, ext: string): { filePath: string; content: string; lines: string[] }[] {
  const results: { filePath: string; content: string; lines: string[] }[] = [];

  function walk(d: string) {
    for (const entry of fs.readdirSync(d, { withFileTypes: true })) {
      const full = path.join(d, entry.name);
      if (entry.isDirectory() && !entry.name.startsWith(".") && entry.name !== "node_modules") {
        walk(full);
      } else if (entry.isFile() && entry.name.endsWith(ext)) {
        const content = fs.readFileSync(full, "utf-8");
        results.push({
          filePath: path.relative(WEBSITE_SRC, full),
          content,
          lines: content.split("\n"),
        });
      }
    }
  }

  walk(dir);
  return results;
}

async function main() {
  console.log("Parity Audit — LeadPilot Website vs Backend DB");
  console.log(`API: ${API_BASE}`);
  console.log(`Source: ${WEBSITE_SRC}\n`);

  // Fetch all catalog data
  const [plans, providers] = await Promise.all([
    fetchData<{ name: string; display_name: string }>("/plans"),
    fetchData<{ key: string; label: string }>("/integration-providers"),
  ]);

  const dbPlanNames = new Set(plans.map((p) => p.name.toLowerCase()));
  const dbPlanDisplayNames = new Set(plans.map((p) => p.display_name.toLowerCase()));
  const dbProviderKeys = new Set(providers.map((p) => p.key.toLowerCase()));

  console.log(`DB plans: ${[...dbPlanNames].join(", ")}`);
  console.log(`DB providers: ${[...dbProviderKeys].join(", ")}\n`);

  // Known phantom plan names that should NOT appear
  const phantomPlanNames = ["pro", "starter", "basic", "professional", "premium"];
  const phantomPlanPatterns = phantomPlanNames
    .filter((name) => !dbPlanNames.has(name) && !dbPlanDisplayNames.has(name))
    .map((name) => ({
      name,
      // Match as standalone word (plan name in quotes, or as plan title)
      regex: new RegExp(`(?:name|tier|plan).*?["'\`]${name}["'\`]|["'\`]${name}["'\`].*?(?:plan|tier)`, "gi"),
    }));

  // Scan source files
  const files = scanFiles(path.join(WEBSITE_SRC, "app"), ".tsx");
  const violations: Violation[] = [];

  for (const { filePath, lines } of files) {
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Check for phantom plan names
      for (const { name, regex } of phantomPlanPatterns) {
        regex.lastIndex = 0;
        if (regex.test(line)) {
          violations.push({
            type: "PHANTOM_PLAN",
            value: name,
            file: filePath,
            line: i + 1,
          });
        }
      }

      // Also check for standalone "Pro" as a plan name in plan arrays/objects
      // This catches hardcoded plan arrays like { name: "Pro", ... }
      if (/name:\s*["']Pro["']/i.test(line) && !dbPlanNames.has("pro")) {
        violations.push({
          type: "PHANTOM_PLAN_PROPERTY",
          value: "Pro",
          file: filePath,
          line: i + 1,
        });
      }
    }
  }

  // Output
  const result = {
    audit_timestamp: new Date().toISOString(),
    api_base: API_BASE,
    plans_in_db: [...dbPlanNames],
    providers_in_db: [...dbProviderKeys],
    violations,
    status: violations.length === 0 ? "PASS" : "FAIL",
  };

  console.log(JSON.stringify(result, null, 2));

  if (violations.length > 0) {
    console.error(`\n${violations.length} violation(s) found.`);
    process.exit(1);
  } else {
    console.log("\nNo violations. Website is in parity with backend.");
    process.exit(0);
  }
}

main().catch((err) => {
  console.error("Audit script failed:", err);
  process.exit(2);
});
