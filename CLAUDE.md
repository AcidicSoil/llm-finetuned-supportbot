# Agents Instructions (Ordered)

- Project: ${PROJECT_TAG}
- Purpose: Canonical instruction list. Do not append logs here;

## 0) Debugging

- **gitmcp** or **contex7-mcp** to fetch latest docs before touching any files

## 1) Startup memory bootstrap (mem0)

- On chat/session start: **mem0**
- Retrieve (project-scoped):
- **mem0** → latest `memory_checkpoints` and recent completions.
- Read/write rules:
  - On completion write checkpoints to **mem0**;

## 2) On task completion (status → done)

- Write a concise completion memory to mem0 including:
  - `task_id`, `title`, `status`, `next step`
  - Files touched
  - Commit/PR link (if applicable)
  - Test results (if applicable)
- Seed/Update the knowledge graph (mcp-think-tank):
  - If this is a **new project** (detected auto-skip in §1), **create a seed node** `project:${PROJECT_TAG}` and initial edges:
    - `project:${PROJECT_TAG}` —[owns]→ `task:${task_id}`
    - `task:${task_id}` —[touches]→ `file:<path>`
    - `task:${task_id}` —[status]→ `<status>`
  - Else, upsert edges for who/what/why/depends-on and recent changes.
- Do NOT write to `AGENTS.md` beyond these standing instructions.

## 3) Status management

- Use Task Master MCP to set task status (e.g., set to "in-progress" when starting).

## 4) Tagging for retrieval

- Use tags: `${PROJECT_TAG}`, `project:${PROJECT_TAG}`, `memory_checkpoint`, `completion`, `agents`, `routine`, `instructions`, plus task-specific tags (e.g., `fastapi`, `env-vars`).

## 5) Handling user requests for code or docs

- When a task or a user requires **code**, **setup or configuration steps**, or **library/API documentation** → use docfork mcp to fetch latest documentation before applying any diffs or creating files/directories.

## 6) Handling Pydantic-specific questions

- For **ANY** question about **Pydantic**, use the **pydantic-docs-mcp** server to help answer:
  - Call `list_doc_sources` tool to get the available `llms.txt` file.
  - Call `fetch_docs` tool to read it.
  - Reflect on the URLs in `llms.txt`.
  - Reflect on the input question.
  - Call `fetch_docs` on any URLs relevant to the question.
  - Use this to answer the question.

## 7) For all other project-specific tasks related to the tech stack

- For **ANY** other project specifics regarding tech stack, use either **gitmcp** or **contex7-mcp** or worst case **exa** to retrieve latest docs to help complete the users request or your tasks with accuracy.

## 8) Library docs retrieval (contex7-mcp standard)

- For every additional library in the stack (e.g., FastAPI, Starlette, httpx, respx, pydantic-settings, pytest-asyncio, sqlite3), fetch current docs before code changes.
- Use contex7-mcp in this order:
  - `resolve-library-id(libraryName)` → select the best match by name similarity, trust score, and snippet coverage. If ambiguous, ask for clarification.
  - `get-library-docs(context7CompatibleLibraryID, topic, tokens)` → request focused topics (e.g., "exception handlers", "lifespan", "request/response", "async client", "retry", "mocking", "markers", "sqlite schema/init"). Use reasonable token limits.
- Summarize key guidance from docs inline to ground any changes. Avoid pasting large docs verbatim.
- If a library isn’t found or coverage is weak, fallback to **gitmcp** (repo docs) or **exa** (targeted web search), then proceed.
- Always note in the task preamble that docs were fetched and which library IDs/topics were used.
