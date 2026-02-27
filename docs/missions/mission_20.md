# Mission 20 — Prompt Studio Knowledge Base v2 + Dynamic Lead Qualification Builder

## Summary

Mission 20 eliminates the three critical gaps in LeadPilot's AI pipeline:

1. **Knowledge files now flow into AI context** — uploaded documents (TXT, CSV, PDF) are extracted and injected into every AI conversation via the new prompt compiler.
2. **Single source of truth for prompt compilation** — `prompt_compiler.py` replaces two divergent context-assembly paths (Test Chat vs Runtime) with one canonical pipeline.
3. **Automation AI steps now use goal/tasks/extra_instructions** — the runtime passes step-level config through the compiler, so AI_REPLY nodes finally execute under the configured goals.
4. **Dynamic lead qualification** — workspace-level configurable questions + statuses with admin defaults/override.

## What Changed

### Backend

| File | Change |
|---|---|
| `app/models/models.py` | Added `sha256_hash` + `status` to `WorkspaceKnowledgeFile`; new `QualificationConfig` model |
| `alembic/versions/f6g7h8i9j0k1_...py` | Migration: 2 new columns + 1 new table |
| `app/api/v1/knowledge.py` | SHA256 dedupe, PDF extraction (PyMuPDF), workspace-isolated storage, download endpoint |
| `app/services/prompt_compiler.py` | **NEW** — single source of truth context compiler |
| `app/api/v1/test_chat.py` | Uses compiler instead of inline assembly |
| `app/domain/runtime.py` | Uses compiler with `step_config` for AI_REPLY |
| `app/api/v1/qualification.py` | **NEW** — GET/POST qualification config (lazy-create pattern) |
| `app/api/v1/admin.py` | 3 new endpoints: qualification defaults, workspace reset |
| `main.py` | Registered qualification router |

### Frontend

| File | Change |
|---|---|
| `prompt-studio/page.tsx` | 4th "Lead Qualification" tab with questions/statuses CRUD; Knowledge tab polished with status badges + download buttons |

### Tests

| File | Tests |
|---|---|
| `tests/test_knowledge.py` | 6 tests — upload, list, dedupe, delete, download, unsupported format |
| `tests/test_prompt_compiler.py` | 5 tests — all sections, step_config, exclude files, exclude qualification, no-config default |
| `tests/test_qualification.py` | 3 tests — lazy create, update + version increment, idempotent GET |

**Total: 118 tests passing (was 57 pre-mission)**

## Architecture: Prompt Compiler

```
compile_workspace_prompt(workspace_id, db, *, include_files, include_qualification, step_config)
    │
    ├── 1. system_prompt_text (from PromptVersion)
    ├── 2. === BUSINESS PROFILE === (business_profile_json)
    ├── 3. === GUARDRAILS === (guardrails_json)
    ├── 4. === KNOWLEDGE BASE (FILES) === (READY files, 4000 char cap each)
    ├── 5. === LEAD QUALIFICATION === (enabled questions sorted by order)
    └── 6. === STEP GOAL / TASKS / STEP INSTRUCTIONS === (if step_config provided)

Returns: CompiledPrompt(system_instruction, temperature, max_tokens, metadata)
```

Both Test Chat and Runtime AI_REPLY call this single function.

## New API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/qualification-config` | Get or lazy-create workspace qualification config |
| POST | `/api/v1/qualification-config` | Update questions + statuses, version auto-increments |
| GET | `/api/v1/knowledge/files/{id}/download` | Download knowledge file |
| GET | `/api/v1/admin/qualification-defaults` | Admin: get global defaults |
| PUT | `/api/v1/admin/qualification-defaults` | Admin: set global defaults |
| POST | `/api/v1/admin/workspaces/{id}/qualification-reset` | Admin: reset workspace to defaults |

## How to Test

1. **Backend tests**: `cd backend && rm -f test.db && python3 -m pytest tests/ -v`
2. **Frontend build**: `cd frontend && npm run build`
3. **Manual — Knowledge files**: Upload .txt in Prompt Studio Knowledge tab → open Test Chat → AI should reference file content
4. **Manual — Automation AI steps**: Create automation with AI_REPLY step goal "Schedule a demo" → trigger → AI should mention scheduling
5. **Manual — Qualification**: Edit questions in Lead Qualification tab → save → Test Chat AI should collect those specific details
