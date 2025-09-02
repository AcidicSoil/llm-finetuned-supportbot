# Efficiency Mode (Extension)

## Scope

- Enabled when the user requests fast execution, prioritization, or minimal back-and-forth.
- Always respects Preflight (§A) and Decision Gate (§B) rules defined in AGENTS.md.

---

## Core Behaviors

- **Act-First Default:** Choose and execute one next step; do not list options unless action is destructive.
- **Single Next Action:** Always produce exactly one high-impact next action.
- **Terse Output:** ≤ 8 bullets or ~120 words. No pleasantries or option menus.
- **No Option Menus:** Replace “A or B?” with “Proceeding with A because X. Undo path: B.”
- **Batching:** Batch doc calls and dependency checks into one pass.
- **Sticky Context:** Cache doc fetches within session; don’t refetch unless version/hash changed.
- **Timebox:** If blocked, create a 3-bullet unblock plan and immediately execute the first.

---

## Preflight Compatibility

- **If touching code/config/APIs/tooling:** Run full Preflight and attach a compact `DocFetchReport`.
- **If not touching those:** Skip Preflight and proceed directly.

---

## Output Format (Strict)

- **Next action:** (imperative, one line).
- **Why:** ≤ 20 words.
- **Acceptance checks:** 3–5 bullets, each testable.
- **If code/diff relevant:** minimal patch or command block.
- **If Preflight ran:** include **one** compact `DocFetchReport` JSON (≤ 15 lines).

---

## Decision Heuristics

- Prefer actions that unblock dependencies fastest.
- If confidence ≥ 0.6: execute with undo path surfaced.
- If < 0.6 and risky: ask **one** yes/no question; otherwise, proceed with safe probe.

---

## Example Rewrite
**Next action:** Audit `src/models.py` for Pydantic v2 compliance and mark Task 2.1 done if aligned.
**Why:** Fastest closure path.
**Acceptance:**

- Models: Inputs, Outputs, Meta, DataRecord present
- `validate_dataset` works on happy/sad paths
- Shared regex constants exist
- Settings ready for `pydantic-settings`
- Minimal pytest coverage
