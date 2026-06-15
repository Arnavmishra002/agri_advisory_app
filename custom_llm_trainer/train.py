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
import sys

# 1. Import unsloth FIRST (mandatory before torch/transformers/peft)
import unsloth

import torch
from datasets import load_dataset
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import (
    DataCollatorForSeq2Seq,
    Trainer,
    TrainingArguments,
    TrainerCallback,
)

# ── Configuration ────────────────────────────────────────────────────────────
MODEL_NAME = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"  # Optimized 4-bit base model
MAX_SEQ_LENGTH = 2048                              # Max prompt/response length
DATASET_PATH = "dataset_prepared.jsonl"             # Local preprocessed JSONL file
OUTPUT_DIR = "krishimitra_outputs"                  # Save checkpoint path
FINAL_MODEL_NAME = "krishimitra-model"              # Name of exported GGUF file

# ── Compatibility Patches ─────────────────────────────────────────────────────
# Patch 1: Guard compute_loss against int num_items_in_batch
_orig_compute_loss = Trainer.compute_loss
def _safe_compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
    if num_items_in_batch is not None and not hasattr(num_items_in_batch, "mean"):
        num_items_in_batch = torch.tensor(float(num_items_in_batch),
                                          device=next(model.parameters()).device)
    return _orig_compute_loss(self, model, inputs, return_outputs, num_items_in_batch)
Trainer.compute_loss = _safe_compute_loss

# Patch 2: Guard training_step against int num_items_in_batch
_orig_training_step = Trainer.training_step
def _safe_training_step(self, model, inputs, num_items_in_batch=None):
    if num_items_in_batch is not None and not hasattr(num_items_in_batch, "mean"):
        num_items_in_batch = torch.tensor(float(num_items_in_batch),
                                          device=next(model.parameters()).device)
    return _orig_training_step(self, model, inputs, num_items_in_batch)
Trainer.training_step = _safe_training_step


class ProgressCallback(TrainerCallback):
    """Prints a heartbeat every 10 steps so the terminal stays active and updated."""
    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs and state.global_step % 10 == 0:
            loss = logs.get("loss", "N/A")
            lr   = logs.get("learning_rate", "N/A")
            step = state.global_step
            total = state.max_steps
            pct  = 100.0 * step / total if total else 0
            vram = torch.cuda.max_memory_allocated() / 1e9
            print(f"   Step {step:>4}/{total} ({pct:5.1f}%) │ loss={loss} │ lr={lr} │ VRAM={vram:.2f}GB")


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
        dtype = None, # None = auto-detection
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token    = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    print("🛠️ Injecting LoRA adapter weights...")
    # 3. Apply PEFT/LoRA adapters
    model = FastLanguageModel.get_peft_model(
        model,
        r = 16,
        target_modules = [
            "q_proj", "k_proj", "v_proj", "o_proj", 
            "gate_proj", "up_proj", "down_proj"
        ],
        lora_alpha = 16,
        lora_dropout = 0,
        bias = "none",
        use_gradient_checkpointing = "unsloth",
        random_state = 3407,
        max_seq_length = MAX_SEQ_LENGTH,
    )

    print("📊 Loading prepared training dataset...")
    # 4. Load dataset from JSONL
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

    # Tokenize dataset explicitly and use DataCollatorForSeq2Seq
    def tokenize(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=MAX_SEQ_LENGTH,
            padding=False,
        )

    tokenized_dataset = dataset.map(tokenize, batched=True, remove_columns=["text"])

    print("🏋️ Starting Supervised Fine-Tuning Trainer...")
    # 5. Initialize SFTTrainer
    trainer = SFTTrainer(
        model = model,
        tokenizer = tokenizer,
        train_dataset = tokenized_dataset,
        max_seq_length = MAX_SEQ_LENGTH,
        dataset_num_proc = 2,
        packing = False,
        data_collator = DataCollatorForSeq2Seq(
            tokenizer = tokenizer,
            model = model,
            padding = True,
            pad_to_multiple_of = 8,
            label_pad_token_id = -100,
        ),
        callbacks = [ProgressCallback()],
        args = TrainingArguments(
            per_device_train_batch_size = 2,
            gradient_accumulation_steps = 4,
            warmup_steps = 20,
            max_steps = 200,                        # Match v7 steps
            learning_rate = 2e-4,
            fp16 = not torch.cuda.is_bf16_supported(),
            bf16 = torch.cuda.is_bf16_supported(),
            logging_steps = 10,
            optim = "adamw_8bit",
            weight_decay = 0.01,
            lr_scheduler_type = "cosine",
            seed = 3407,
            output_dir = OUTPUT_DIR,
            remove_unused_columns = False,
            report_to = "none",
        ),
    )

    # 6. Execute training
    trainer_stats = trainer.train(resume_from_checkpoint=False)
    print(f"✅ Training completed! Peak VRAM usage: {torch.cuda.max_memory_allocated() / 1e9:.2f} GB")

    # 7. Save PEFT checkpoint locally
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"💾 LoRA adapters saved locally to: {OUTPUT_DIR}/")

    # 8. Export directly to GGUF (4-bit medium quantization)
    print("\n📦 Quantizing and exporting model to GGUF format...")
    import gc
    del trainer
    gc.collect()
    torch.cuda.empty_cache()

    model = model.merge_and_unload()
    model.save_pretrained_gguf(
        FINAL_MODEL_NAME, 
        tokenizer, 
        quantization_method = "q4_k_m"
    )
    
    gguf_filename = f"{FINAL_MODEL_NAME}-q4_k_m.gguf"
    print(f"\n🎉 Success! GGUF model exported to: {os.path.abspath(gguf_filename)}")
    print("   Copy this file to your hosting machine and run: ollama create krishimitra-llm -f Modelfile")

if __name__ == "__main__":
    train()
