#!/usr/bin/env python3
"""
KrishiMitra — Agricultural Dataset Preprocessor
===============================================
Generates a high-quality starter instruction-tuning dataset and provides 
utilities to parse downloaded Kisan Call Center (KCC) CSV logs.

Output:
    dataset_prepared.jsonl (formatted in Qwen ChatML format)
"""

import os
import json
import csv

# 1. High-quality seed Q&A data (Hindi & English) to bootstrap training immediately
SEED_DATA = [
    # Wheat queries
    {
        "query": "मेरे गेहूँ की पत्तियों पर पीले रंग के पाउडर जैसे धब्बे दिख रहे हैं, यह क्या है?",
        "response": "यह पीला रतुआ (Yellow Rust) बीमारी के लक्षण हैं। इसके नियंत्रण के लिए: \n- तुरंत प्रभावित पौधों को नष्ट करें।\n- खेत में पानी जमा न होने दें।\n- प्रति हेक्टेयर 500 मिलीलीटर प्रोपिकोनाजोल 25% ई.सी. को 500 लीटर पानी में मिलाकर छिड़काव करें।\n- जैविक नियंत्रण के लिए ट्राइकोडर्मा विरिडी का प्रयोग करें।"
    },
    {
        "query": "गेहूँ में पहली सिंचाई (CRI Stage) कब करनी चाहिए?",
        "response": "गेहूँ की फसल में पहली सिंचाई बोने के 20 से 25 दिनों के बाद करनी चाहिए। इस समय पौधे में 'मुकुट जड़' (Crown Root Initiation - CRI) का निर्माण होता है। यह सिंचाई फसल के अच्छे कल्ले फूटने (Tillering) और समुचित विकास के लिए सबसे महत्वपूर्ण है।"
    },
    {
        "query": "What is the recommended fertilizer dose for high-yield wheat?",
        "response": "For high-yield irrigated wheat, the recommended NPK dose is 120:60:40 kg/ha:\n- Apply the full dose of Phosphorus (60 kg) and Potassium (40 kg), and 1/3 of Nitrogen during sowing.\n- Apply the remaining Nitrogen in two equal splits: the first split after the first irrigation (25 days), and the second split at the jointing stage (55 days)."
    },
    
    # Rice queries
    {
        "query": "धान की नर्सरी तैयार करने का सही समय क्या है?",
        "response": "खरीफ सीजन के लिए धान की नर्सरी (पौधशाला) लगाने का सही समय 15 मई से 15 जून के बीच होता है। 21 से 25 दिन पुरानी पौध मुख्य खेत में रोपाई के लिए बिल्कुल उपयुक्त होती है।"
    },
    {
        "query": "My rice plant stems are turning brown and drying up. What is the cure?",
        "response": "This indicates stem borer (तना छेदक) infestation. To control it:\n- Use Trichogramma chilonis cards (biocontrol agent) at 5 cards per hectare.\n- In case of severe chemical infestation, apply Cartap Hydrochloride 4G at 25 kg/ha or Chlorantraniliprole 18.5% SC at 150 ml/ha mixed with 500 liters of water."
    },
    
    # Soil Health
    {
        "query": "मिट्टी की जांच क्यों जरूरी है और नमूना कैसे लें?",
        "response": "मिट्टी की जांच (Soil Testing) से खेत में पोषक तत्वों की कमी का पता चलता है, जिससे सही मात्रा में उर्वरक डालकर खेती की लागत घटाई जा सकती है। नमूना लेने के लिए:\n- खेत में 8 से 10 अलग-अलग स्थानों से 'V' आकार का 15 सेमी गहरा गड्ढा खोदें।\n- गड्ढे के किनारे से मिट्टी की एक पतली परत खुरच लें।\n- सभी नमूनों को मिलाकर आधा किलो मिट्टी साफ थैली में भरकर जांच प्रयोगशाला भेजें।"
    },
    {
        "query": "How can I improve acidic soil?",
        "response": "To reclaim acidic soil (pH < 6.0):\n- Apply agricultural lime (Calcium Carbonate) based on soil test recommendations (typically 2 to 5 tonnes/ha depending on clay content).\n- Ensure balanced use of organic manures, compost, and green manuring (e.g., Dhaincha) to buffer soil pH naturally."
    },
    
    # Government Schemes
    {
        "query": "पीएम-किसान (PM-KISAN) योजना के तहत कितनी वित्तीय सहायता मिलती है?",
        "response": "पीएम-किसान योजना के तहत पात्र किसान परिवारों को प्रति वर्ष ₹6,000 की वित्तीय सहायता प्रदान की जाती है। यह राशि ₹2,000 की तीन समान किश्तों में सीधे किसानों के बैंक खातों (DBT) में भेजी जाती है।"
    },
    {
        "query": "What is PMFBY and how much is the premium rate for crops?",
        "response": "PMFBY stands for Pradhan Mantri Fasal Bima Yojana, a crop insurance scheme. The farmer premium shares are:\n- Kharif Crops: 2.0% of sum insured.\n- Rabi Crops: 1.5% of sum insured.\n- Annual Commercial/Horticultural Crops: 5.0% of sum insured. The government pays the remaining premium subsidy."
    }
]

# ChatML Formatting template for Qwen 2.5
SYSTEM_PROMPT = "You are KrishiMitra AI, an expert agricultural advisor for Indian farmers."

def format_to_chatml(query, response):
    """Formats raw QA into Qwen ChatML JSON structure."""
    return {
        "text": f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n{response}<|im_end|>"
    }

def convert_kcc_csv(csv_path, output_jsonl_path):
    """
    Utility to parse downloaded Kisan Call Center CSV logs.
    Adapt the keys to match your CSV headers.
    """
    if not os.path.exists(csv_path):
        print(f"ℹ️  No KCC CSV found at '{csv_path}'. Skipping CSV parsing.")
        return 0
    
    count = 0
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f_in, \
         open(output_jsonl_path, "a", encoding="utf-8") as f_out:
        
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
            print(f"⚠️ Could not identify query/answer columns automatically in {csv_path}. Skipping.")
            return 0
            
        print(f"💡 Using columns: Query='{query_col}', Answer='{answer_col}', Crop='{crop_col or 'None'}'")

        for row in reader:
            query = (row.get(query_col) or "").strip()
            answer = (row.get(answer_col) or "").strip()
            crop = (row.get(crop_col) or "").strip() if crop_col else ""
            
            if query and answer:
                # Augment prompt context slightly if crop name is available
                full_query = query
                if crop and crop.lower() not in query.lower():
                    full_query = f"Crop: {crop}. Question: {query}"
                
                chat_data = format_to_chatml(full_query, answer)
                f_out.write(json.dumps(chat_data, ensure_ascii=False) + "\n")
                count += 1
                
    print(f"✅ Converted {count} KCC CSV rows to instruction-tuning format.")
    return count

def main():
    output_path = "dataset_prepared.jsonl"
    
    # 1. Write seed data
    with open(output_path, "w", encoding="utf-8") as f:
        for item in SEED_DATA:
            chat_data = format_to_chatml(item["query"], item["response"])
            f.write(json.dumps(chat_data, ensure_ascii=False) + "\n")
            
    print(f"✅ Generated starter seed dataset with {len(SEED_DATA)} high-quality samples.")
    
    # 2. Convert any downloaded CSV log files
    # Download KCC logs from Kaggle / AIKosh, name it 'kcc_raw.csv' and run the script
    convert_kcc_csv("kcc_raw.csv", output_path)
    
    print(f"\n🎉 Dataset ready! File written to: {os.path.abspath(output_path)}")
    print("   Upload this file alongside train.py to your GPU environment to start training.")

if __name__ == "__main__":
    main()
