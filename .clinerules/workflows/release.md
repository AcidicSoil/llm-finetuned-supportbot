# Workflow: Release (Template)

Ask AI: Cut a lightweight release with changelog notes.

```bash
# Generate changelog from commits since last tag (simple)
git log --pretty=format:\"- %s\" $(git describe --tags --abbrev=0 2>/dev/null)...HEAD > CHANGELOG.md || true

# Create tag (interactive)
echo \"Ready to tag? e.g., v0.1.0\" || true
```

<ask_followup_question>
Provide a concise release title and notes. Should I create a git tag now?
</ask_followup_question>
