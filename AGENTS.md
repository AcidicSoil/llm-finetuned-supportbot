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

### MCP Servers & Aliases (runtime)

- **mem0** — free-form checkpoints & notes (alias: `mem0`)
- **Knowledge Graph** — structured entities/relations/observations (alias: `knowledge-graph-mcp`)

  - Primary ops: `create_entities`, `create_relations`, `add_observations`, `read_graph`, `search_nodes`
  - Namespace: `project:${PROJECT_TAG}`

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
    ],
    "kg_ops": [
      {"tool": "knowledge-graph-mcp", "op": "create_entities|create_relations|add_observations|read_graph|search_nodes", "time_utc": "<ISO8601>", "scope": "project:${PROJECT_TAG}"}
    ]
  }
}
```

---

## A) Preflight: Latest Docs Requirement (**MUST**, Blocking)

**Goal:** Ensure the assistant retrieves and considers the *latest relevant docs* before planning, acting, or finalizing.

**Primary/Fallback Order (consolidated):**

1. **sourcebot** (primary)
2. **contex7-mcp** (fallback if sourcebot fails)
3. **gitmcp** (last-resort fallback if both above fail)

**What to do:**

- For every task that could touch code, configuration, APIs, tooling, or libraries:

  - Call **sourcebot** to fetch the latest documentation or guides.
  - If the call **fails**, immediately retry with **contex7-mcp**; if that also **fails**, retry with **gitmcp**.
- Each successful call **MUST** capture:

  - Tool name, query/topic, retrieval timestamp (UTC), and source refs/URLs (or repo refs/commits).
- Scope:

  - Fetch docs for each **area to be touched** (framework, library, CLI, infra, etc.).
  - Prefer focused topics (e.g., "exception handlers", "lifespan", "retry policy", "sqlite schema").

**Failure handling:**

- If **all** three providers fail for a required area, **do not finalize**. Return a minimal plan that includes:

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
      {"name": "sourcebot|contex7-mcp|gitmcp", "time_utc": "<ISO8601>", "query": "<topic/ids>"}
    ],
    "sources": [
      {"url_or_ref": "<doc url or repo ref>", "kind": "api|guide|code|spec", "commit_or_version": "<hash|tag|n/a>"}
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

- Allowed only for outages/ambiguous scope/timeboxed spikes. Must include:

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

  - Try **sourcebot** → if fail, **contex7-mcp** → if fail, **gitmcp**.
  - Record results in `DocFetchReport`.

## 1) Startup memory bootstrap (mem0 + KG-MCP)

- On chat/session start: initialize **mem0** and the **Knowledge Graph MCP (KG-MCP)**.
- Retrieve (project-scoped):

  - **mem0** → latest `memory_checkpoints` and recent task completions.
  - **KG-MCP** → ensure a graph namespace exists for this project and load prior nodes/edges.

    - **Server alias**: `knowledge-graph-mcp` (e.g., Smithery "Knowledge Graph Memory Server" such as `@jlia0/servers`).
    - **Bootstrap ops** (idempotent):

      - `create_entities` (or `upsert_entities`) for: `project:${PROJECT_TAG}`.
      - `create_relations` to link existing tasks/files if present.
      - `read_graph` / `search_nodes` to hydrate working context.
- Read/write rules:

  - Prefer **mem0** for free-form notes and checkpoints.
  - Prefer **KG-MCP** for **structured** facts/relations (entities, edges, observations).
  - If KG-MCP is unavailable, continue with mem0 and record `kg_unavailable: true` in the session preamble.

## 2) On task completion (status → done)

- Write a concise completion memory to mem0 including:

  - `task_id`, `title`, `status`, `next step`
  - Files touched
  - Commit/PR link (if applicable)
  - Test results (if applicable)
- **Update the Knowledge Graph (KG-MCP)**:

  - Ensure base entity `project:${PROJECT_TAG}` exists.
  - Upsert `task:${task_id}` and any `file:<path>` entities touched.
  - Create/refresh relations:

    - `project:${PROJECT_TAG}` —\[owns]→ `task:${task_id}`
    - `task:${task_id}` —\[touches]→ `file:<path>`
    - `task:${task_id}` —\[status]→ `<status>`
    - Optional: `task:${task_id}` —\[depends\_on]→ `<entity>`
  - Attach `observations` capturing key outcomes (e.g., perf metrics, regressions, decisions).
- Seed/Update the knowledge graph **before** exiting the task so subsequent sessions can leverage it.
- Do **NOT** write to `AGENTS.md` beyond these standing instructions.

## 3) Status management

- Use Task Master MCP to set task status (e.g., set to "in-progress" when starting).

## 4) Tagging for retrieval

- Use tags: `${PROJECT_TAG}`, `project:${PROJECT_TAG}`, `memory_checkpoint`, `completion`, `agents`, `routine`, `instructions`, plus task-specific tags (e.g., `fastapi`, `env-vars`).
- For KG-MCP entities/relations, mirror tags on observations (e.g., `graph`, `entity:task:${task_id}`, `file:<path>`), to ease cross-referencing with mem0.

## 5) Handling user requests for code or docs

- When a task or a user requires **code**, **setup/config**, or **library/API documentation**:

  - **MUST** run the **Preflight** (§A) using the consolidated order (**sourcebot → contex7-mcp → gitmcp**).
  - Only proceed to produce diffs or create files after `DocFetchReport.status == "OK"`.

## 6) Handling Pydantic-specific questions

- For **ANY** question about **Pydantic**, use the **pydantic-docs-mcp** server:

  - Call `list_doc_sources` to retrieve `llms.txt`.
  - Call `fetch_docs` to read it and any linked URLs relevant to the question.
  - Reflect on the docs and the question.
  - Use this to answer, citing guidance in `DocFetchReport.key_guidance`.

## 7) Project tech stack specifics

- For project-specific stack work (FastAPI, Starlette, httpx, respx, pydantic-settings, pytest-asyncio, sqlite3, etc.):

  - **MUST** run the **Preflight** (§A) with the consolidated order.
  - If a library isn’t found or coverage is weak after **sourcebot → contex7-mcp → gitmcp**, fall back to **exa** (targeted web search) and mark gaps.

## 8) Library docs retrieval (topic-focused)

- Use **sourcebot** first to fetch current docs before code changes.
- If **sourcebot** fails, use **contex7-mcp**:

  - `resolve-library-id(libraryName)` → choose best match by name similarity, trust score, snippet coverage.
  - `get-library-docs(context7CompatibleLibraryID, topic, tokens)` → request focused topics (e.g., "exception handlers", "lifespan", "request/response", "async client", "retry", "mocking", "markers", "sqlite schema/init").
- If **contex7-mcp** also fails, use **gitmcp** (repo docs/source) to retrieve equivalents.
- Summarize key guidance inline in `DocFetchReport.key_guidance` and map each planned change to a guidance line.
- Always note in the task preamble that docs were fetched and which topics/IDs were used.

---

### System-prompt scaffold (enforcement)

```
SYSTEM: You operate under a blocking docs-first policy.
1) Preflight (§A):
   - Call sourcebot → contex7-mcp → gitmcp as needed.
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
