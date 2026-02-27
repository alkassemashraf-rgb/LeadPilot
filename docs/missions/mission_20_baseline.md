# Mission 20 — Pre-Mission Baseline

Captured before any Mission 20 changes.

## State of AI Context Compilation

### Test Chat (`test_chat.py:101-116`)
```python
# Fetched PromptConfig + PromptVersion manually
# Built system instruction as: system_prompt_text + json.dumps(business_profile_json) + json.dumps(guardrails_json)
# Knowledge files: NOT included
# Qualification: NOT included
# Step config: N/A
```

### Runtime AI_REPLY (`runtime.py:285-333`)
```python
# Built system instruction as: system_prompt_text + "Business Context:" + business_profile_json
# Guardrails: NOT included
# Knowledge files: NOT included
# Qualification: NOT included
# Step config (goal/tasks/extra_instructions): NOT read despite being stored in definition_json
```

**Result**: Two divergent prompts from the same config. Knowledge files uploaded but never used. Automation goals collected but ignored.

## Knowledge Files

- `WorkspaceKnowledgeFile` model existed with `extracted_text` field
- Upload endpoint extracted text for .txt, .md, .json, .csv
- No PDF support
- No SHA256 dedupe
- No download endpoint
- No status tracking (READY/FAILED)
- Storage path: flat `storage/knowledge/{uuid}{ext}` (not workspace-isolated)

## Qualification

- Hardcoded checkboxes in Prompt Studio editor tab: "Full Name", "Company Email", "Budget Range", etc.
- Stored as `required_details[]` in structured_data form
- No `QualificationConfig` model
- No admin defaults/override
- No qualification statuses

## Prompt Studio Frontend

- 3 tabs: Assistant Configuration, Knowledge Base, Version History
- Knowledge tab: upload/delete only, no status indicators
- No qualification management tab

## Test Count

57 tests across 13 files, all passing.
