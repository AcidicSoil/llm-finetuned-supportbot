#!/usr/bin/env python
# coding: utf-8

"""Interactive CLI demo for the fine-tuned model."""

import argparse
import torch
from src.evaluation import load_model_and_tokenizer, load_peft_model


def main():
    parser = argparse.ArgumentParser(description="Interactive CLI demo.")
    parser.add_argument("--base_model_name", type=str, required=True, help="Name of the base model.")
    parser.add_argument("--peft_model_path", type=str, help="Path to the PEFT model adapter.")
    parser.add_argument("--quantization", action="store_true", help="Enable quantization.")
    args = parser.parse_args()

    model, tokenizer = load_model_and_tokenizer(args.base_model_name, args.quantization)
    if args.peft_model_path:
        model = load_peft_model(model, args.peft_model_path)

    print("Model loaded. Type 'exit' to quit.")
    while True:
        prompt = input("Prompt: ")
        if prompt.lower() == 'exit':
            break

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=100, temperature=0.7)
        response = tokenizer.decode(output[0], skip_special_tokens=True)
        print(f"Response: {response}")


if __name__ == "__main__":
    main()
