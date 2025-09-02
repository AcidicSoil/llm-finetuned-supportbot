#!/usr/bin/env python
# coding: utf-8

"""Interactive CLI demo for the fine-tuned model."""

import argparse

import torch
from src.chunking import last_window_for_text
from src.evaluation import load_model_and_tokenizer, load_peft_model


def main():
    parser = argparse.ArgumentParser(description="Interactive CLI demo.")
    parser.add_argument(
        "--base_model_name", type=str, required=True, help="Name of the base model."
    )
    parser.add_argument(
        "--peft_model_path", type=str, help="Path to the PEFT model adapter."
    )
    parser.add_argument(
        "--quantization", action="store_true", help="Enable quantization."
    )
    parser.add_argument(
        "--chunking-strategy",
        choices=["truncate", "sliding_window"],
        default="truncate",
        help="Handle long prompts via truncation or sliding window",
    )
    parser.add_argument("--max-input-length", type=int, default=512)
    parser.add_argument("--stride", type=int, default=128)

    args = parser.parse_args()

    model, tokenizer = load_model_and_tokenizer(args.base_model_name, args.quantization)
    if args.peft_model_path:
        model = load_peft_model(model, args.peft_model_path)

    print("Model loaded. Type 'exit' to quit.")
    while True:
        prompt = input("Prompt: ")
        if prompt.lower() == "exit":
            break

        if args.chunking_strategy == "sliding_window":
            ids, mask = last_window_for_text(
                tokenizer,
                prompt,
                max_length=args.max_input_length,
                stride=args.stride,
            )
            inputs = {
                "input_ids": torch.tensor([ids], dtype=torch.long, device=model.device),
                "attention_mask": torch.tensor(
                    [mask], dtype=torch.long, device=model.device
                ),
            }
        else:
            inputs = tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=args.max_input_length,
            )
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=100, temperature=0.7)
        response = tokenizer.decode(output[0], skip_special_tokens=True)
        print(f"Response: {response}")


if __name__ == "__main__":
    main()
