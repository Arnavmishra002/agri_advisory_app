#!/usr/bin/env python3
"""
KrishiMitra — Unsloth QLoRA Fine-Tuning Script
=============================================
Fine-tunes Qwen 2.5 7B on the local agricultural dataset and 
exports the final model to GGUF format for Ollama.

Recommended environment:
    Google Colab (T4 GPU), Kaggle Notebook, or local NVIDIA GPU (VRAM >= 8GB)
"""

import os
import torch
from datasets import load_dataset
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments

# ── Configuration ────────────────────────────────────────────────────────────
MODEL_NAME = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"  # Optimized 4-bit base model
MAX_SEQ_LENGTH = 2048                              # Max prompt/response length
DATASET_PATH = "dataset_prepared.jsonl"             # Local preprocessed JSONL file
OUTPUT_DIR = "krishimitra_outputs"                  # Save checkpoint path
FINAL_MODEL_NAME = "krishimitra-model"              # Name of exported GGUF file

def train():
    # 1. Validate dataset existence
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(
            f"❌ Dataset not found at '{DATASET_PATH}'. Please run `python3 prepare_dataset.py` first."
        )

    print("🚀 Loading model in 4-bit precision...")
    # 2. Load the model and tokenizer
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = MODEL_NAME,
        max_seq_length = MAX_SEQ_LENGTH,
        load_in_4bit = True,
        dtype = None, # None = auto-detection (Float16/Bfloat16 based on hardware)
    )

    print("🛠️ Injecting LoRA adapter weights...")
    # 3. Apply PEFT/LoRA adapters
    # target_modules targets all projections to maximize learning capacity
    model = FastLanguageModel.get_peft_model(
        model,
        r = 16,                                        # Rank (higher = more capacity, 8/16/32/64)
        target_modules = [
            "q_proj", "k_proj", "v_proj", "o_proj", 
            "gate_proj", "up_proj", "down_proj"
        ],
        lora_alpha = 16,
        lora_dropout = 0,
        bias = "none",
        use_gradient_checkpointing = "unsloth",        # Extremely low memory usage
        random_state = 3407,
        max_seq_length = MAX_SEQ_LENGTH,
    )

    print("📊 Loading prepared training dataset...")
    # 4. Load dataset from JSONL
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

    print("🏋️ Starting Supervised Fine-Tuning Trainer...")
    # 5. Initialize SFTTrainer
    trainer = SFTTrainer(
        model = model,
        tokenizer = tokenizer,
        train_dataset = dataset,
        dataset_text_field = "text",
        max_seq_length = MAX_SEQ_LENGTH,
        dataset_num_proc = 2,
        packing = False, # Set to True for short QA inputs to speed up training
        args = TrainingArguments(
            per_device_train_batch_size = 2,
            gradient_accumulation_steps = 4,
            warmup_steps = 10,
            max_steps = 120,                        # Adjust based on dataset size (e.g. 1-3 epochs)
            learning_rate = 2e-4,                   # Standard LoRA learning rate
            fp16 = not torch.cuda.is_bf16_supported(),
            bf16 = torch.cuda.is_bf16_supported(),
            logging_steps = 5,
            optim = "adamw_8bit",
            weight_decay = 0.01,
            lr_scheduler_type = "linear",
            seed = 3407,
            output_dir = OUTPUT_DIR,
        ),
    )

    # 6. Execute training
    trainer_stats = trainer.train()
    print(f"✅ Training completed! Peak VRAM usage: {torch.cuda.max_memory_allocated() / 1e9} GB")

    # 7. Save PEFT checkpoint locally
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"💾 LoRA adapters saved locally to: {OUTPUT_DIR}/")

    # 8. Export directly to GGUF (4-bit medium quantization)
    print("\n📦 Quantizing and exporting model to GGUF format...")
    print("   This may take a few minutes...")
    model.save_pretrained_gguf(
        FINAL_MODEL_NAME, 
        tokenizer, 
        quantization_method = "q4_k_m" # Optimal balance of size (4.7 GB) and reasoning quality
    )
    
    gguf_filename = f"{FINAL_MODEL_NAME}-q4_k_m.gguf"
    print(f"\n🎉 Success! GGUF model exported to: {os.path.abspath(gguf_filename)}")
    print("   Copy this file to your hosting machine and run: ollama create krishimitra-llm -f Modelfile")

if __name__ == "__main__":
    train()
