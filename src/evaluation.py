

def load_peft_model(model, peft_model_path: str):
    """Utility to load a PEFT adapter and apply to a base model."""
    model = PeftModel.from_pretrained(model, peft_model_path)
    model = model.merge_and_unload()
    return model
