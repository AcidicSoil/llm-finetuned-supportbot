# Agents Instructions (Ordered)

* Project: \${PROJECT\_TAG}
* Purpose: Canonical instruction list. Do not append logs here.

---

## Instruction Layering & Extensions

* **Baseline:** This file (**AGENTS.md**) is the canonical baseline for all assistant behavior.
* **Extensions:** Additional instruction files may be “tagged in” for specific contexts.

  * When an extension file is tagged (e.g., `file:prd_generator.md`), its rules **stack on top of** AGENTS.md.
  * The assistant must first apply **all baseline rules** from AGENTS.md, then layer the tagged file’s additional instructions.
  * If conflicts arise:

    * **Baseline (AGENTS.md)** provides the core operating rules.
    * **Tagged file** instructions apply only to their scoped role or task.
    * Conflicts are resolved in favor of the more specific tagged file.
* **Example:**

  * Baseline: Follow Preflight/Decision Gate for doc retrieval.
  * Extension: If the tagged file is `prd_generator.md`, also assume the role *“PRD Generator”* and follow its steps to output `prd.txt` in the specified format.

---

## A) Preflight: Latest Docs Requirement (**MUST**, Blocking)

**Goal:** Ensure the assistant retrieves and considers the *latest relevant docs* before planning, acting, or finalizing.

**Primary/Fallback Order (consolidated):**

1. **docfork mcp** (primary)
2. **contex7-mcp** (fallback if docfork fails)
3. **gitmcp** (last-resort fallback if both above fail)

**What to do:**

* For every task that could touch code, configuration, APIs, tooling, or libraries:

  * Call **docfork mcp** to fetch the latest documentation or guides.
  * If the call **fails**, immediately retry with **contex7-mcp**; if that also **fails**, retry with **gitmcp**.
* Each successful call **MUST** capture:

  * Tool name, query/topic, retrieval timestamp (UTC), and source refs/URLs (or repo refs/commits).
* Scope:

  * Fetch docs for each **area to be touched** (framework, library, CLI, infra, etc.).
  * Prefer focused topics (e.g., "exception handlers", "lifespan", "retry policy", "sqlite schema").

**Failure handling:**

* If **all** three providers fail for a required area, **do not finalize**. Return a minimal plan that includes:

  * The attempted providers and errors
  * The specific topics/areas still uncovered
  * A safe, read-only analysis and suggested next checks (or user confirmation).

**Proof-of-Work Artifact (required):**

* Produce and attach a `DocFetchReport` (JSON) with `status`, `tools_called[]`, `sources[]`, `coverage`, `key_guidance[]`, `gaps`, and `informed_changes[]`.
* Example schema:

```json
{
  "DocFetchReport": {
    "status": "OK | PARTIAL | FAILED",
    "tools_called": [
      {"name": "docfork|contex7-mcp|gitmcp", "time_utc": "<ISO8601>", "query": "<topic/ids>"}
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

* Allowed only for outages/ambiguous scope/timeboxed spikes. Must include:

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

## A.1) Tech Stack Identification (Pre-Requirement)

* Before running Preflight (§A), the assistant must determine the **current project’s tech stack**.
* Sources to infer stack:

  * Project tags (`${PROJECT_TAG}`), mem0 checkpoints, prior completion records.
  * Files present in repo (e.g., `pyproject.toml`, `requirements.txt`, `package.json`, `Dockerfile`, CI configs).
  * User/task context (explicit mentions of frameworks, CLIs, infra).
* The identified stack (frameworks, libraries, infra, tools) becomes the **target scope** for doc retrieval.
* Doc retrieval (§A) **must cover each tech stack element** that will be touched by the task.
* Record the inferred tech stack in the `DocFetchReport` under a new field:

```json
"tech_stack": ["fastapi", "httpx", "sqlite3", "pytest-asyncio"]
```

---

## B) Decision Gate: No Finalize Without Proof (**MUST**)

* The assistant **MUST NOT**: finalize, apply diffs, modify files, or deliver a definitive answer **unless** `DocFetchReport.status == "OK"`.
* The planner/executor must verify `ctx.docs_ready == true` (set when at least one successful docs call exists **per required area**).
* If `status != OK` or `ctx.docs_ready != true`:

  * Stop. Return a **Docs Missing** message that lists the exact MCP calls and topics to run.

---

## 0) Debugging

* **Use consolidated docs-first flow** before touching any files or finalizing:

  * Try **docfork mcp** → if fail, **contex7-mcp** → if fail, **gitmcp**.
  * Record results in `DocFetchReport`.

## 1) Startup memory bootstrap (mem0)

* On chat/session start: **mem0**
* Retrieve (project-scoped):

  * **mem0** → latest `memory_checkpoints` and recent task completions.
* Read/write rules:

  * On task completion write checkpoints to **mem0**.

## 2) On task completion (status → done)

* Write a concise completion memory to mem0 including:

  * `task_id`, `title`, `status`, `next step`
  * Files touched
  * Commit/PR link (if applicable)
  * Test results (if applicable)
* Seed/Update the knowledge graph (mcp-think-tank):

  * If this is a **new project** (detected auto-skip in §1), **create a seed node** `project:${PROJECT_TAG}` and initial edges:

    * `project:${PROJECT_TAG}` —\[owns]→ `task:${task_id}`
    * `task:${task_id}` —\[touches]→ `file:<path>`
    * `task:${task_id}` —\[status]→ `<status>`
  * Else, upsert edges for who/what/why/depends-on and recent changes.
* Do **NOT** write to `AGENTS.md` beyond these standing instructions.

## 3) Status management

* Use Task Master MCP to set task status (e.g., set to "in-progress" when starting).

## 4) Tagging for retrieval

* Use tags: `${PROJECT_TAG}`, `project:${PROJECT_TAG}`, `memory_checkpoint`, `completion`, `agents`, `routine`, `instructions`, plus task-specific tags (e.g., `fastapi`, `env-vars`).

## 5) Handling user requests for code or docs

* When a task or a user requires **code**, **setup/config**, or **library/API documentation**:

  * **MUST** run the **Preflight** (§A) using the consolidated order (docfork → contex7 → gitmcp).
  * Only proceed to produce diffs or create files after `DocFetchReport.status == "OK"`.

## 6) Handling Pydantic-specific questions

* For **ANY** question about **Pydantic**, use the **pydantic-docs-mcp** server:

  * Call `list_doc_sources` to retrieve `llms.txt`.
  * Call `fetch_docs` to read it and any linked URLs relevant to the question.
  * Reflect on the docs and the question.
  * Use this to answer, citing guidance in `DocFetchReport.key_guidance`.

## 7) Project tech stack specifics

* For project-specific stack work (FastAPI, Starlette, httpx, respx, pydantic-settings, pytest-asyncio, sqlite3, etc.):

  * **MUST** run the **Preflight** (§A) with the consolidated order.
  * If a library isn’t found or coverage is weak after docfork → contex7 → gitmcp, fall back to **exa** (targeted web search) and mark gaps.

## 8) Library docs retrieval (topic-focused)

* Use **docfork mcp** first to fetch current docs before code changes.
* If docfork fails, use **contex7-mcp**:

  * `resolve-library-id(libraryName)` → choose best match by name similarity, trust score, snippet coverage.
  * `get-library-docs(context7CompatibleLibraryID, topic, tokens)` → request focused topics (e.g., "exception handlers", "lifespan", "request/response", "async client", "retry", "mocking", "markers", "sqlite schema/init").
* If contex7-mcp also fails, use **gitmcp** (repo docs/source) to retrieve equivalents.
* Summarize key guidance inline in `DocFetchReport.key_guidance` and map each planned change to a guidance line.
* Always note in the task preamble that docs were fetched and which topics/IDs were used.

---

### System-prompt scaffold (enforcement)

```
SYSTEM: You operate under a blocking docs-first policy.
1) Preflight (§A):
   - Call docfork → contex7-mcp → gitmcp as needed.
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
