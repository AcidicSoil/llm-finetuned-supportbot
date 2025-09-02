# Extension: Emit GitMCP TOML for tech stack (one-time at project init)

## Scope

- Runs **once** during project initialization immediately after **A.1 Tech & Language Identification** is completed.
- Uses the discovered `tech_stack` array recorded in the `DocFetchReport`.

## Behavior

- Generate a single consolidated `.toml` snippet for `codex-cli` style config under the `[mcp_servers.*]` tables.
- For **each** item in `tech_stack`, emit a table with:
  - Table name: `[mcp_servers.<slug>-docs]` where `<slug>` is a kebab-cased version of the library/tool name (e.g., `fastapi` → `fastapi-docs`).
  - `command = "npx"`
  - `args = ["mcp-remote", "https://gitmcp.io/OWNER/REPO"]`
- **Owner/Repo placeholders** MUST remain as literal `OWNER` and `REPO` unless the assistant is 100% certain of the canonical repo mapping. (Example mappings may be shown separately as non-authoritative samples.)
- Output this snippet **once** in the run’s initialization section, clearly marked `# Generated MCP servers for tech stack`.

## Output template (per entry)

```toml
[mcp_servers.{slug}-docs]
command = "npx"
args = [
  "mcp-remote",
  "https://gitmcp.io/OWNER/REPO"
]
