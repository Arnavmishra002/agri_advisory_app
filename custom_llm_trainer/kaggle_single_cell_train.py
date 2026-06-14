# ==============================================================================
# KrishiMitra — Single-Cell Kaggle Fine-Tuning & Quantization Script
# ==============================================================================
# Copy and paste this entire file into a single cell of your Kaggle Notebook.
# Make sure "Internet" is set to ON in your Kaggle settings panel!
# ==============================================================================

# ── Step 1: Install Unsloth and PyTorch dependencies ──────────────────────────
print("📦 Installing Unsloth and high-speed training dependencies...")
import sys

# Remove default Kaggle PyTorch to prevent version conflicts
!pip install pip3-autoremove -q
!pip-autoremove torch torchvision torchaudio -y -q

# Install GPU-optimized PyTorch 2.1 + xformers
!pip install torch torchvision torchaudio xformers --index-url https://download.pytorch.org/whl/cu121 -q

# Install Unsloth and training packages
!pip install "unsloth[kaggle-new] @ git+https://github.com/unslothai/unsloth.git" -q
!pip install datasets trl peft transformers bitsandbytes -q

# ── Step 2: Auto-detect, clean, and format KCC dataset ────────────────────────
print("\n📊 Scanning for attached datasets in /kaggle/input...")
import os
import glob
import csv
import json
from datasets import load_dataset

# Starter seed dataset in case no Kaggle datasets are attached yet
SEED_DATA = [
    {"query": "मेरे गेहूँ की पत्तियों पर पीले रंग के पाउडर जैसे धब्बे दिख रहे हैं, यह क्या है?", "response": "यह पीला रतुआ (Yellow Rust) बीमारी के लक्षण हैं। इसके नियंत्रण के लिए प्रति हेक्टेयर 500 मिलीलीटर प्रोपिकोनाजोल 25% ई.सी. को 500 लीटर पानी में मिलाकर छिड़काव करें।"},
    {"query": "धान की नर्सरी तैयार करने का सही समय क्या है?", "response": "खरीफ सीजन के लिए धान की नर्सरी (पौधशाला) लगाने का सही समय 15 मई से 15 जून के बीच होता है।"},
    {"query": "What is the recommended fertilizer dose for high-yield wheat?", "response": "For high-yield irrigated wheat, the recommended NPK dose is 120:60:40 kg/ha."}
]

SYSTEM_PROMPT = "You are KrishiMitra AI, an expert agricultural advisor for Indian farmers."

def format_to_chatml(query, response):
    return {
        "text": f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n{response}<|im_end|>"
    }

# Scan input directories for KCC CSVs
csv_files = glob.glob("/kaggle/input/**/*.csv", recursive=True)
output_jsonl = "/kaggle/working/dataset_prepared.jsonl"
dataset_count = 0

with open(output_jsonl, "w", encoding="utf-8") as f_out:
    # Always write seed examples first
    for item in SEED_DATA:
        f_out.write(json.dumps(format_to_chatml(item["query"], item["response"]), ensure_ascii=False) + "\n")
        dataset_count += 1

    if csv_files:
        print(f"🔍 Found {len(csv_files)} CSV file(s). Attempting KCC parsing...")
        for csv_path in csv_files:
            print(f"   Reading: {csv_path}")
            with open(csv_path, "r", encoding="utf-8", errors="ignore") as f_in:
                reader = csv.DictReader(f_in)
                
                # Dynamic column name discovery
                query_col, answer_col, crop_col = None, None, None
                if reader.fieldnames:
                    for col in reader.fieldnames:
                        col_lower = col.lower()
                        if not query_col and any(kw in col_lower for kw in ["query", "question", "kisanquery", "querytext"]):
                            query_col = col
                        if not answer_col and any(kw in col_lower for kw in ["answer", "response", "reply", "responsetext", "advisorreply"]):
                            answer_col = col
                        if not crop_col and any(kw in col_lower for kw in ["crop", "cropname"]):
                            crop_col = col

                if not query_col or not answer_col:
                    print(f"   ⚠️ Could not identify query/answer columns automatically. Skipping: {csv_path}")
                    continue
                
                print(f"   💡 Using columns: Query='{query_col}', Answer='{answer_col}', Crop='{crop_col or 'None'}'")
                
                for row in reader:
                    query = (row.get(query_col) or "").strip()
                    answer = (row.get(answer_col) or "").strip()
                    crop = (row.get(crop_col) or "").strip() if crop_col else ""
                    
                    if query and answer:
                        full_query = query
                        if crop and crop.lower() not in query.lower():
                            full_query = f"Crop: {crop}. Question: {query}"
                        
                        f_out.write(json.dumps(format_to_chatml(full_query, answer), ensure_ascii=False) + "\n")
                        dataset_count += 1
    else:
        print("⚠️ No CSV datasets attached. Training will proceed with the agricultural seed dataset.")

print(f"✅ Preprocessing done. Total examples for training: {dataset_count}")

# ── Step 3: Load Model & Tokenizer ────────────────────────────────────────────
print("\n🚀 Loading Qwen 2.5 7B in 4-bit precision via Unsloth...")
import torch
from unsloth import FastLanguageModel

MODEL_NAME = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
MAX_SEQ_LENGTH = 2048

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = MODEL_NAME,
    max_seq_length = MAX_SEQ_LENGTH,
    load_in_4bit = True,
    dtype = None,
)

# Apply LoRA target adapters
model = FastLanguageModel.get_peft_model(
    model,
    r = 16,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha = 16,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    random_state = 3407,
    max_seq_length = MAX_SEQ_LENGTH,
)

# ── Step 4: Run Fine-Tuning ───────────────────────────────────────────────────
print("\n🏋️ Initializing Trainer and starting Supervised Fine-Tuning...")
from trl import SFTTrainer
from transformers import TrainingArguments

dataset = load_dataset("json", data_files=output_jsonl, split="train")

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = MAX_SEQ_LENGTH,
    dataset_num_proc = 2,
    packing = False,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 10,
        max_steps = 100, # Adjust based on data size (e.g. increase for bigger dataset)
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 5,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = "krishimitra_checkpoints",
    ),
)

trainer.train()
print(f"✅ Fine-Tuning complete. VRAM peak: {torch.cuda.max_memory_allocated() / 1e9:.2f} GB")

# ── Step 5: Quantize and Export to GGUF ───────────────────────────────────────
print("\n📦 Quantizing and exporting model to GGUF format...")
GGUF_NAME = "krishimitra-model"

model.save_pretrained_gguf(
    GGUF_NAME, 
    tokenizer, 
    quantization_method = "q4_k_m"
)

print(f"\n🎉 SUCCESS! Fine-tuned GGUF file is available at: /kaggle/working/{GGUF_NAME}-q4_k_m.gguf")
print("   You can download this file directly from the Output files pane on the right!")
