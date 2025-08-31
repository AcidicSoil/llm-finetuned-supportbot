# Cline — Developer Cheat Sheet

## 1) Memory Bank (setup, usage, best practices)

* **Purpose:** Persistent, repo‑scoped context that Cline reads at the start of each task to “remember” your project.
* **Location/Structure (`memory-bank/`):**

  * `projectbrief.md` (goals, scope)
  * `productContext.md` (problems, users, use‑cases)
  * `systemPatterns.md` (architecture & decisions)
  * `techContext.md` (stack, env, constraints)
  * `activeContext.md` (what you’re working on now)
  * `progress.md` (milestones, TODOs, issues)
* **Setup (any one):**

  * Chat: “Initialize the memory bank for this project.”
  * MCP (community): install memory‑bank MCP and run `initialize_memory_bank .`
* **How Cline uses it:** Reads all files at task start; updates after major changes or on command (“update memory bank”).
* **When to update:** After features/bugfixes, new decisions, or shifting focus (keep `activeContext.md` and `progress.md` fresh).
* **Best practices:**

  * Keep files concise, decision‑oriented; avoid noise.
  * Note “current focus” in `activeContext.md`.
  * Record “why” in `systemPatterns.md` (tradeoffs).
  * Commit the folder so teammates get the same context.

---

## 2) Workflows (creation, execution, examples)

* **What:** Markdown files that script repeatable, multi‑step tasks you can run with `/workflow-name`.
* **Where:** Project: `.clinerules/workflows/*.md` (recommended); also supported globally.
* **Format (essentials):**

  * Free text “Ask AI” guidance
  * Steps with:

    * Shell blocks `bash …` (build/test/deploy)
    * Tool tags (e.g., `<ask_followup_question>`, `<read_file>`, etc.)
* **Run:** Type `/your-workflow-name` → Cline executes step‑by‑step, pausing for approvals/questions.
* **Example (deploy):**

  * Step 1: `npm ci && npm test`
  * Step 2: `docker build` + `docker push`
  * Step 3: `<ask_followup_question>` (“Deploy now?”)
  * Step 4: `kubectl rollout restart ...` (conditional)
* **Tips:**

  * Keep steps deterministic; test them.
  * Use branching via follow‑up questions.
  * Compose with other tools (GitHub CLI, MCP tools).
  * Rely on **Focus Chain** for ad‑hoc task planning—Cline auto‑tracks subtasks.

---

## 3) MCP Servers (configuration, integration, security)

* **What:** Plugin layer (Model Context Protocol) that exposes tools/resources to Cline (search, browser, DB, CI, etc.).
* **Install options:**

  * **Marketplace UI:** one‑click add, then provide keys/paths.
  * **From GitHub:** clone/build server; add to Cline MCP settings.
  * **Custom:** write your own (STDIO or SSE transport).
* **Config (conceptual):**

  ```json
  {
    "mcpServers": {
      "local-tool": { "command": "python", "args": ["./tool.py"], "env": { "API_KEY": "…" } },
      "remote-agent": { "url": "https://example.com/mcp", "headers": { "Authorization": "Bearer …" } }
    }
  }
  ```

* **Usage:** Ask naturally; Cline proposes tool calls; you approve (or whitelist via `alwaysAllow`).
* **Transports:**

  * **STDIO (local):** low latency, no network.
  * **SSE (remote):** shared/hosted tools; requires network.
* **Security:**

  * Install trusted servers only; keep secrets in env/config.
  * Keep human‑in‑the‑loop approvals for risky actions.

---

## 4) Rules (definition, usage, examples)

* **What:** Persistent Markdown instructions that shape Cline’s behavior.
* **Where:**

  * **Global:** `~/Documents/Cline/Rules/…`
  * **Project:** `.clinerules/*.md` (recommended modular files, e.g., `01-guidelines.md`)
* **Create/Manage:**

  * UI “Rules” tab → “+”
  * `/newrule` wizard (interactive Q\&A → file)
  * Order/merge: multiple files are combined; workspace rules override global.
* **Good rule content:**

  * Coding standards (style, testing, error handling)
  * Architecture conventions & documentation requirements
  * Tooling behaviors (e.g., “read Memory Bank before tasks; update after”)
  * Safety checks (“ask before using X”, “no eval”, etc.)
* **Examples:**

  * “Python: PEP8, 4 spaces; JS: 2 spaces, Airbnb.”
  * “Write unit tests for every bug fix.”
  * “Document decisions in `/docs/architecture.md`.”

---

## 5) Additional Tools (mentions, checkpoints, slash commands, remote browser)

* **@ Mentions (inject context):**

  * `@/path/file` (full file), `@/dir/` (folder), `@problems` (VS Code Problems), `@terminal` (recent output),
    `@git-changes`, `@[commit]`, `@https://…` (URL content; needs browser support).
  * Use to avoid copy/paste and give Cline exact, full‑fidelity context.
* **Checkpoints (safe undo/compare):**

  * Auto snapshot after each code‑changing step.
  * **Compare** diffs per step.
  * Restore options: **Task+Workspace**, **Task only**, **Workspace only**.
* **Key Slash Commands:**

  * `/newtask` — fork a fresh task with a summarized handoff.
  * `/deep-planning` — force thorough plan → then execute.
  * `/smol` (or `/compact`) — compress conversation into a concise summary to free context.
  * `/newrule` — create a rule interactively.
* **Remote Browser:**

  * Enable to power `@url` and web automation.
  * Easiest: run Chrome with `--remote-debugging-port=9222` and connect via Cline.
  * Or install a Browser MCP (Playwright/Puppeteer) and configure path/keys.

---

## 6) Project Scaffold (recommended structure & integration)

```
my-project/
├─ memory-bank/
│  ├─ projectbrief.md
│  ├─ productContext.md
│  ├─ systemPatterns.md
│  ├─ techContext.md
│  ├─ activeContext.md
│  └─ progress.md
├─ .clinerules/
│  ├─ 01-guidelines.md          # style/testing/architecture rules
│  ├─ 02-memory-bank.md         # instruct Cline to read/update memory
│  ├─ 03-newtask-strategy.md    # when/how to handoff/compact
│  └─ workflows/
│     ├─ pr-review.md
│     ├─ deploy-service.md
│     └─ release.md
├─ src/
├─ tests/
└─ README.md
```

* **Team setup checklist:**

  * Commit `memory-bank/` & `.clinerules/` to repo.
  * Document recommended MCPs (names, required ENV) in `README.md`.
  * Each dev: install MCPs, connect Remote Browser, verify `/workflows` appear.
* **Daily loop:**

  1. Start task → Cline loads Memory Bank + Rules.
  2. Use `@mentions` to inject exact files/logs.
  3. Let Cline act; **Compare** diffs; **Restore** if needed.
  4. After milestone → “update memory bank”; commit memory updates.
  5. Use `/newtask` or `/smol` to keep context sharp.
  6. Run workflows for routine ops (PR review, deploy, release).

**Bottom line:** Put durable knowledge in **Memory Bank**, enforce expectations with **Rules**, automate repeatables via **Workflows**, extend reach with **MCP**, keep safety with **Checkpoints**, and supercharge context with **@mentions** + **Remote Browser**.
