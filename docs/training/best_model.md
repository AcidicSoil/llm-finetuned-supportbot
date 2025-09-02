# Best Model Selection

Both SFT and DPO recipes can load the best-performing checkpoint at the end of training.

## Enabling

Add the following to your CLI or YAML (YAML keys map 1:1 to CLI flags):

```bash
--load-best-model-at-end \
--metric-name eval_loss \
--no-greater-is-better
```

- `metric-name`: default example uses `eval_loss`. You may choose another metric if you log it.
- `no-greater-is-better`: set this when the metric should be minimized.

Internally these map to the underlying trainer’s arguments and are passed for both SFT and DPO.

## Notes

- Best-model selection requires periodic evaluation and checkpointing (`--eval-steps`, `--save-steps`).
- Some TRL versions handle best-model selection slightly differently; this project passes through the arguments for compatibility.
