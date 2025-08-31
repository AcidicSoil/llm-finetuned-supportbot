# Agents Instructions (Ordered)

- Project: \${PROJECT\_TAG}
- Purpose: Canonical instruction list. Do not append logs here.

---

## Instruction Layering & Extensions

- **Baseline:** This file (**AGENTS.md**) is the canonical baseline for all assistant behavior.
- **Extensions:** Additional instruction files may be layered in using a **dedicated extension tag** (see below). Plain `@{...}` remains **context-only** and does **not** change behavior.

### Tagging Syntax (context vs. extensions)

**Context tag — `@{file}` (no behavior change)**

- Purpose: Include files in retrieval/context only (e.g., for grounding, examples, specs). *Does not* add rules.
- Syntax: `@{path/to/file.md}` (absolute or relative to repo root). Globs allowed, e.g., `@{docs/*.md}`.
- Order: Irrelevant for behavior; these are not layered.

**Extension tag — `@ext{file}` (adds rules)**

- Purpose: Declare instruction **Extensions** that layer on top of **AGENTS.md**.
- Syntax: `@ext{path/to/instruction.md}`. Globs allowed: `@ext{docs/roles/*.md}`.
- Multiple allowed and **ordered** left → right: `@ext{prd_generator.md} @ext{guardrails.md}`.
- Inline comments are ignored after either tag form: `@ext{ops_playbook.md}  # ops guidance`.

### Resolution & Loading

1. Resolve each tag to a file path:

   - Prefer repo root; if not found, try relative to the caller’s cwd.
   - Expand globs to a **lexicographically sorted** file list.
2. Treat each **`@ext{...}`** file as an **Extension** layered on **AGENTS.md**:

   - **Baseline** = AGENTS.md
   - **Extension** = tagged file’s instructions, scoped to its role/task
   - **Conflict rule** = The more specific **extension** wins within its scope; otherwise baseline holds.
   - **File validity rule**: Instruction files must either (a) live under `instructions/` or (b) end with `.instr.md` to be valid for `@ext{...}`.
3. **Order of precedence** (only among extensions): left-to-right; when two extensions conflict in the same scope, the **rightmost** wins.
4. Files tagged via plain **`@{...}`** are **context-only** and never contribute instructions.

### Example Usage

- Context only:

  - `codex-cli run "Analyze these examples @{examples/*.md}"`
- Single extension:

  - `codex-cli run "Draft a PRD for X @ext{prd_generator.md}"`
- Multiple extensions (ordered):

  - `codex-cli run "Harden auth flow @ext{security/guardrails.md} @ext{framework/fastapi.md}"`
- Mixed (context + extensions):

  - `codex-cli run "Prepare release notes @{changelog.md} @ext{docs/release/notes_template.md}"`

### Execution Flow (Docs Integration)

- **Preflight (§A)** must include **both** context (`@{...}`) and extension (`@ext{...}`) files in the retrieval coverage set and list them in `DocFetchReport.sources`.
- **Compose instructions**

  1. Apply AGENTS.md (baseline)
  2. Layer **only** the `@ext{...}` extensions (left → right)
  3. Resolve conflicts per rules above
- Proceed only when `DocFetchReport.status == "OK"` (Decision Gate §B).

### Failure Handling

- If any `@ext{...}` file cannot be resolved:

  - **Do not finalize.** Return a minimal “Docs Missing” plan listing the missing paths and suggested fix.
- If a `@{...}` context file cannot be resolved:

  - Continue, but record it under `DocFetchReport.gaps.context_missing[]` with the attempted providers; suggest a fix in the plan section.

### DocFetchReport Addendum

When tags are used, add:

```json
{
  "DocFetchReport": {
    "tagged_extensions": [
      {"path": "prd_generator.md", "loaded": true},
      {"path": "security/guardrails.md", "loaded": true}
    ],
    "tagged_context": [
      {"path": "changelog.md", "loaded": true}
    ]
  }
}
```

---

## A) Preflight: Latest Docs Requirement (**MUST**, Blocking)

**Goal:** Ensure the assistant retrieves and considers the *latest relevant docs* before planning, acting, or finalizing.

**Providers Whitelist & Order (strict):**

1. **docfork mcp** (primary)
2. **gitmcp** (fallback if docfork fails or is unavailable)
3. **exa** (targeted web search; use only for **official docs** or primary sources when the first two do not cover the topic)

> **Policy:** Prefer canonical docs and source-of-truth references. When using **exa**, restrict to official documentation, standards, or the project’s source repositories. Record exact URLs and versions/commits.

**What to do:**

- For every task that could touch code, configuration, APIs, tooling, or libraries:

  - Call **docfork mcp** to fetch the latest documentation or guides.
  - If the call **fails** (error, unavailable, or insufficient coverage), retry with **gitmcp**; if that also **fails or is insufficient**, use **exa** to retrieve official docs.
- Each successful call **MUST** capture:

  - Tool name, query/topic, retrieval timestamp (UTC), and source refs/URLs (or repo refs/commits).
- Scope:

  - Fetch docs for each **area to be touched** (framework, library, CLI, infra, etc.).
  - Prefer focused topics (e.g., "exception handlers", "lifespan", "retry policy", "sqlite schema").

**Failure handling:**

- If **all** providers above fail to produce adequate coverage for a required area, **do not finalize**. Return a minimal plan that includes:

  - The attempted providers and errors
  - The specific topics/areas still uncovered
  - A safe, read-only analysis and suggested next checks (or user confirmation).

**Proof-of-Work Artifact (required):**

- Produce and attach a `DocFetchReport` (JSON) with `status`, `tools_called[]`, `sources[]`, `coverage`, `key_guidance[]`, `gaps`, and `informed_changes[]`.
- Example schema:

```json
{
  "DocFetchReport": {
    "status": "OK | PARTIAL | FAILED",
    "tools_called": [
      {"name": "docfork|gitmcp|exa", "time_utc": "<ISO8601>", "query": "<topic/ids>"}
    ],
    "sources": [
      {"url_or_ref": "<doc url or repo ref>", "kind": "api|guide|spec|code", "commit_or_version": "<hash|tag|n/a>"}
    ],
    "coverage": "Which parts of the task these sources cover.",
    "key_guidance": [
      "Short bullets of the exact rules/APIs that constrain the change."
    ],
    "gaps": "Anything still unknown.",
    "informed_changes": ["files or commands to be touched, mapped to guidance"]
  }
}
```

**Override Path (explicit, logged):**

- Allowed for outages/ambiguous scope/timeboxed spikes. Must include:

```json
{
  "Override": {
    "reason": "server_down|ambiguous_scope|timeboxed_spike",
    "risk_mitigation": ["read-only analysis", "scoped PoC", "user confirmation required"],
    "expires_after": "1 action or 30m",
    "requested_by": "system|user"
  }
}
```

---

## A.1) Tech & Language Identification (Pre-Requirement)

- Before running Preflight (§A), the assistant must determine both:

  1. The **primary language(s)** used in the project (e.g., Python, TypeScript, Pytest, Bash).
  2. The **current project’s tech stack** (frameworks, libraries, infra, tools).

- Sources to infer language/stack:

  - Project tags (`${PROJECT_TAG}`), mem0 checkpoints, prior completion records.
  - Files present in repo (e.g., `pyproject.toml`, `requirements.txt`, `package.json`, `tsconfig.json`, `Dockerfile`, CI configs).
  - File extensions in repo (`.py`, `.ts`, `.js`, `.sh`, `.sql`, etc.).
  - User/task context (explicit mentions of frameworks, CLIs, infra).

- Doc retrieval (§A) **must cover each identified language and stack element** that will be touched by the task.

- Record both in the `DocFetchReport`:

```json
"tech_stack": ["fastapi", "httpx", "sqlite3", "pytest-asyncio"],
"languages": ["python", "pytest"]
```

---

## B) Decision Gate: No Finalize Without Proof (**MUST**)

- The assistant **MUST NOT**: finalize, apply diffs, modify files, or deliver a definitive answer **unless** `DocFetchReport.status == "OK"`.
- The planner/executor must verify `ctx.docs_ready == true` (set when at least one successful docs call exists **per required area**).
- If `status != OK` or `ctx.docs_ready != true`:

  - Stop. Return a **Docs Missing** message that lists the exact MCP calls and topics to run.

---

## 0) Debugging

- **Use consolidated docs-first flow** before touching any files or finalizing:

  - Try **docfork mcp** → if fail, **gitmcp** → if fail or insufficient, **exa** (official docs only).
  - Record results in `DocFetchReport`.

## 1) Startup memory bootstrap (mem0)

- On chat/session start: **mem0**
- Retrieve (project-scoped):

  - **mem0** → latest `memory_checkpoints` and recent task completions.
- Read/write rules:

  - On task completion write checkpoints to **mem0**.

## 2) On task completion (status → done)

- Write a concise completion memory to mem0 including:

  - `task_id`, `title`, `status`, `next step`
  - Files touched
  - Commit/PR link (if applicable)
  - Test results (if applicable)
- Seed/Update the knowledge graph (mcp-think-tank):

  - If this is a **new project** (detected auto-skip in §1), **create a seed node** `project:${PROJECT_TAG}` and initial edges:

    - `project:${PROJECT_TAG}` —\[owns]→ `task:${task_id}`
    - `task:${task_id}` —\[touches]→ `file:<path>`
    - `task:${task_id}` —\[status]→ `<status>`
  - Else, upsert edges for who/what/why/depends-on and recent changes.
- Do **NOT** write to `AGENTS.md` beyond these standing instructions.

## 3) Status management

- Use Task Master MCP to set task status (e.g., set to "in-progress" when starting).

## 4) Tagging for retrieval

- Use tags: `${PROJECT_TAG}`, `project:${PROJECT_TAG}`, `memory_checkpoint`, `completion`, `agents`, `routine`, `instructions`, plus task-specific tags (e.g., `fastapi`, `env-vars`).

## 5) Handling user requests for code or docs

- When a task or a user requires **code**, **setup/config**, or **library/API documentation**:

  - **MUST** run the **Preflight** (§A) using the provider order (docfork → gitmcp → exa).
  - Only proceed to produce diffs or create files after `DocFetchReport.status == "OK"`.

## 6) Handling Pydantic-specific questions

- For **ANY** question about **Pydantic**, use the **pydantic-docs-mcp** server:

  - Call `list_doc_sources` to retrieve `llms.txt`.
  - Call `fetch_docs` to read it and any linked URLs relevant to the question.
  - Reflect on the docs and the question.
  - Use this to answer, citing guidance in `DocFetchReport.key_guidance`.

## 7) Project tech stack specifics

- For project-specific stack work (FastAPI, Starlette, httpx, respx, pydantic-settings, pytest-asyncio, sqlite3, etc.):

  - **MUST** run the **Preflight** (§A) with the provider order above.
  - If a library isn’t found or coverage is weak after **docfork → gitmcp**, use **exa** to target official docs or repo sources; if still inadequate, **stop and return a Docs Missing report**. You may invoke the **Override Path** if justified and approved.

## 8) Library docs retrieval (topic-focused)

- Use **docfork mcp** first to fetch current docs before code changes.
- If docfork fails or is insufficient, use **gitmcp** (repo docs/source) to retrieve equivalents.
- If gitmcp is insufficient, use **exa** to query official docs with focused topics (e.g., "exception handlers", "lifespan", "request/response", "async client", "retry", "mocking", "markers", "sqlite schema/init").
- Summarize key guidance inline in `DocFetchReport.key_guidance` and map each planned change to a guidance line.
- Always note in the task preamble which providers/topics were used.

---

### System-prompt scaffold (enforcement)

```
SYSTEM: You operate under a blocking docs-first policy.
1) Preflight (§A):
   - Call docfork → gitmcp → exa (official docs only) as needed.
   - Build DocFetchReport (status must be OK).
2) Planning:
   - Map each planned change to key_guidance items in DocFetchReport.
3) Decision Gate (§B):
   - If DocFetchReport.status != OK → STOP and return "Docs Missing" with exact MCP calls.
4) Execution:
   - Proceed only if ctx.docs_ready == true.
5) Completion:
   - Attach DocFetchReport and write completion memory (§2).
```

---

*End of file.*
