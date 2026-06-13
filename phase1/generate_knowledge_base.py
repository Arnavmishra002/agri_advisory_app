#!/usr/bin/env python3
"""
KrishiMitra AI — Knowledge Base Generator
==========================================
Uses local Qwen 2.5 7B (via Ollama) to generate all knowledge base files.
ZERO cloud API cost. Run once, generates ~15 comprehensive agricultural documents.

Usage:
    cd /Users/arnavmishra/ai/agri_advisory_app/phase1
    python3 generate_knowledge_base.py

Prerequisites:
    - Ollama running: ollama serve
    - Model pulled: ollama pull qwen2.5:7b
"""

import json
import os
import sys
import time
from pathlib import Path

import urllib.request
import urllib.error

OLLAMA_URL  = "http://localhost:11434/api/generate"
MODEL       = "qwen2.5:7b"
KB_DIR      = Path(__file__).parent / "knowledge_base"

# ── Qwen system instruction (prepended to every prompt) ──────────────────────
SYSTEM = (
    "You are a senior agricultural scientist at ICAR (Indian Council of Agricultural Research). "
    "Write detailed, accurate, practical farming guides for Indian farmers. "
    "Always include: specific variety names, exact chemical doses (g/L or kg/ha), "
    "Economic Threshold Levels (ETL) for pests, ICAR/CIB&RC approved pesticide names, "
    "fertilizer split schedules, critical irrigation timings, and MSP 2024-25 values. "
    "Format as a structured reference document with clear headings and bullet points."
)

# ── All knowledge base topics to generate ────────────────────────────────────
TOPICS = [
    # ── CROPS ────────────────────────────────────────────────────────────────
    {
        "file": "crops/sugarcane_icar.txt",
        "title": "Sugarcane (Saccharum officinarum)",
        "prompt": (
            "Write a comprehensive ICAR Package of Practices for Sugarcane farming in India. "
            "Include: (1) Varieties — CoC-671, CoJ-64, Co-86032, CoC-24, suitable states. "
            "(2) Planting — sets planting Oct-Dec and Jan-Feb, spacing 90cm rows, seed rate 35-40 quintals/ha, "
            "sett treatment Aregasan 3% or Carbendazim 0.1% for 10 min. "
            "(3) Fertilizer — N:P:K 250:100:120 kg/ha for irrigated crop, split N application schedule at planting, "
            "3 months, 5 months. Zinc sulphate 25 kg/ha. "
            "(4) Irrigation — 8-10 irrigations, critical at germination and grand growth period. "
            "(5) Pests — Pyrilla (leaffhopper) ETL 10/leaf control with Dimethoate; "
            "Early Shoot Borer ETL 10% dead shoots control with Chlorpyrifos granules; "
            "Internode Borer control with Fipronil 0.3GR; "
            "Woolly aphid control with Dimethoate 30EC 1L/ha. "
            "(6) Diseases — Red Rot control with hot water seed treatment 50C 2h; "
            "Wilt use disease-free seed; Smut control Carbendazim seed treatment; "
            "Ratoon Stunting Disease control hot water treatment. "
            "(7) Harvesting — harvest at 10-12 months, sucrose content 12-14%. "
            "(8) Yield 600-800 quintals/ha irrigated. "
            "(9) FRP (Fair and Remunerative Price) 2024-25: Rs 340 per quintal."
        ),
    },
    {
        "file": "crops/groundnut_millets.txt",
        "title": "Groundnut, Bajra, Jowar",
        "prompt": (
            "Write comprehensive ICAR Package of Practices for three crops: "
            "(A) GROUNDNUT (Arachis hypogaea) Kharif crop: varieties TAG-24, K-6, GG-20; "
            "seed rate 80-100 kg/ha; spacing 30x10cm; seed treatment Thiram+Carbendazim; "
            "N:P:K 20:60:30 kg/ha all basal; Rhizobium inoculation; "
            "gypsum 500 kg/ha at pegging stage for calcium; "
            "3-4 irrigations, critical at pegging and pod filling; "
            "pests: Thrips ETL 15/plant control Dimethoate, Leaf miner control Quinalphos 25EC 1L/ha, "
            "Spodoptera control Chlorpyrifos; "
            "diseases: Tikka leaf spot Cercospora control Chlorothalonil 75WP 2g/L, "
            "Stem rot Sclerotium control Trichoderma; "
            "yield 15-20 q/ha rainfed, 25-30 q/ha irrigated; MSP 2024-25 Rs 6783/q. "
            "(B) BAJRA/Pearl Millet (Pennisetum glaucum) Kharif: varieties HHB-67 Improved, Pusa 322, Raj 171; "
            "seed rate 4-5 kg/ha; N:P:K 80:40:40 kg/ha; drought tolerant; "
            "pests: stem borer control granules in whorl; "
            "diseases: Downy mildew major — seed treatment Metalaxyl 6g/kg; "
            "yield 20-25 q/ha; MSP Rs 2625/q. "
            "(C) JOWAR/Sorghum (Sorghum bicolor) Kharif+Rabi: varieties CSH-16, SPV-462, M-35-1; "
            "seed rate 10-12 kg/ha; N:P:K 80:40:20 kg/ha; "
            "pests: Shoot fly ETL 10% dead hearts control Carbofuran 3G in whorl, "
            "Stem borer control same; "
            "diseases: Anthracnose, Grain mold control; "
            "yield 25-35 q/ha; MSP Rs 3371/q."
        ),
    },
    {
        "file": "crops/vegetables_extended.txt",
        "title": "Brinjal, Chilli, Cauliflower, Okra",
        "prompt": (
            "Write comprehensive ICAR Package of Practices for four vegetable crops: "
            "(A) BRINJAL (Solanum melongena): varieties Pusa Purple Long, Arka Nidhi, hybrids; "
            "spacing 60x45cm; N:P:K 150:75:75 kg/ha; "
            "pests: Shoot and Fruit Borer ETL 5% damage control Chlorpyrifos 20EC 2mL/L or Spinosad; "
            "Aphids and Whitefly control Imidacloprid; "
            "diseases: Phomopsis blight control Mancozeb 2.5g/L; "
            "yield 200-300 q/ha. "
            "(B) CHILLI (Capsicum annuum): varieties Pusa Jwala, LCA-235, hybrids; "
            "spacing 60x45cm; N:P:K 120:60:60 kg/ha; "
            "pests: Thrips control Spinosad 0.3mL/L, Mites control Abamectin, "
            "fruit borer control Emamectin benzoate; "
            "diseases: Anthracnose Colletotrichum control Copper oxychloride + Mancozeb, "
            "Powdery mildew control Sulphur 3g/L, Leaf curl virus control whitefly; "
            "yield 80-120 q/ha green chilli, 15-20 q/ha dry; MSP not fixed (market price). "
            "(C) CAULIFLOWER (Brassica oleracea botrytis): varieties Pusa Snowball K-1, Pusa Sharad; "
            "spacing 60x45cm; N:P:K 120:60:60 kg/ha + Boron 1 kg/ha; "
            "pests: Diamond-back moth control Bt 2 kg/ha or Spinosad; "
            "diseases: Black rot control Copper compounds; "
            "yield 200-300 q/ha. "
            "(D) OKRA/Bhindi (Abelmoschus esculentus): varieties Pusa A-4, Arka Anamika, VRO-6; "
            "spacing 45x30cm; N:P:K 100:60:60 kg/ha; "
            "pests: Jassids and Whitefly (YVMV vector) control Imidacloprid 17.8SL 0.3mL/L; "
            "Fruit borer control Profenofos+Cypermethrin; "
            "diseases: Yellow Vein Mosaic Virus control whitefly, use resistant varieties; "
            "yield 80-100 q/ha."
        ),
    },
    # ── SOIL AND FERTILIZERS ─────────────────────────────────────────────────
    {
        "file": "soil/soil_health_fertilizer_guide.txt",
        "title": "Soil Health, Fertilizers, Micronutrients",
        "prompt": (
            "Write a comprehensive soil health and fertilizer guide for Indian farmers. Include: "
            "(1) Soil pH scale: <4.5 very strongly acidic; 4.5-5.5 strongly acidic apply agricultural lime; "
            "5.5-6.0 moderately acidic apply lime; 6.0-7.5 optimal range for most crops; "
            "7.5-8.0 moderately alkaline apply gypsum 2-3 q/acre; >8.0 strongly alkaline apply gypsum 5 q/acre + pyrite. "
            "(2) How to read a Soil Health Card (SHC) — all 12 parameters tested: pH, EC, OC, N, P, K, S, Zn, B, Fe, Mn, Cu. "
            "Website soilhealth.dac.gov.in to get your card online. "
            "(3) NPK deficiency symptoms: N deficiency yellow leaves from bottom, apply Urea 46% N at 217 kg/ha per 100 kg N; "
            "P deficiency purple leaves, apply DAP 18-46-0 at 220 kg/ha per 100 kg P; "
            "K deficiency brown leaf margins, apply MOP 60% K at 167 kg/ha per 100 kg K. "
            "(4) Micronutrient deficiencies: Zinc — white-yellow stripes in young leaves, "
            "apply ZnSO4 21% at 25 kg/ha as basal or chelated Zn foliar 0.5%; "
            "Boron — hollow stems, poor pod set, apply Borax Na2B4O7 at 1-2 kg/ha or 0.2% foliar; "
            "Sulphur — young leaf yellowing, apply Gypsum at 200 kg/ha or Elemental S at 40 kg/ha — "
            "critical for mustard, onion, garlic, pulses; "
            "Iron — interveinal chlorosis, apply FeSO4 0.5% foliar spray. "
            "(5) Fertilizer types and nutrient content table: Urea 46-0-0; DAP 18-46-0; SSP 0-16-0 + 12% S; "
            "MOP 0-0-60; NPK 10-26-26; NPK 20-20-0; NPK 12-32-16; Ammonium sulphate 20-0-0 + 24% S. "
            "(6) Organic amendments: FYM 0.5% N applied 10 t/ha; Vermicompost 1.5-2% N applied 5 t/ha; "
            "Poultry manure 2-3% N applied 3 t/ha. "
            "(7) How to collect soil sample — instructions step by step, mix 20 spots per field, "
            "air dry, send 500g to Krishi Vigyan Kendra, cost Rs 20-50 per test."
        ),
    },
    {
        "file": "soil/irrigation_water_management.txt",
        "title": "Irrigation, Water Management, PM-KUSUM",
        "prompt": (
            "Write a comprehensive irrigation and water management guide for Indian farmers. Include: "
            "(1) Methods comparison: Flood/Furrow irrigation efficiency 40-50%; "
            "Sprinkler irrigation efficiency 70-80%, saves 30-35% water, subsidy available 50-80%; "
            "Drip irrigation efficiency 90-95%, saves 40-50% water, subsidy 55-90% under PMKSY; "
            "AWD (Alternate Wetting Drying) for paddy saves 25% water same yield. "
            "(2) Irrigation scheduling by crop: "
            "Wheat critical stages CRI 21 DAS, tillering 40 DAS, jointing 65 DAS, heading 80 DAS, grain fill 100 DAS; "
            "Rice maintain 5cm standing water, allow drying to hairline cracks then re-irrigate; "
            "Maize critical at knee-height V5 and silking R1; "
            "Cotton critical at square formation, flowering, boll development; "
            "Mustard 2 irrigations only at rosette and pod fill, never at flowering. "
            "(3) ET0 (Reference Evapotranspiration) interpretation: "
            "ET0 <3mm/day low demand; 3-5mm/day moderate; >5mm/day high demand — reduce irrigation interval. "
            "(4) Water quality: EC <0.7 dS/m safe; 0.7-3 dS/m marginal; >3 dS/m not suitable. "
            "(5) PM-KUSUM scheme: 90% subsidy on solar pumps — 30% central + 30% state + 30% bank loan, farmer pays only 10%; "
            "helpline 1800-180-3333; website pmkusum.mnre.gov.in; "
            "also solar panels on barren land with extra income from selling power to grid. "
            "(6) PMKSY (Pradhan Mantri Krishi Sinchayee Yojana): "
            "Har Khet Ko Pani and More Crop Per Drop; "
            "drip and sprinkler subsidy up to Rs 40,000/ha; "
            "website pmksy.gov.in. "
            "(7) Signs of over-irrigation: waterlogging, yellowing, root rot, soil crusting, yield loss; "
            "Signs of under-irrigation: leaf rolling in afternoon, wilting, poor flowering, small grain."
        ),
    },
    # ── PESTS AND DISEASES ───────────────────────────────────────────────────
    {
        "file": "pests/pesticide_safety_resistance.txt",
        "title": "Pesticide Safety, Resistance Management, Biopesticides",
        "prompt": (
            "Write a comprehensive pesticide safety and management guide for Indian farmers. Include: "
            "(1) Pesticide classification by WHO hazard — Class Ia Extremely hazardous (red label) like Monocrotophos, "
            "Class Ib Highly hazardous (red label) like Chlorpyrifos, "
            "Class II Moderately hazardous (yellow label) like Mancozeb, Imidacloprid, "
            "Class III Slightly hazardous (blue label) like Neem oil, Bt, "
            "Class IV Unlikely hazardous (green label) like Spinosad, Emamectin. "
            "(2) Mixing order in tank: Fill half water → add wettable powder → add EC → add SC → top up water → mix. "
            "Never mix: Copper compounds with organophosphates; alkaline + acidic materials; "
            "Bordeaux mixture with most pesticides. "
            "(3) Spray timing: Early morning 6-9 AM best; avoid noon; avoid before rain; "
            "flat fan nozzle for herbicides; hollow cone for fungicides; directed spray for soil pests. "
            "(4) PPE — full sleeve shirt, gloves, mask N95 or respirator, goggles, boots; wash clothes after spraying. "
            "(5) Pre-harvest intervals (PHI): Organophosphates 14-21 days; Pyrethroids 7-14 days; "
            "Carbendazim 7 days; Mancozeb 7 days; Imidacloprid 7-14 days; Bt day of harvest safe. "
            "(6) Resistance management IRAC groups: "
            "Group 1A carbamates; Group 1B organophosphates; Group 3 pyrethroids; Group 4 neonicotinoids; "
            "Group 5 spinosyns; Group 6 avermectins; Group 28 diamides. "
            "Rule: Never apply same group more than 2 consecutive sprays. Rotate groups. "
            "(7) Biopesticides — full list with doses: "
            "Beauveria bassiana 1.15WP at 2.5 kg/ha; "
            "Metarhizium anisopliae at 2.5 kg/ha for soil insects; "
            "Bt kurstaki (Dipel, Biobit) at 1 kg/ha for caterpillars only; "
            "HaNPV (Helicoverpa NPV) at 250 LE/ha; "
            "Neem oil 3000ppm at 5mL/L; "
            "Trichoderma viride at 4g/kg seed or 2.5 kg/ha soil; "
            "Pseudomonas fluorescens at 10g/kg seed. "
            "(8) Emergency first aid for pesticide poisoning: "
            "Remove contaminated clothing, wash skin with soap water, induce vomiting only for ingestion, "
            "nearest hospital Organophosphate antidote Atropine 2-4mg IV; "
            "Poison control: 1800-11-6767 (India toll free)."
        ),
    },
    {
        "file": "pests/crop_disease_diagnosis.txt",
        "title": "Disease Diagnosis and Treatment by Symptoms",
        "prompt": (
            "Write a crop disease diagnosis guide for Indian farmers — diagnosis by visible symptoms. "
            "Format as: SYMPTOM → LIKELY CAUSE → CONFIRM BY → TREATMENT. Include: "
            "(1) Yellow leaves: older leaves yellow bottom-up = Nitrogen deficiency apply Urea; "
            "all leaves pale yellow = Magnesium or Sulphur deficiency; "
            "interveinal yellow young leaves = Iron deficiency (chlorosis) apply FeSO4 foliar; "
            "yellow patches with water-soaked borders = bacterial disease copper spray; "
            "mosaic yellow pattern = virus disease control vector insect, no cure remove plants. "
            "(2) Wilting: sudden wilt one side = Fusarium or Verticillium wilt, cut stem see brown vascular; "
            "wilting + root rot at base = Phytophthora root rot drain field; "
            "wilting + white cottony base = Sclerotium wilt Trichoderma soil treatment; "
            "wilting afternoon recovery morning = drought stress irrigate. "
            "(3) Leaf spots: circular spots with yellow halo = Early blight Alternaria apply Mancozeb; "
            "water-soaked expanding irregular = Late blight Phytophthora spray Metalaxyl+Mancozeb immediately; "
            "powdery white coating on leaf = Powdery mildew apply Sulphur 3g/L or Hexaconazole; "
            "orange-red pustules on leaf = Rust disease apply Propiconazole 1mL/L; "
            "dark brown angular spots = Bacterial blight spray Copper oxychloride. "
            "(4) Stem problems: hollow stem = Boron deficiency apply Borax 1kg/ha; "
            "stem borer frass/sawdust = stem borer apply Chlorpyrifos granules in whorl; "
            "black sooty mold on stem = honeydew from sucking pest control pest first. "
            "(5) Fruit/pod problems: holes in fruit = fruit borer apply Emamectin benzoate; "
            "blossom drop = high temperature + humidity or Ca deficiency apply CaNO3; "
            "cracked fruit = irregular irrigation ensure uniform watering. "
            "(6) Root problems: knots on roots = Root-knot nematode Meloidogyne apply Carbofuran 3G 20 kg/ha or "
            "biocontrol Paecilomyces lilacinus; "
            "brown rotting roots = Pythium damping off apply Metalaxyl; "
            "healthy roots but poor growth = nutrient deficiency do soil test."
        ),
    },
    # ── GOVERNMENT SCHEMES ───────────────────────────────────────────────────
    {
        "file": "schemes/government_schemes_complete.txt",
        "title": "Government Schemes — PM-Kisan, PMFBY, KCC, PM-KUSUM, eNAM",
        "prompt": (
            "Write a comprehensive guide to all major Indian government agricultural schemes for farmers. "
            "For each scheme include: eligibility, benefit amount, how to apply, documents needed, website, helpline. "
            "(1) PM-KISAN (Pradhan Mantri Kisan Samman Nidhi): Rs 6000/year in 3 installments of Rs 2000; "
            "all small and marginal farmers; Aadhaar + bank account + land records needed; "
            "apply at pmkisan.gov.in or nearest CSC; check status pmkisan.gov.in/Rpt_BeneficiaryStatus; "
            "helpline 155261 or 1800-115-526. "
            "(2) PMFBY (Pradhan Mantri Fasal Bima Yojana): crop insurance; "
            "farmer premium 2% for Kharif, 1.5% for Rabi, 5% for horticulture; "
            "rest of premium paid by government; claim within 72 hours of crop damage; "
            "apply at pmfby.gov.in or bank/insurance company before cutoff date; "
            "helpline 14447. "
            "(3) KCC (Kisan Credit Card): short-term agricultural credit at 4% interest for first Rs 1.5 lakh; "
            "apply at any bank with land records, Aadhaar; credit limit based on land holding; "
            "valid 5 years with annual renewal; "
            "also covers post-harvest expenses and allied activities. "
            "(4) PM-KUSUM (Pradhan Mantri Kisan Urja Suraksha evam Utthaan Mahabhiyan): "
            "solar pump: farmer pays only 10%, government 60%, bank loan 30%; "
            "also solar panels on barren land, farmer sells surplus power; "
            "apply through state nodal agencies; website pmkusum.mnre.gov.in. "
            "(5) Soil Health Card (SHC): free soil test every 3 years; "
            "12 nutrients tested; recommendations printed on card; "
            "apply at soilhealth.dac.gov.in or nearest soil testing lab. "
            "(6) eNAM (Electronic National Agriculture Market): online mandi platform; "
            "farmer can sell from any registered mandi in country; "
            "register at enam.gov.in or through FPO; "
            "better price discovery, transparent bidding. "
            "(7) MIDH (Mission for Integrated Development of Horticulture): "
            "subsidy on horticultural crops, drip irrigation, cold storage, processing; "
            "apply through horticulture department. "
            "(8) National Food Security Mission: subsidy on seeds, fertilizers for rice, wheat, pulses. "
            "(9) Paramparagat Krishi Vikas Yojana (PKVY): Rs 50,000/ha for 3 years for organic farming; "
            "cluster approach 50 farmers per group."
        ),
    },
    # ── WEATHER AND CALENDAR ─────────────────────────────────────────────────
    {
        "file": "weather/crop_weather_calendar.txt",
        "title": "Crop Calendar, Weather Advisory, Season Guide",
        "prompt": (
            "Write a comprehensive crop calendar and weather advisory guide for Indian farmers. Include: "
            "(1) Indian agricultural seasons: "
            "Kharif (June-November): rice, maize, cotton, soybean, groundnut, bajra, jowar, arhar, moong, urad, sugarcane; "
            "Rabi (October-March): wheat, mustard, gram, lentil, barley, potato, onion; "
            "Zaid (March-June): watermelon, muskmelon, cucumber, moong, summer vegetables. "
            "(2) Month-wise farm operations calendar for major crops: "
            "January: Rabi field operations, wheat topdress, mustard pod filling, irrigation; "
            "February: Wheat heading, aphid watch, rabi harvest preparation; "
            "March: Wheat harvest, summer crop sowing, land preparation; "
            "April: Summer crops, mango harvest, heat stress management; "
            "May: Pre-kharif land preparation, fertilizer procurement; "
            "June: Monsoon arrival, kharif sowing (rice nursery, maize, soybean), soil test; "
            "July: Transplanting rice, kharif weeding, pest scouting begins; "
            "August: Kharif crop growth, cotton boll formation, IPM spray schedule; "
            "September: Early kharif harvest, rabi preparation, soil moisture conservation; "
            "October: Rice harvest, rabi sowing begins (wheat, mustard, gram), seed procurement; "
            "November: Wheat sowing peak, potato planting, rabi fertilizer application; "
            "December: Rabi crop establishment, wheat tillering, irrigation schedule. "
            "(3) Weather-based advisories: "
            "High temperature >40C: irrigate early morning/evening, mulching, shade nets; "
            "Low temperature <5C: cover nursery beds, avoid N application before frost; "
            "Heavy rain >100mm/day: ensure drainage, delay spraying, watch for fungal diseases; "
            "Dry spell >15 days without rain: irrigation scheduling, moisture conservation by mulching; "
            "High humidity >85% for 3 days: fungal disease spray calendar activate. "
            "(4) IMD weather services for farmers: "
            "Meghdoot app — free weather forecast for farmers in regional languages; "
            "Kisan portal mausam.imd.gov.in/farmer; "
            "Gramin Krishi Mausam Sewa (GKMS) district-level 5-day forecast; "
            "helpline 1800-11-8080 (toll free IMD farmer weather helpline)."
        ),
    },
    # ── MARKET INFORMATION ───────────────────────────────────────────────────
    {
        "file": "schemes/msp_market_prices_2024.txt",
        "title": "MSP 2024-25, Mandi Prices, Selling Guide",
        "prompt": (
            "Write a comprehensive market and MSP guide for Indian farmers for 2024-25. Include: "
            "(1) MSP 2024-25 complete list (Cabinet approved): "
            "Wheat Rs 2275/q; Rice/Paddy common Rs 2300/q, Grade A Rs 2320/q; "
            "Maize Rs 2090/q; Jowar hybrid Rs 3371/q, maldandi Rs 3421/q; "
            "Bajra Rs 2625/q; Ragi Rs 3846/q; "
            "Arhar/Tur Rs 7000/q; Moong Rs 8682/q; Urad Rs 7400/q; "
            "Gram Rs 5440/q; Lentil Rs 6425/q; "
            "Mustard/Rapeseed Rs 5650/q; Groundnut Rs 6783/q; Sunflower Rs 7280/q; "
            "Soybean Rs 4892/q; "
            "Cotton medium staple Rs 6620/q, long staple Rs 7020/q; "
            "Sugarcane FRP Rs 340/q. "
            "(2) Difference between MSP and mandi price — MSP is government guaranteed minimum, "
            "actual mandi price can be higher or lower, MSP procurement through FCI/NAFED. "
            "(3) How to sell at MSP procurement: "
            "Register on PM-AASHA portal; "
            "contact nearest Mandi/APMC or FCI procurement center; "
            "bring KCC, bank passbook, land records; "
            "payment within 3 days of delivery to bank account. "
            "(4) eNAM (enam.gov.in) — electronic mandi for better prices: "
            "register at local mandi, get APMC license; "
            "upload sample photos and quality details; "
            "buyers bid online; payment same day; "
            "helpline 1800-270-0224. "
            "(5) Agmarknet (agmarknet.gov.in) — check today's mandi prices before selling: "
            "search by commodity + state + mandi; "
            "data updated daily from APMC markets across India. "
            "(6) FPO (Farmer Producer Organisation) advantages: "
            "collective bargaining, bulk selling, input procurement discount, "
            "processing and export access; "
            "how to form an FPO through NABARD or SFAC. "
            "(7) Post-harvest storage tips: "
            "grain moisture must be below 12% before storage; "
            "use airtight HDPE bags or pucca godown; "
            "Celphos (Aluminium phosphide) for fumigation 3g/tonne under tarpaulin; "
            "Warehousing Corporation of India storage facility available at district level."
        ),
    },
    # ── ADVANCED TOPICS ──────────────────────────────────────────────────────
    {
        "file": "soil/organic_farming_guide.txt",
        "title": "Organic Farming, Vermicompost, Biofertilizers",
        "prompt": (
            "Write a comprehensive organic farming guide for Indian farmers. Include: "
            "(1) Principles of organic farming — no synthetic pesticides/fertilizers, "
            "soil health improvement, biodiversity, sustainability. "
            "(2) Biofertilizers — complete guide: "
            "Rhizobium (legume N-fixation) 5g/kg seed; "
            "Azotobacter (non-legume N-fixation) 5g/kg seed or 5kg/ha soil; "
            "PSB (Phosphorus Solubilising Bacteria) 5g/kg seed; "
            "KSB (Potassium Solubilising Bacteria) 5g/kg seed; "
            "how to apply seed treatment, soil application, drip injection; "
            "shelf life 6 months in cool dark place. "
            "(3) Compost making: raw materials FYM + crop residue + kitchen waste; "
            "C:N ratio must be 25-30:1; "
            "aerobic composting 90 days; "
            "Trichoderma enriched compost add 1kg Trichoderma per tonne. "
            "(4) Vermicompost: use Eisenia fetida worms; "
            "beds 1m x 2m x 0.3m deep; moisten regularly; "
            "60-90 days ready; harvest dark crumbly material; "
            "apply 5 tonnes/ha improves water holding capacity. "
            "(5) Jeevamrit and Beejamrit (natural fermented inputs from Subhash Palekar natural farming): "
            "Jeevamrit recipe: 200L water + 10kg cow dung + 5-10L cow urine + 2kg jaggery + 2kg flour + handful soil; "
            "ferment 48 hours, apply 200L/acre through irrigation. "
            "(6) Green manuring: Sesbania aculeata (Dhaincha) sow, incorporate at 45 days adds 60 kg N/ha; "
            "Sunhemp (Crotalaria juncea) 50 kg N/ha; "
            "Cowpea as green manure; Sunflower stubble incorporation. "
            "(7) PKVY scheme provides Rs 50,000/ha subsidy for organic conversion over 3 years. "
            "(8) Certification: Participatory Guarantee System (PGS) India, NPOP for export; "
            "apply through state agriculture department."
        ),
    },
    {
        "file": "crops/horticulture_fruits.txt",
        "title": "Mango, Banana, Citrus, Pomegranate",
        "prompt": (
            "Write a comprehensive ICAR guide for major fruit crops in India. Include: "
            "(A) MANGO (Mangifera indica): varieties Alphonso, Dasheri, Langra, Totapuri, Kesar; "
            "planting 10x10m spacing, pit 1x1x1m; "
            "fertilizer mature tree 1kg N + 0.5kg P + 1kg K per year; "
            "irrigation critical at fruit development; "
            "flowering November-January, harvest April-July depending variety; "
            "pests: Mango hoppers control Imidacloprid 0.5 mL/L; "
            "Stone weevil control; "
            "diseases: Anthracnose spray Carbendazim 1g/L at bud burst; "
            "Powdery mildew spray Sulphur 3g/L; "
            "Malformation control Naphthalene Acetic Acid 200 ppm at panicle emergence. "
            "(B) BANANA (Musa sp.): varieties Cavendish Grand Naine, Robusta, Poovan, Nendran; "
            "planting 1.8x1.5m; tissue culture plants preferred; "
            "fertilizer N:P:K 200:60:300 g per plant per year split 3-4 applications; "
            "irrigation daily or alternate days, 20-25L per plant; "
            "harvest 11-15 months; "
            "pests: Banana stem weevil, nematodes; "
            "diseases: Panama wilt (Fusarium oxysporum) no cure use resistant varieties; "
            "Sigatoka leaf spot spray Mancozeb 2g/L + oil. "
            "(C) CITRUS (Citrus spp.): varieties Kinnow, Nagpur Mandarin, Mosambi, Acid lime; "
            "planting 6x6m; fertilizer mature tree 600g N + 200g P + 400g K per year; "
            "irrigation 15-20 days interval; "
            "pests: Citrus psylla vector of Greening disease; Citrus leafminer; "
            "diseases: Canker spray Copper oxychloride 3g/L; "
            "Greening (Huanglongbing) no cure — remove infected trees. "
            "(D) POMEGRANATE (Punica granatum): varieties Bhagwa, Ganesh, Mridula; "
            "planting 5x4m; fertilizer 625g N + 250g P + 250g K per plant per year; "
            "drought tolerant but needs 4-6 irrigations; "
            "pests: Pomegranate butterfly control Quinalphos; Thrips control Spinosad; "
            "diseases: Bacterial blight spray Copper + Streptomycin; "
            "Fruit cracking — calcium spray + regular irrigation."
        ),
    },
    {
        "file": "pests/fall_armyworm_detailed.txt",
        "title": "Fall Armyworm — Detailed Management Guide",
        "prompt": (
            "Write a comprehensive management guide for Fall Armyworm (Spodoptera frugiperda) — "
            "the new invasive pest that arrived in India in 2018. Include: "
            "(1) Identification — distinguish from common armyworm and Spodoptera litura: "
            "FAW has inverted Y on head, 4 spots in square pattern on 8th abdominal segment; "
            "larvae up to 4.5cm, brown-green with stripes. "
            "(2) Life cycle: egg mass 100-200 eggs on leaf, hatch 2-3 days; "
            "larval stage 14-22 days, 6 instars; pupa in soil 8-9 days; "
            "adult moth female lays 1000-2000 eggs lifetime, migrates hundreds of km. "
            "(3) Host range — maize most preferred, also sorghum, rice, sugarcane, cotton, tomato, groundnut, wheat. "
            "(4) Damage symptoms: "
            "Window pane damage — transparent patches on young leaves; "
            "Whorl damage — frass (sawdust-like excreta) in whorl; "
            "Ear damage — larvae inside cob silk. "
            "(5) Scouting and ETL: scout twice weekly at early crop stages; "
            "ETL: 5% plants showing fresh whorl damage (vegetative stage); "
            "2 eggs/plants or 1 larva/plant (early). "
            "(6) Management — IPM approach: "
            "CULTURAL: early sowing, crop rotation, deep ploughing; "
            "MECHANICAL: hand picking egg masses, pheromone traps (FAW specific lure) 5-10/ha; "
            "BIOLOGICAL: Trichogramma pretiosum or T. chilonis releases 1 lakh cards/ha; "
            "Bacillus thuringiensis kurstaki 2kg/ha directed into whorl for early instar; "
            "Beauveria bassiana 1.15WP 2.5 kg/ha; "
            "Nomuraea rileyi 2.5 kg/ha; "
            "NPV (nuclear polyhedrosis virus) for fall armyworm; "
            "CHEMICAL (only if biological fails, instar 1-3 only): "
            "Spinetoram 11.7SC 0.5mL/L BEST choice; "
            "Emamectin benzoate 5SG 0.4g/L; "
            "Chlorantraniliprole 18.5SC 0.4mL/L; "
            "Chlorpyrifos 20EC 2.5L/ha only large instar. "
            "(7) Spray tips: spray into whorl in early morning; "
            "add sand to increase contact time in whorl; "
            "do NOT spray pyrethroids — ineffective and cause secondary pest flare-up. "
            "(8) Resistance monitoring: if Spinetoram fails after 2 sprays switch to Chlorantraniliprole."
        ),
    },
    {
        "file": "crops/spices_turmeric_ginger_garlic.txt",
        "title": "Turmeric, Ginger, Garlic, Coriander",
        "prompt": (
            "Write ICAR Package of Practices for important spice crops in India. "
            "(A) TURMERIC (Curcuma longa): major states Telangana, AP, Odisha, TN, Maharashtra; "
            "varieties Pratibha, Suguna, Rajendra Sonia; "
            "planting April-June in ridges and furrows; "
            "seed rhizomes 2500-3000 kg/ha; spacing 45x25cm; "
            "N:P:K 120:60:120 kg/ha; organic manure 20-25 tonnes/ha; "
            "irrigation every 7-10 days, 15-20 irrigations needed; "
            "major pest: shoot borer Conogethes punctiferalis control Chlorpyrifos 2.5mL/L; "
            "rhizome rot Pythium control Metalaxyl+Mancozeb, avoid waterlogging; "
            "leaf blotch Taphrina control Mancozeb 2.5g/L; "
            "harvest 7-9 months; boil rhizomes 45-60 min, dry in sun 10-15 days; "
            "yield 200-300 q/ha fresh (reduce 5:1 for dry). "
            "(B) GINGER (Zingiber officinale): varieties Maran, Nadia, Suprabha; "
            "planting March-May; seed rhizomes 1500-1800 kg/ha; spacing 30x20cm; "
            "N:P:K 75:50:50 kg/ha + organic manure 25 t/ha; "
            "shade crop ideal, needs 60-70% shade; "
            "soft rot Pythium aphanidermatum most serious disease — "
            "seed treatment Metalaxyl 6g/kg + field application Metalaxyl 750g/ha at planting; "
            "bacterial wilt Ralstonia no treatment, destroy infected plants; "
            "yield 150-200 q/ha fresh. "
            "(C) GARLIC (Allium sativum): varieties Yamuna Safed (G-50), G-1, Agrifound White; "
            "sowing October-November in North India; spacing 15x7.5cm; "
            "bulb splitting (seed) 400-500 kg/ha; "
            "N:P:K 100:50:50 kg/ha; basal all P+K + 30kg N; top dress 70kg N in 2 splits; "
            "irrigation 8-10 times, stop 20 days before harvest; "
            "thrips control Spinosad or Dimethoate; "
            "purple blotch control Iprodione+Mancozeb; "
            "harvest April-May; dry 2-3 weeks in shade; "
            "yield 100-150 q/ha. "
            "(D) CORIANDER (Coriandrum sativum): varieties Rajendra Swati, RCr-41, CS-6; "
            "sowing October-November; broadcast or line sowing 15-20 kg/ha seed; "
            "N:P:K 30:30:20 kg/ha; 3-4 irrigations; "
            "stem gall control remove and burn infected plants; "
            "powdery mildew control Karathane 1mL/L; "
            "yield 8-12 q/ha dry seed."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════════
    # BATCH 2 — 20 additional topics for complete query coverage
    # ══════════════════════════════════════════════════════════════════════════

    # ── MORE CROPS ────────────────────────────────────────────────────────────
    {
        "file": "crops/wheat_varieties_zone_wise.txt",
        "title": "Wheat Varieties Zone-wise India",
        "prompt": (
            "Write a comprehensive zone-wise wheat variety selection guide for India. "
            "Format each zone as: ZONE → STATES → RECOMMENDED VARIETIES → WHY. "
            "Include: "
            "(1) North-West Plain Zone (Punjab, Haryana, Delhi, western UP, Rajasthan): "
            "HD-3086, PBW-343, WH-1105, PBW-621; sowing Nov 1-15; "
            "characteristics rust resistance, high yield 50-60 q/ha. "
            "(2) North-East Plain Zone (eastern UP, Bihar, Jharkhand, West Bengal): "
            "HD-2781, K-307, GW-322, HI-8498; terminal heat tolerant; sowing Nov 10-25. "
            "(3) Central Zone (MP, Chhattisgarh, Gujarat, Rajasthan): "
            "GW-496, HI-8663, MP-4010, RAJ-4120; drought tolerant; sowing Nov 15-30. "
            "(4) Peninsular Zone (Maharashtra, Karnataka, AP, TN): "
            "NW-1014, HI-977, K-9107; short-duration 100-110 days; late sowing adapted. "
            "(5) Hilly Zones (Himachal, Uttarakhand, J&K): "
            "HS-507, VL-804, VL-892; cold tolerant; sowing Oct-Nov. "
            "(6) Irrigated vs rainfed variety choice. "
            "(7) Late sowing varieties (after Dec 15): NW-1014, HD-2985, Raj-4120 for all zones. "
            "(8) Variety resistance to diseases: yellow rust, brown rust, loose smut. "
            "Include seed cost, availability source (NSC, IARI, state farms)."
        ),
    },
    {
        "file": "crops/rice_varieties_zone_wise.txt",
        "title": "Rice Varieties, Transplanting and Direct Seeding",
        "prompt": (
            "Write a comprehensive rice cultivation guide covering varieties and methods. "
            "(1) VARIETY SELECTION by state: "
            "Punjab/Haryana: PR-126 (early, saves water), PR-121, Pusa-44 (avoid — late, water-hungry); "
            "UP/Bihar: Swarna, Samba Masuri, Pusa Basmati-1121, Pusa Basmati-1509; "
            "West Bengal/Assam: Minikit, Satabdi, Gitesh; "
            "Maharashtra/AP/Telangana: BPT-5204, MTU-1010, Swarna Sub1 (flood tolerant); "
            "Tamil Nadu: ADT-43, CO-51, TRY-3; "
            "Karnataka: Jyothi, KMP-175, Cauvery. "
            "(2) DIRECT SEEDED RICE (DSR): "
            "Method: seeds drilled in puddled or dry field; "
            "saves 15-20 days nursery, 25-30% water, reduces labor 40%; "
            "herbicide pre-emergence Pendimethalin 30EC 3.3L/ha within 3 DAS; "
            "risk: more weed pressure, need 10% extra seed. "
            "(3) SRI (System of Rice Intensification): "
            "single seedling 8-12 days old, 25x25cm spacing, "
            "alternate wet-dry water management, compost 5t/ha; "
            "yield 20-25% higher than conventional. "
            "(4) Basmati rice cultivation: "
            "varieties Pusa Basmati-1121, Pusa Basmati-1509, Traditional Basmati; "
            "export quality requirements GI tag; "
            "grain length 7.5mm+, aroma essential; "
            "low N (80kg/ha) for quality; harvest at 85% maturity. "
            "(5) RICE-WHEAT ROTATION: "
            "timely harvest of rice to sow wheat Nov 1-15; "
            "Happy Seeder technology for stubble management without burning."
        ),
    },
    {
        "file": "crops/barley_lentil_sunflower.txt",
        "title": "Barley, Lentil, Sunflower",
        "prompt": (
            "Write ICAR Package of Practices for three Rabi/Kharif crops: "
            "(A) BARLEY (Hordeum vulgare): varieties RD-2552, BH-393, K-141; "
            "sowing Oct 25-Nov 15; seed rate 100 kg/ha; spacing 22.5cm rows; "
            "N:P:K 60:30:20 kg/ha; 2-3 irrigations; most drought tolerant cereal; "
            "pests: Aphid control Dimethoate; diseases: Stripe disease seed treatment; "
            "uses: malt industry, cattle feed; yield 30-40 q/ha; MSP Rs 1735/q. "
            "(B) LENTIL (Lens culinaris): varieties Pant L-406, DPL-62, K-75; "
            "sowing Oct 15-Nov 15; seed rate 35-40 kg/ha; spacing 30x10cm; "
            "N:P:K 20:50:20 kg/ha + Rhizobium inoculation; rainfed mostly; "
            "pests: Pod borer ETL 10% damage control Quinalphos; "
            "diseases: Stemphylium blight control Zineb 2.5g/L; Rust control Mancozeb; "
            "yield 10-15 q/ha; MSP Rs 6425/q. "
            "(C) SUNFLOWER (Helianthus annuus): Rabi+Kharif; varieties KBSH-44, MSFH-17, Sungold; "
            "seed rate 5 kg/ha hybrid; spacing 60x30cm; "
            "N:P:K 90:60:60 kg/ha + Boron 1 kg/ha (critical for seed setting); "
            "5-6 irrigations critical at 30 DAS, bud stage, flowering, seed fill; "
            "cross pollination required — plant 1 row every 4 rows alternate variety; "
            "pests: Capitulum borer control Chlorpyrifos; head moth Helicoverpa control; "
            "diseases: Downy mildew seed treatment Metalaxyl; Alternaria control Mancozeb; "
            "harvest when back of head turns yellow; "
            "yield 15-18 q/ha; MSP Rs 7280/q."
        ),
    },
    {
        "file": "crops/crop_rotation_intercropping.txt",
        "title": "Crop Rotation, Intercropping, Mixed Farming",
        "prompt": (
            "Write a comprehensive guide on crop rotation, intercropping, and mixed farming systems for India. "
            "(1) BENEFITS OF CROP ROTATION: "
            "breaks pest-disease cycles, improves soil health, reduces input cost, "
            "legal requirement for some crop insurance. "
            "(2) RECOMMENDED ROTATIONS by region: "
            "Punjab/Haryana: Rice-Wheat (most common but depletes soil) → better: Maize-Wheat or Sugarcane-Wheat; "
            "MP/Rajasthan: Soybean-Wheat, Cotton-Gram, Maize-Mustard; "
            "Maharashtra: Cotton-Gram, Soybean-Safflower; "
            "South India: Rice-Groundnut, Rice-Sunflower, Maize-Chickpea; "
            "always include legume in rotation to fix N. "
            "(3) INTERCROPPING SYSTEMS with row ratios: "
            "Maize + Soybean (2:2) — most profitable, both Kharif; "
            "Sugarcane + Onion (plant-to-plant); "
            "Cotton + Moong (1:1); "
            "Wheat + Mustard (9:1); "
            "Arhar/Pigeonpea + Soybean (1:2); "
            "Groundnut + Castor (6:2). "
            "(4) MULTIPLE CROPPING INDEX (MCI): "
            "3 crops/year in irrigated areas; MCI > 200 = good; "
            "Green manure crop counts toward MCI. "
            "(5) MIXED FARMING — integration with livestock: "
            "crop residue as fodder, animal dung as manure, reduces input cost 25-30%; "
            "NABARD Kisan Credit Card covers livestock purchase. "
            "(6) Cover crops and green manure integration schedule month-wise."
        ),
    },

    # ── FERTILIZERS AND SOIL IN DEPTH ─────────────────────────────────────────
    {
        "file": "soil/fertilizer_application_schedule.txt",
        "title": "Crop-wise Fertilizer Schedules and Split Doses",
        "prompt": (
            "Write a comprehensive fertilizer application schedule guide for all major Indian crops. "
            "Format as: CROP → TOTAL DOSE (N:P:K kg/ha) → BASAL → TOP DRESS 1 → TOP DRESS 2 → FOLIAR. "
            "Include: "
            "Wheat: 120:60:40; basal P+K+40N; TD1 40N at CRI; TD2 40N at tillering. "
            "Rice transplanted: 100:50:50; basal P+K+25N; TD1 37.5N at tillering; TD2 37.5N at PI. "
            "Maize hybrid: 150:75:75; basal all P+K+50N; TD1 50N at V5; TD2 50N at tasseling. "
            "Cotton: 120:60:60+Boron; basal P+K+30N; TD1 45N at squaring; TD2 45N at boll. "
            "Mustard: 60:40:30+Sulphur; all basal P+K+S + 30N; TD1 30N at rosette. "
            "Soybean: 20:80:40; all basal. "
            "Chickpea: 20:60:20; all basal. "
            "Sugarcane: 250:85:120; split 4 applications. "
            "Tomato: 150:75:75+Ca; basal P+K+50N; 3 top dresses. "
            "Potato: 180:120:120; split at planting and earthing-up. "
            "Include: "
            "How to calculate actual fertilizer quantity from nutrient dose; "
            "Urea calculation: N required ÷ 0.46; "
            "DAP calculation: P required ÷ 0.46 (for P content); "
            "MOP calculation: K required ÷ 0.60; "
            "Neem-coated urea (NCU) instructions; "
            "Liquid fertilizers — Nano Urea 500mL bottle = 50kg Urea, spray 2-4mL/L."
        ),
    },
    {
        "file": "soil/nano_fertilizers_new_technology.txt",
        "title": "Nano Fertilizers, Liquid Fertilizers, New Technology",
        "prompt": (
            "Write a guide on new fertilizer technologies available in India 2024. "
            "(1) NANO UREA (IFFCO): "
            "500mL bottle replaces one bag of Urea (50kg); "
            "foliar spray 2-4mL/L water at tillering and other critical stages; "
            "reduces ground-level urea requirement by 50%; "
            "approved by Government of India 2021; "
            "price Rs 225/500mL bottle; "
            "application: 2 sprays replace 1 top-dressing. "
            "(2) NANO DAP (IFFCO): "
            "500mL replaces 25kg DAP; seed treatment 5-10mL/kg seed or foliar spray; "
            "approved 2023. "
            "(3) LIQUID BIOFERTILIZERS: "
            "Rhizobium liquid 1L/10kg seed; Azotobacter liquid 1L/acre; "
            "longer shelf life than powder biofertilizers. "
            "(4) WATER-SOLUBLE FERTILIZERS (WSF): "
            "for drip irrigation — 19:19:19 NPK; 0:52:34; 13:0:45; "
            "completely soluble, no clogging; use 2-4 kg/100L water in drip. "
            "(5) SULPHUR-COATED UREA (SCU): "
            "slow release, reduces leaching; "
            "useful for sandy soils, paddy, sugarcane. "
            "(6) MICRONUTRIENT MIXTURES: "
            "Multi-micronutrient (Zn+B+Fe+Mn+Cu+Mo) foliar spray; "
            "available as Chelamin, Micromax, Multiplex brands; "
            "2g/L foliar spray at vegetative stage. "
            "(7) PGPR (Plant Growth Promoting Rhizobacteria): "
            "Pseudomonas fluorescens + Bacillus subtilis combined; "
            "seed treatment improves germination and early growth 15-20%."
        ),
    },
    {
        "file": "soil/soil_testing_interpretation.txt",
        "title": "Soil Testing, Soil Health Card Interpretation, pH Management",
        "prompt": (
            "Write a detailed guide on soil testing and Soil Health Card interpretation for Indian farmers. "
            "(1) HOW TO COLLECT SOIL SAMPLE correctly: "
            "collect from 0-15cm depth (topsoil) and 15-30cm (sub-soil); "
            "take 15-20 sample points per field using zigzag pattern; "
            "avoid spots near trees, paths, fertilizer storage; "
            "mix all sub-samples in clean bucket, quarter out 500g; "
            "fill in sample form: farmer name, survey number, crop, previous crop, irrigation source; "
            "cost: Rs 20-50 at KVK or soil testing lab. "
            "(2) SOIL HEALTH CARD parameters and optimal ranges: "
            "pH: 6.0-7.5 optimal; "
            "EC: <0.8 dS/m safe; 0.8-1.6 marginal; >1.6 saline; "
            "Organic Carbon (OC%): <0.5 very low; 0.5-0.75 low; >0.75 adequate; "
            "Available Nitrogen: Low <280 kg/ha; Med 280-560; High >560; "
            "Available Phosphorus (P2O5): Low <10 kg/ha; Med 10-25; High >25; "
            "Available Potassium (K2O): Low <108 kg/ha; Med 108-280; High >280; "
            "Sulphur: <10 ppm deficient; "
            "Zinc: <0.6 ppm deficient — very common in India; "
            "Boron: <0.5 ppm deficient; "
            "Iron: <4.5 ppm deficient; Manganese: <2 ppm deficient. "
            "(3) pH CORRECTION step by step: "
            "Test pH first. For acidic soil pH < 6.0: "
            "calculate lime requirement = (target pH - current pH) × 1.5 tonnes/ha agricultural lime; "
            "apply 3-4 months before sowing; "
            "For alkaline soil pH > 7.5: "
            "apply Gypsum (CaSO4) 2-5 tonnes/ha based on sodicity level; "
            "apply Elemental S 500 kg/ha for pH 8.5+; "
            "pyrite (FeS2) 500 kg/ha is cheapest option. "
            "(4) WEBSITE soilhealth.dac.gov.in to download your Soil Health Card online."
        ),
    },

    # ── IRRIGATION AND WATER MANAGEMENT ──────────────────────────────────────
    {
        "file": "soil/drip_sprinkler_installation.txt",
        "title": "Drip and Sprinkler Irrigation — Installation and Subsidy",
        "prompt": (
            "Write a comprehensive guide on drip and sprinkler irrigation for Indian farmers. "
            "(1) DRIP IRRIGATION: "
            "components: main pipe, sub-main, lateral pipes, drippers (emitters), filters, fertigation unit; "
            "dripper discharge rates: 1.0, 1.6, 2.0, 3.5 L/hr; "
            "spacing for vegetables 30-60cm; for fruits 0.5-1m along rows; "
            "water saving 40-60% vs flood; "
            "fertilizer saving 30% via fertigation; "
            "cost Rs 40,000-80,000/ha depending on crop; "
            "PMKSY subsidy: SC/ST/small farmers 90%; general farmers 75%; "
            "maintenance: flush laterals monthly; clean filters weekly; "
            "suitable crops: drip best for vegetables, fruits, sugarcane, cotton. "
            "(2) SPRINKLER IRRIGATION: "
            "types: portable, semi-permanent, permanent; "
            "sprinkler head spacing 9x9m or 12x12m; "
            "discharge 3-5mm/hr application rate; "
            "water saving 30-35% vs flood; "
            "suitable crops: wheat, pulses, oilseeds, vegetables, nurseries; "
            "not suitable: paddy (needs standing water), heavy clay soils; "
            "cost Rs 12,000-25,000/ha; subsidy 55-80%. "
            "(3) HOW TO APPLY FOR SUBSIDY under PMKSY: "
            "register on PMKSY portal or state horticulture department; "
            "purchase from empanelled vendors only (list on PMKSY website); "
            "documents: land records, Aadhaar, bank account, caste certificate; "
            "subsidy directly credited to bank account after installation verification. "
            "(4) FERTIGATION schedule for drip-irrigated crops: "
            "inject soluble fertilizers at 20-30 minute into each irrigation cycle; "
            "NPK 19:19:19 at vegetative stage, 12:61:0 at flowering, 0:0:60 at fruit fill."
        ),
    },

    # ── PEST AND DISEASE DEEP DIVES ───────────────────────────────────────────
    {
        "file": "pests/rice_diseases_blast_blt_sheath.txt",
        "title": "Rice Diseases — Blast, BLB, Sheath Blight, False Smut",
        "prompt": (
            "Write a detailed disease management guide for major rice diseases in India. "
            "(1) RICE BLAST (Pyricularia oryzae) — most serious rice disease: "
            "Leaf blast: oval/diamond-shaped spots with grey center and brown border; "
            "Neck blast at panicle base: most damaging — crop looks burnt; "
            "Favored by: temperature 22-28C + humidity >90% for 3+ days; "
            "ETL: 2-3 lesions per leaf (leaf blast) OR any neck blast symptom. "
            "Control: "
            "Seed treatment: Tricyclazole 75WP 2g/kg or Carbendazim 2g/kg; "
            "Foliar spray: Tricyclazole 75WP 500g/ha at booting + 7-10 days later; "
            "OR Isoprothiolane 40EC 750mL/ha; "
            "Preventive: spray at panicle initiation stage always in blast-prone areas. "
            "(2) BACTERIAL LEAF BLIGHT (BLB — Xanthomonas oryzae): "
            "Symptoms: water-soaked margins turning yellow-white from tip; "
            "Kresek (seedling wilt) at early stage; "
            "Favored by: heavy N fertilization, flooding, wounds; "
            "No curative spray. Management: "
            "Remove excess N; drain field; "
            "spray Copper oxychloride 50WP 3g/L + Streptomycin 100ppm; "
            "use resistant varieties: IR-64, Swarna Sub1. "
            "(3) SHEATH BLIGHT (Rhizoctonia solani): "
            "Water-soaked oval lesions on leaf sheath near waterline; "
            "Favored by: dense planting, high N, high humidity; "
            "ETL: 25-30% tillers infected. "
            "Control: Hexaconazole 5SC 1mL/L or Propiconazole 25EC 1mL/L at disease onset. "
            "(4) FALSE SMUT (Ustilaginoidea virens): "
            "Black/orange balls replace grains; toxin risk in affected grain; "
            "Control: Propiconazole 25EC spray at panicle emergence. "
            "(5) BROWN SPOT (Helminthosporium oryzae): "
            "Brown oval spots; associated with nutrient deficiency; "
            "Control: improve soil nutrition + Mancozeb 75WP 2.5g/L."
        ),
    },
    {
        "file": "pests/wheat_diseases_rust_smut.txt",
        "title": "Wheat Diseases — Yellow Rust, Brown Rust, Karnal Bunt, Loose Smut",
        "prompt": (
            "Write a detailed wheat disease management guide for India. "
            "(1) YELLOW/STRIPE RUST (Puccinia striiformis): "
            "Stripe of yellow-orange pustules along leaf veins — most feared disease; "
            "Spreads in cool 10-15C + high humidity weather; "
            "Can destroy entire crop in 2-3 weeks if unchecked; "
            "ETL: First pustule appearance = spray immediately. "
            "Control: Propiconazole 25EC 500mL/ha at first appearance, repeat 15 days; "
            "OR Tebuconazole 250EW 750mL/ha; "
            "Preventive: use resistant varieties HD-3086, DBW-187, PBW-343. "
            "(2) BROWN/LEAF RUST (Puccinia recondita): "
            "Circular orange-red pustules scattered on leaves; "
            "develops in warmer weather 15-22C; "
            "ETL: 5-10% leaf area infected. "
            "Control: Mancozeb 75WP 2.5g/L + Propiconazole 1mL/L combo. "
            "(3) KARNAL BUNT (Tilletia indica): "
            "Partial replacement of grain by black smutty mass; "
            "quarantine pest — affects export quality; "
            "Prevention: Seed treatment Carboxin 75WP 2.5g/kg + Thiram 75WP 1.5g/kg. "
            "(4) LOOSE SMUT (Ustilago tritici): "
            "Entire spike replaced by black spore mass; "
            "Seed-borne — use certified seed + Carboxin treatment; "
            "Hot water treatment 50C for 2 hours as alternative. "
            "(5) POWDERY MILDEW (Blumeria graminis): "
            "White powdery coating on upper leaf surfaces; "
            "Control: Sulphur 80WP 3g/L or Hexaconazole 5SC 1mL/L. "
            "(6) SPRAY CALENDAR for wheat: "
            "Seed treatment before sowing; "
            "First foliar at tillering (40 DAS) if rust seen; "
            "Mandatory spray at booting (65-70 DAS) in rust-prone areas."
        ),
    },
    {
        "file": "pests/nematode_management.txt",
        "title": "Nematode Management in Indian Crops",
        "prompt": (
            "Write a comprehensive nematode management guide for Indian farmers. "
            "(1) ROOT-KNOT NEMATODE (Meloidogyne spp.) — most common: "
            "Affects: vegetables (tomato, brinjal, okra, potato), groundnut, banana, wheat; "
            "Symptoms: galls/knots on roots, stunted plants, yellowing, wilting even when irrigated; "
            "Diagnosis: pull out roots, look for knot-like swellings; "
            "ETL: 10 nematodes per 250g soil (initial inoculum). "
            "Management: "
            "Soil solarization: wet soil, cover with clear polythene 6 weeks in summer — kills 90%; "
            "Bio-control: Paecilomyces lilacinus 1kg/ha soil application + seed treatment; "
            "Trichoderma viride 2.5kg/ha; "
            "Neem cake incorporation 2 t/ha; "
            "Chemical: Carbofuran 3G 20-25 kg/ha incorporated in soil before planting; "
            "Fluopyram (Velum Prime) soil drench 0.4mL/L for high-value crops. "
            "(2) CYST NEMATODE (Heterodera spp.): "
            "Affects wheat (Heterodera avenae), potato, soybean; "
            "Management similar to root-knot; resistant varieties in wheat. "
            "(3) BURROWING NEMATODE (Radopholus similis): "
            "Affects banana, black pepper; causes toppling disease; "
            "Hot water treatment of planting material 55C 20 min. "
            "(4) INTEGRATED APPROACH: "
            "Crop rotation with non-host crops (maize, sorghum, wheat alternate with vegetable); "
            "Marigold (Tagetes erecta) as trap crop or intercrop — secretes nematicidal root exudates; "
            "Summer deep ploughing exposes soil to UV — kills nematode eggs. "
            "(5) Recognizing nematode vs nutrient deficiency — key differences in symptoms."
        ),
    },

    # ── GOVERNMENT SCHEMES IN DEPTH ───────────────────────────────────────────
    {
        "file": "schemes/crop_insurance_pmfby_detail.txt",
        "title": "PMFBY Crop Insurance — Detailed Claim Process",
        "prompt": (
            "Write a comprehensive guide on PMFBY (Pradhan Mantri Fasal Bima Yojana) crop insurance. "
            "(1) COVERAGE: what is covered — prevented sowing, standing crop loss, post-harvest loss, "
            "localized calamities (hailstorm, landslide, inundation), flood, drought, cyclone; "
            "not covered: war, nuclear risk, deliberate damage. "
            "(2) PREMIUM RATES: "
            "Kharif crops: 2% of sum insured by farmer; "
            "Rabi crops: 1.5% of sum insured; "
            "Annual commercial/horticulture crops: 5%; "
            "rest of actuarial premium paid by government. "
            "(3) HOW TO ENROLL: "
            "Loanee farmers: auto-enrolled through KCC/crop loan — opt-out if not needed; "
            "Non-loanee farmers: enroll within cut-off date (last date is 15 days before sowing); "
            "Apply at: Bank, CSC, PMFBY portal pmfby.gov.in, Crop Insurance App; "
            "Documents: land records, Aadhaar, bank account, sowing declaration. "
            "(4) HOW TO FILE A CLAIM — step by step: "
            "Within 72 hours of crop damage: call 14447 helpline OR "
            "use Crop Insurance App (photo upload) OR inform bank/insurance company in writing; "
            "For post-harvest loss (14 days after harvest): same procedure; "
            "Crop cutting experiments (CCE) determine yield; "
            "If notified area yield < threshold yield: automatic payment — no individual assessment needed. "
            "(5) CLAIM TIMELINE: payment within 2 months of harvest; "
            "directly to bank account via PFMS. "
            "(6) GRIEVANCE: helpline 14447; email help.agri-insurance@gov.in; "
            "State agriculture department mediates disputes. "
            "(7) RWBCIS (Restructured Weather Based Crop Insurance Scheme): "
            "weather parameters (temperature, rainfall) trigger automatic payment; "
            "no CCE needed; faster payment."
        ),
    },
    {
        "file": "schemes/kcc_loan_nabard_schemes.txt",
        "title": "KCC, Agricultural Loans, NABARD, Mudra",
        "prompt": (
            "Write a comprehensive guide on agricultural credit and loan schemes for Indian farmers. "
            "(1) KISAN CREDIT CARD (KCC): "
            "credit limit based on landholding + scale of finance; "
            "Interest rate: 7% per annum; with timely repayment 3% subvention = effective 4%; "
            "applies to first Rs 3 lakh; above 3 lakh = market rate; "
            "validity 5 years; revolving credit — withdraw and repay anytime; "
            "covers: crop cultivation, post-harvest, maintenance, allied activities (fishery, animal husbandry); "
            "apply at: any bank, cooperative, RRB; "
            "documents: land records, Aadhaar, passport photo; "
            "processing: 2-4 weeks. "
            "(2) AGRICULTURAL GOLD LOAN: "
            "fastest disbursal (same day); "
            "loan up to 75% of gold value; "
            "interest 7-12%; no land records needed; "
            "useful for emergency crop input purchases. "
            "(3) NABARD SCHEMES: "
            "Kisan Credit Card refinance to banks; "
            "Watershed Development Fund; "
            "RIDF (Rural Infrastructure Development Fund) for irrigation; "
            "WADI tribal development program; "
            "FPO (Farmer Producer Organisation) formation support: Rs 15 lakh grant per FPO; "
            "contact nearest NABARD district office. "
            "(4) MUDRA LOAN for agri-allied activities: "
            "Shishu: up to Rs 50,000; Kishore: Rs 50,000-5 lakh; Tarun: Rs 5-10 lakh; "
            "for: agri-processing, dairy, poultry, sericulture; "
            "no collateral for Shishu and Kishore. "
            "(5) PM-SVANidhi (for street vendors who sell farm produce): "
            "working capital loan Rs 10,000 initially; "
            "no collateral; apply via PM-SVANidhi app."
        ),
    },

    # ── MARKET AND SELLING ────────────────────────────────────────────────────
    {
        "file": "schemes/fpo_mandi_export_guide.txt",
        "title": "FPO, eNAM, Export, Value Addition",
        "prompt": (
            "Write a comprehensive market access guide for Indian farmers. "
            "(1) FARMER PRODUCER ORGANISATION (FPO): "
            "minimum 10 farmers to form; register as producer company under Companies Act; "
            "benefits: bulk buying inputs 15-25% cheaper; collective selling better price; "
            "access to credit, processing, export; "
            "government support: Rs 15 lakh/FPO (10,000 new FPOs scheme); "
            "register through NABARD, SFAC, NCDC or state agencies; "
            "contact SFAC: sfac.in or 011-26862367. "
            "(2) eNAM (Electronic National Agriculture Market): "
            "register at local APMC; get farmer ID; "
            "assay (quality testing) of produce; upload to platform; "
            "buyers from across India bid online; "
            "helpline: 1800-270-0224; website enam.gov.in; "
            "covered commodities: 175+ including grains, vegetables, fruits, spices. "
            "(3) EXPORT OPPORTUNITIES: "
            "Basmati rice: APEDA registration required; "
            "Fresh vegetables/fruits: GlobalGAP certification for EU; "
            "Organic produce: APEDA NOP/EU organic certification; "
            "Spices: Spices Board India spicesboard.in; "
            "contact APEDA: apeda.gov.in for export registration. "
            "(4) VALUE ADDITION to increase income: "
            "tomato → tomato puree/paste (3-5x value); "
            "onion → dehydrated onion (8-10x value); "
            "turmeric → turmeric powder (2-3x); "
            "dal milling: buy pulse at MSP, mill to dal, 40-60% margin; "
            "cold storage: store onion/potato during peak and sell at off-season premium; "
            "PMKVY scheme provides processing equipment subsidy. "
            "(5) DIRECT MARKETING (Farm-to-Consumer): "
            "Rythu Bazaars (Telangana/AP); "
            "Hadaspar vegetable market; "
            "WhatsApp group selling to urban consumers; "
            "BigBasket, Ninjacart, DeHaat platforms for direct farmer purchase."
        ),
    },
    {
        "file": "schemes/post_harvest_storage_cold_chain.txt",
        "title": "Post-Harvest Management, Storage, Cold Chain",
        "prompt": (
            "Write a comprehensive post-harvest management guide for Indian farmers. "
            "(1) GRAIN STORAGE: "
            "moisture content before storage: wheat <12%; rice <14%; maize <12%; pulses <10%; "
            "HDPE woven bags 50kg — basic storage; "
            "hermetic bags (Purdue Improved Crop Storage PICS): airtight, no pesticide needed, last 6-12 months; "
            "pucca godown: maintain humidity <65%, temperature <25C; "
            "fumigation: Aluminium phosphide (Celphos) 3 tablets/tonne under tarpaulin for 5 days; "
            "safety: 3-day ventilation before entering fumigated godown — phosphine gas is lethal; "
            "Warehousing Corporation of India (WDRA) facilities in all districts. "
            "(2) VEGETABLE AND FRUIT COLD CHAIN: "
            "pre-cooling immediately after harvest reduces field heat; "
            "temperature requirements: potato 4C, onion 1-2C, tomato 10-12C, mango 12-13C; "
            "cold storage near farm: MIDH subsidy 40% for pack houses; "
            "Ripening chamber: ethylene 100ppm for 24h for banana/mango. "
            "(3) SIMPLE LOW-COST TECHNOLOGIES: "
            "Bamboo bins lined with polythene — grain storage 6 months; "
            "Evaporative cooler (cool chamber): brick/sand+water box reduces temp 10-15C; "
            "Wax coating for citrus/mango — extends shelf life 2-3 weeks; "
            "Zero Energy Cool Chamber: brick+sand construction, 24-28C maintains fruits 2-3 weeks. "
            "(4) MANGO RIPENING: "
            "Natural: spread in single layer, cover with straw 3-5 days; "
            "Commercial: Ethephon (Ethrel) 500ppm dip for uniform ripening; "
            "Calcium carbide — BANNED in India (toxic); report violations. "
            "(5) PREVENTING LOSSES: "
            "India loses 30-40% of horticulture produce post-harvest; "
            "harvest at correct maturity index; handle gently; "
            "grading and sorting before storage; "
            "use ventilated crates not closed boxes."
        ),
    },

    # ── INTEGRATED FARMING SYSTEMS ────────────────────────────────────────────
    {
        "file": "crops/polyhouse_greenhouse_farming.txt",
        "title": "Polyhouse, Greenhouse, Protected Cultivation",
        "prompt": (
            "Write a comprehensive guide on protected cultivation (polyhouse/greenhouse) for Indian farmers. "
            "(1) TYPES AND COST: "
            "Low-cost polyhouse (bamboo/GI pipe): Rs 300-500/sq.m; "
            "Medium tech (GI frame + UV film): Rs 600-800/sq.m; "
            "High tech (automated climate control): Rs 1000-1500/sq.m; "
            "shade net house: Rs 80-150/sq.m. "
            "(2) NHBM SUBSIDY: "
            "National Horticulture Board Mission: 50-65% subsidy on polyhouse; "
            "maximum Rs 56 lakh/ha for high-tech; "
            "apply through MIDH portal or state horticulture department; "
            "NHM subsidy: nhb.gov.in. "
            "(3) CROPS SUITABLE for polyhouse: "
            "Vegetables: capsicum, cucumber, tomato, lettuce, baby corn; "
            "Flowers: gerbera, carnation, rose (most profitable); "
            "Off-season vegetables: 3-4x normal market price. "
            "(4) MANAGEMENT INSIDE POLYHOUSE: "
            "Temperature control: ventilation fans, foggers; optimal 22-28C day, 15-18C night; "
            "Humidity: 60-80%; "
            "Drip irrigation mandatory; "
            "Fertigation schedule weekly. "
            "(5) HYDROPONICS basics: "
            "Nutrient Film Technique (NFT) for leafy vegetables; "
            "setup cost Rs 800-1200/sq.m; "
            "no soil needed — grows in water nutrient solution; "
            "yield 3-5x vs soil in same area. "
            "(6) PROFITABILITY: "
            "Gerbera: 1 lakh flowers/1000 sq.m/year @ Rs 4-8/flower = Rs 4-8 lakh revenue; "
            "Capsicum: 50 kg/sq.m/year @ Rs 30-80/kg premium polyhouse produce. "
            "(7) COMMON MISTAKES: overwatering, poor ventilation, wrong variety for local climate."
        ),
    },
    {
        "file": "crops/animal_husbandry_integration.txt",
        "title": "Animal Husbandry — Dairy, Poultry, Goat Farming",
        "prompt": (
            "Write a practical guide on integrated animal husbandry with farming for income diversification. "
            "(A) DAIRY FARMING: "
            "Breeds: HF (Holstein Friesian) 20-25 L/day; Jersey 12-15 L; "
            "crossbreeds HF×Sahiwal, Jersey×Gir best for India; "
            "Sahiwal, Gir, Red Sindhi (desi) — better disease resistance, lower input; "
            "Feed: dry fodder 10% body weight + concentrate 400g per L milk; "
            "Vaccination: FMD (Foot and Mouth Disease) every 6 months; HS (Hemorrhagic Septicemia) annual; "
            "Milk production economics: Rs 28-35/L selling price; input cost Rs 20-25/L. "
            "(B) POULTRY: "
            "Broiler: 6-7 weeks to market weight 2kg; "
            "Layer: egg production 280-300 eggs/year/bird; "
            "backyard poultry: 4-6 eggs/week desi breed; "
            "diseases: Ranikhet (Newcastle) — vaccinate at 7 days, 28 days, every 3 months; "
            "Gumboro (IBD) — vaccinate at 14 days, 28 days. "
            "(C) GOAT FARMING: "
            "low investment, fast return; "
            "Breeds: Sirohi, Barbari, Black Bengal, Osmanabadi; "
            "2 kids per year; slaughter weight 20-25kg in 12 months; "
            "market price Rs 400-600/kg live weight; "
            "diseases: PPR — vaccinate annually; FMD — every 6 months. "
            "(D) GOVERNMENT SUPPORT: "
            "KCC covers allied activities (dairy, poultry, fishery); "
            "NABARD dairy loans; "
            "Animal Husbandry Infrastructure Development Fund (AHIDF) Rs 15,000 crore; "
            "Rashtriya Gokul Mission for desi breed conservation; "
            "helpline 1800-180-1551 for animal husbandry queries."
        ),
    },
    {
        "file": "crops/climate_smart_agriculture.txt",
        "title": "Climate Change Adaptation, Drought, Flood Management",
        "prompt": (
            "Write a comprehensive guide on climate-smart agriculture for Indian farmers. "
            "(1) DROUGHT MANAGEMENT: "
            "Early warning: IMD meghdoot app, check 5-day forecast before each operation; "
            "Drought tolerant varieties: Wheat GW-496; Rice Sahbhagi Dhan; Maize African Tall; "
            "Moisture conservation: mulching with crop residue reduces evaporation 30%; "
            "In-situ moisture conservation: contour bunding, tied ridges; "
            "Contingency crops if monsoon fails by July 15: Bajra, moong, sunhemp; "
            "National Drought Monitoring Centre (NDMC): nmsc.gov.in. "
            "(2) FLOOD AND WATERLOGGING: "
            "Flood tolerant varieties: Swarna Sub1 (7 days submergence), FR-13A gene; "
            "Post-flood recovery: remove standing water immediately, spray urea 2% foliar, "
            "spray fungicide Carbendazim to prevent fungal outbreak; "
            "rehabilitate soil with gypsum + organic matter. "
            "(3) HEAT STRESS: "
            "Wheat terminal heat: sow early November; choose heat tolerant K-9107, NW-1014; "
            "Foliar spray Salicylic acid 1mM or Thiourea 1000ppm at grain fill reduces heat damage; "
            "Night irrigation when temperature >38C. "
            "(4) UNSEASONAL RAIN at harvest: "
            "harvest early at 85% maturity; use desiccant (Diquat 20SL 0.5L/ha) for quick drying wheat; "
            "temporary storage under tarpaulin; "
            "PMFBY covers post-harvest loss for 14 days. "
            "(5) CARBON CREDIT OPPORTUNITIES: "
            "zero tillage, agroforestry, SRI paddy generate carbon credits; "
            "Verra and Gold Standard registries; "
            "FPO aggregation helps small farmers participate."
        ),
    },
    {
        "file": "pests/stored_grain_pest_management.txt",
        "title": "Stored Grain Pests — Weevil, Moth, Rat Management",
        "prompt": (
            "Write a comprehensive guide on stored grain pest management for Indian farmers. "
            "(1) MAJOR STORAGE PESTS and identification: "
            "Rice/Grain Weevil (Sitophilus oryzae): small brown beetle 3mm, round holes in grain; "
            "Khapra Beetle (Trogoderma granarium): hairy larvae, most dangerous quarantine pest; "
            "Pulse Beetle (Callosobruchus maculatus): round exit holes in dal/pulse grains; "
            "Flour Moth (Ephestia kuehniella): webbing in grain mass; "
            "Lesser Grain Borer (Rhyzopertha dominica): fine dust, hollow grains. "
            "(2) PREVENTION: "
            "Clean and fumigate godown before filling; "
            "Moisture of grain must be below safe limit before storage; "
            "No cracks in walls/floor — seal with cement; "
            "Keep surrounding area clean, avoid adjacent food waste. "
            "(3) TREATMENT METHODS: "
            "Admixture with inert dusts: Diatomaceous earth (DE) 1kg/tonne — physical mode, safe for food; "
            "Grain protectant spray: Malathion 50EC 1L in 100L water per tonne of bags (outside of bags only); "
            "Fumigation: Aluminium phosphide (ALP) tablets 3g/tonne — 5-day exposure; "
            "CRITICAL: never fumigate in sealed living area; open 3 days before entering; "
            "use only licensed fumigators for large quantities. "
            "(4) RAT MANAGEMENT: "
            "Permanent concrete storage prevents rats better than any poison; "
            "Mechanical traps (snap traps, live traps); "
            "Rodenticide: Bromadiolone 0.005% bait blocks at 50-100g per burrow; "
            "Zinc phosphide 2% mixed in bait — single-dose, acute; place away from children/pets. "
            "(5) HERMETIC STORAGE bags: "
            "GrainPro, PICS bags — triple-layer airtight; "
            "no pesticide needed; safe for seed storage; "
            "government distribution through food department."
        ),
    },
    {
        "file": "crops/seed_production_certification.txt",
        "title": "Seed Production, Certification, Seed Village Program",
        "prompt": (
            "Write a comprehensive guide on seed production and quality for Indian farmers. "
            "(1) SEED CLASSES: "
            "Breeder Seed (BS): produced by ICAR/SAU scientists, nucleus material; "
            "Foundation Seed (FS): multiplied from BS, tagged yellow; "
            "Certified Seed (CS): multiplied from FS, tagged blue; "
            "Truthfully Labelled (TL): private companies, no certification; "
            "Buy only BS/FS/CS for best results. "
            "(2) HOW TO CHECK SEED QUALITY: "
            "Germination test at home: 100 seeds on wet cloth, 7 days count sprouted; "
            "minimum germination: wheat 85%, rice 80%, maize 90%, pulses 75%; "
            "Purity test: check for other crop seeds and weed seeds; "
            "buy from registered seed dealer, ask for receipt. "
            "(3) HOME SEED PRODUCTION for self-use: "
            "use certified seed as base; "
            "maintain isolation distance: cross-pollinated (maize, sorghum) 400m; self-pollinated (wheat, rice) 3-10m; "
            "select disease-free, true-to-type plants; "
            "harvest separately, dry to <12% moisture; "
            "treat before storage. "
            "(4) SEED VILLAGE PROGRAM: "
            "ICAR/NSC program: farmers trained to produce certified seed; "
            "7-10% premium over grain price; "
            "seed is sold to NSC/state seed corporations; "
            "contact: NSC (National Seeds Corporation) nationalseeds.com or district agriculture office. "
            "(5) SEED TREATMENT before sowing: "
            "Chemical: Thiram 3g/kg + Carbendazim 2g/kg (broad spectrum); "
            "Biological: Trichoderma viride 4g/kg + Pseudomonas fluorescens 10g/kg; "
            "Never mix chemical fungicide with Rhizobium (kills the bacteria)."
        ),
    },
    {
        "file": "schemes/digital_tools_apps_farmers.txt",
        "title": "Digital Tools, Apps, and Services for Farmers",
        "prompt": (
            "Write a guide on useful digital tools, apps, and services available to Indian farmers in 2024. "
            "(1) WEATHER AND ADVISORY APPS: "
            "Meghdoot App (IMD): free 5-day weather forecast in regional languages, crop advisory; "
            "Damini App (IMD): lightning alerts — life safety; "
            "Kisan Suvidha App: weather, market price, dealer locator, crop doctor; "
            "AgriMarket App: mandi prices within 50km radius. "
            "(2) GOVERNMENT SCHEME APPS: "
            "PM-Kisan App: check installment status, register, update Aadhaar; "
            "PMFBY App: crop insurance enrollment, claim, status; "
            "Soil Health Card App: download soil health card, fertilizer recommendations; "
            "eNAM App: buy/sell in online mandi. "
            "(3) MARKET PRICE APPS: "
            "AgriMarket: commodity-wise mandi prices; "
            "Agmarknet website: agmarknet.gov.in for historical prices; "
            "eNAM app: live auction prices; "
            "Ninjacart (B2B): bulk selling directly to retailers; "
            "DeHaat: input supply + market linkage. "
            "(4) CROP DIAGNOSIS APPS: "
            "Plantix (PEAT): photo-based disease detection, 500+ crops; "
            "KrishiRaksha (this app!): AI disease detection + advisory; "
            "Farmer.chat: multilingual AI chatbot. "
            "(5) FINANCIAL SERVICES: "
            "DigiLocker: store land records, Aadhaar, certificates digitally; "
            "BHIM UPI: instant payment at mandi; "
            "Jan Dhan account: required for scheme benefits direct transfer. "
            "(6) LEARNING PLATFORMS: "
            "Kisan Call Centre: 1800-180-1551 (free, 24x7, 22 languages); "
            "DD Kisan Channel (TV): crop advisory; "
            "YouTube: ICAR, KVK channels for crop management videos. "
            "(7) CONNECTIVITY: "
            "PM-WANI: free public Wi-Fi at CSC and gram panchayat; "
            "BSNL rural 4G expansion 2024."
        ),
    },
]


# ── Helper functions ─────────────────────────────────────────────────────────

def ask_qwen(prompt: str, max_tokens: int = 2500) -> str:
    """Send prompt to Qwen via Ollama API, return text response."""
    full_prompt = f"{SYSTEM}\n\n{prompt}"
    payload = json.dumps({
        "model": MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.15,   # low = factual, consistent
            "num_predict": max_tokens,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result.get("response", "").strip()


def save_file(relative_path: str, content: str) -> None:
    """Save content to knowledge_base/<relative_path>."""
    full_path = KB_DIR / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    kb = round(len(content.encode("utf-8")) / 1024, 1)
    print(f"  ✓  Saved {relative_path}  ({kb} KB)")


def check_ollama() -> bool:
    """Verify Ollama is running and model is available."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            return any("qwen2.5" in m for m in models)
    except Exception:
        return False


# ── Main generator ────────────────────────────────────────────────────────────

def main():
    print("\n" + "═" * 60)
    print("  KrishiMitra Knowledge Base Generator")
    print("  Using: Qwen 2.5 7B via Ollama (100% local, zero API cost)")
    print("═" * 60 + "\n")

    if not check_ollama():
        print("❌  Ollama not running or qwen2.5:7b not found.")
        print("   Run:  ollama serve  (in a separate terminal)")
        print("   Then: ollama pull qwen2.5:7b")
        sys.exit(1)

    print(f"✅  Ollama OK — {MODEL} ready")
    print(f"📂  Output: {KB_DIR}\n")

    total      = len(TOPICS)
    completed  = 0
    failed     = []
    start_all  = time.time()

    for i, topic in enumerate(TOPICS, 1):
        file_path = topic["file"]
        title     = topic["title"]
        prompt    = topic["prompt"]

        # Skip if file already exists and is non-empty
        existing = KB_DIR / file_path
        if existing.exists() and existing.stat().st_size > 500:
            print(f"[{i}/{total}] ⏭  {title}  (already exists, skipping)")
            completed += 1
            continue

        print(f"[{i}/{total}] ⚙  Generating: {title}")
        t0 = time.time()

        try:
            content = ask_qwen(prompt)
            if len(content) < 200:
                raise ValueError(f"Response too short ({len(content)} chars) — likely truncated")

            # Add a header with source attribution
            header = (
                f"# {title}\n"
                f"# Generated by KrishiMitra AI Knowledge Base Builder\n"
                f"# Source: ICAR guidelines + agricultural research literature\n"
                f"# Last updated: 2024-25 season\n\n"
            )
            save_file(file_path, header + content)
            elapsed = round(time.time() - t0, 1)
            print(f"     ✅  Done in {elapsed}s")
            completed += 1

        except KeyboardInterrupt:
            print("\n⚠  Interrupted by user. Partial knowledge base saved.")
            break
        except Exception as exc:
            print(f"     ❌  Failed: {exc}")
            failed.append(title)

        # Small pause between calls to avoid overwhelming Ollama
        time.sleep(1)

    # ── Summary ───────────────────────────────────────────────────────────────
    total_time = round(time.time() - start_all, 0)
    print("\n" + "═" * 60)
    print(f"  Knowledge Base Generation Complete")
    print(f"  ✅  {completed}/{total} files generated")
    print(f"  ⏱   Total time: {int(total_time//60)}m {int(total_time%60)}s")
    if failed:
        print(f"  ❌  Failed: {', '.join(failed)}")
    print("═" * 60)

    # Count total KB size
    total_bytes = sum(f.stat().st_size for f in KB_DIR.rglob("*.txt"))
    print(f"\n  📚  Total knowledge base size: {round(total_bytes/1024, 0):.0f} KB")
    print(f"  📂  Location: {KB_DIR}")
    print(f"\n  Next step: python3 ingest.py  (builds the vector store)")
    print()


if __name__ == "__main__":
    main()
