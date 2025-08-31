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

def main():
    parser = argparse.ArgumentParser(description="Evaluate base and fine-tuned models.")
    parser.add_argument("--base_model_name", type=str, required=True, help="Name of the base model.")
    parser.add_argument("--peft_model_path", type=str, help="Path to the PEFT model adapter.")
    parser.add_argument("--evaluation_suite", type=str, required=True, help="Path to the evaluation suite (JSONL file).")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the evaluation results.")
    parser.add_argument("--max_new_tokens", type=int, default=100, help="Maximum number of new tokens to generate.")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature for generation.")
    parser.add_argument("--quantization", action="store_true", help="Enable quantization.")
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
        prompt = item["prompt"]
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

        results.append({
            "prompt": prompt,
            "base_response": base_response,
            "base_latency": base_latency,
            "peft_response": peft_response,
            "peft_latency": peft_latency,
        })

    # Save results
    output_path = Path(args.output_dir) / "results.csv"
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

if __name__ == "__main__":
    main()
