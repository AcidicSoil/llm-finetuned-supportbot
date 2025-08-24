# System Patterns & Decisions

Model strategy:
- Start with a small open model (e.g., 7B) compatible with PEFT/LoRA and 4-bit quantization (bitsandbytes) to keep costs low.

Training approach:
- Supervised fine-tuning using HF `transformers` + `peft` with LoRA adapters.
- Keep base weights frozen; save adapters for portability.

Data format:
- Conversation-style QA pairs with roles (user/assistant) normalized to a consistent prompt template.

Evaluation:
- Scripted eval set of ~100 support-style prompts; compute win rate vs. base responses and note hallucinations via rubric.

Demo surface:
- Simple CLI and optional FastAPI endpoint for local testing.

Tradeoffs:
- Small models may underperform on nuanced reasoning; focus on domain adaptation and prompt hygiene.
- LoRA favors iteration speed over maximal performance.

