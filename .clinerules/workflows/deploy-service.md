# Workflow: Deploy Service (Template)

Ask AI: Prepare a deployment. This repo is primarily training/eval; treat this as a template and confirm steps before running.

```bash
# Build container (optional)
docker build -t supportbot:latest . || true

# Push image (placeholder)
echo "Skipping push; configure registry first" || true
```

<ask_followup_question>
This project may not have a deployable service yet. Do you want to skip deployment, or set up a minimal FastAPI and containerize it?
</ask_followup_question>
