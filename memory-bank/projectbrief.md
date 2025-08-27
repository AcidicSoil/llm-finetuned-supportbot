# Project Brief

Goal: Fine-tune a small open LLM on tech-support style conversations and evaluate improvements in helpfulness and accuracy for a support bot use case.

Scope:

- Data prep, training (LoRA/PEFT), lightweight evaluation, and a minimal demo (CLI/API).
- Out of scope: Full productionization, multi-node training, proprietary datasets.

Why now:

- Showcase practical fine-tuning on modest hardware with transparent metrics for a portfolio-ready project.

Success criteria:

- Win-rate improvement vs. base model on 100 eval questions.
- Lower hallucination rate per rubric.
- Reasonable cost/time documented.

Primary artifacts:

- Reproducible training script(s), eval scripts, results/ summaries, README write-up.
