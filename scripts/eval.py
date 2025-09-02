#!/usr/bin/env python
# coding: utf-8

"""Evaluation script for comparing base and fine-tuned models."""

import argparse
import json
import time
from pathlib import Path

import pandas as pd
import torch
from tqdm import tqdm

from src.evaluation import load_model_and_tokenizer, load_peft_model
from src.eval_schema import classify_error, ErrorType

def main():
    parser = argparse.ArgumentParser(description="Evaluate base and fine-tuned models.")
    parser.add_argument("--base_model_name", type=str, required=True, help="Name of the base model.")
    parser.add_argument("--peft_model_path", type=str, help="Path to the PEFT model adapter.")
    parser.add_argument("--evaluation_suite", type=str, required=True, help="Path to the evaluation suite (JSONL file).")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the evaluation results.")
    parser.add_argument("--max_new_tokens", type=int, default=100, help="Maximum number of new tokens to generate.")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature for generation.")
    parser.add_argument("--quantization", action="store_true", help="Enable quantization.")
    parser.add_argument("--annotate_errors", action="store_true", help="Annotate responses with heuristic error types")
    args = parser.parse_args()

    # Load base model and tokenizer
    base_model, tokenizer = load_model_and_tokenizer(args.base_model_name, args.quantization)

    # Load PEFT model if adapter path is provided
    peft_model = None
    if args.peft_model_path:
        peft_model = load_peft_model(base_model, args.peft_model_path)

    # Load evaluation suite
    with open(args.evaluation_suite, 'r') as f:
        evaluation_suite = [json.loads(line) for line in f]

    # Run evaluation
    results = []
    for item in tqdm(evaluation_suite):
        # Support either flat {prompt: ...} or schema-like {inputs:{question,context?}}
        if "prompt" in item:
            prompt = item["prompt"]
        else:
            inputs = item.get("inputs", {})
            prompt = inputs.get("question") or inputs.get("prompt") or ""
        inputs = tokenizer(prompt, return_tensors="pt").to(base_model.device)

        # Generate from base model
        start_time = time.time()
        base_output = base_model.generate(**inputs, max_new_tokens=args.max_new_tokens, temperature=args.temperature)
        base_latency = time.time() - start_time
        base_response = tokenizer.decode(base_output[0], skip_special_tokens=True)

        # Generate from PEFT model
        peft_response = None
        peft_latency = None
        if peft_model:
            start_time = time.time()
            peft_output = peft_model.generate(**inputs, max_new_tokens=args.max_new_tokens, temperature=args.temperature)
            peft_latency = time.time() - start_time
            peft_response = tokenizer.decode(peft_output[0], skip_special_tokens=True)

        rec = {
            "prompt": prompt,
            "base_response": base_response,
            "base_latency": base_latency,
            "peft_response": peft_response,
            "peft_latency": peft_latency,
        }
        if args.annotate_errors and peft_response is not None:
            etype = classify_error(prompt, peft_response)
            rec["error_type"] = etype.value if isinstance(etype, ErrorType) else None
        results.append(rec)

    # Save results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "results.csv"
    df = pd.DataFrame(results)
    df.to_csv(output_path, index=False)
    print(f"Results saved to {output_path}")

    # Calculate and print metrics
    if args.peft_model_path:
        if 'winner' not in df.columns:
            print("Winner column not found. Please add a 'winner' column with values 'base', 'peft', or 'tie'.")
        else:
            win_rate = df['winner'].value_counts(normalize=True)
            print("\nWin Rate:")
            print(win_rate)

        if 'base_hallucination' not in df.columns or 'peft_hallucination' not in df.columns:
            print("Hallucination columns not found. Please add 'base_hallucination' and 'peft_hallucination' columns with boolean values.")
        else:
            base_hallucination_rate = df['base_hallucination'].mean()
            peft_hallucination_rate = df['peft_hallucination'].mean()

            print("\nHallucination Rate:")
            print(f"Base model: {base_hallucination_rate:.2%}")
            print(f"PEFT model: {peft_hallucination_rate:.2%}")

    # Error aggregates
    if args.annotate_errors and 'error_type' in df.columns:
        agg = df['error_type'].value_counts(dropna=True, normalize=True).to_dict()
        stats_path = output_dir / "error_stats.json"
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump({"rates": agg}, f, indent=2)
        print(f"Error stats saved to {stats_path}")

if __name__ == "__main__":
    main()
