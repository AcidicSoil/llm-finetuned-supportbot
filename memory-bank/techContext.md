# Tech Context

Stack:
- Python, PyTorch, Hugging Face `transformers`, `datasets`, `peft`, `trl`, `bitsandbytes`.

Environment:
- Local dev with virtualenv. Optional CUDA if available.

Constraints:
- Keep VRAM modest by using 4/8-bit quant + LoRA.
- Prefer reproducibility (seeded runs, requirements.txt, README steps).

Repos/dirs of note:
- `demo.py`, `eval/`, `results/`, `tests/` (as available).
- `PRD.txt` for product direction; Cline workflows present under `.clinerules/`.

Secrets:
- None required for basic training; if using model hub push, store tokens in env.

