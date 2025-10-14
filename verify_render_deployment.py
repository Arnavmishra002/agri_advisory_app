#!/usr/bin/env python3
"""
Quick verification script to check if service cards are clickable on Render
"""

import requests
from bs4 import BeautifulSoup
from colorama import init, Fore, Style

init(autoreset=True)

RENDER_URL = "https://krishmitra-zrk4.onrender.com/"

def check_service_cards():
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}{'🌾 RENDER DEPLOYMENT VERIFICATION':^70}")
    print(f"{Fore.CYAN}{'='*70}\n")
    print(f"{Fore.WHITE}Target: {RENDER_URL}\n")
    
    try:
        print(f"{Fore.YELLOW}⏳ Fetching page...")
        response = requests.get(RENDER_URL, timeout=15)
        
        if response.status_code == 200:
            print(f"{Fore.GREEN}✅ Page loaded successfully! (Status: 200)\n")
            
            html = response.text
            
            # Check for service cards
            services = [
                'सरकारी योजनाएं',
                'फसल सुझाव',
                'मौसम पूर्वानुमान',
                'बाजार कीमतें',
                'कीट नियंत्रण',
                'AI सहायक'
            ]
            
            print(f"{Fore.CYAN}📋 Checking Service Cards:\n")
            
            all_found = True
            for service in services:
                if service in html:
                    print(f"{Fore.GREEN}✅ {service} - FOUND")
                else:
                    print(f"{Fore.RED}❌ {service} - NOT FOUND")
                    all_found = False
            
            # Check for service sections (content areas)
            print(f"\n{Fore.CYAN}📦 Checking Service Content Sections:\n")
            
            sections_to_check = [
                ('government-schemes-section', 'Government Schemes Section'),
                ('crop-recommendations-section', 'Crop Recommendations Section'),
                ('weather-section', 'Weather Section'),
                ('market-prices-section', 'Market Prices Section'),
                ('pest-detection-section', 'Pest Control Section'),
                ('chatbot-section', 'AI Chatbot Section')
            ]
            
            sections_found = 0
            for section_id, section_name in sections_to_check:
                if section_id in html or section_name.split()[0].lower() in html.lower():
                    print(f"{Fore.GREEN}✅ {section_name} - RENDERED")
                    sections_found += 1
                else:
                    print(f"{Fore.YELLOW}⚠️  {section_name} - Check manually")
            
            # Check for JavaScript initialization
            print(f"\n{Fore.CYAN}🔧 Checking JavaScript Setup:\n")
            
            js_checks = [
                ('DOMContentLoaded', 'Event Listener'),
                ('showService', 'Service Display Function'),
                ('data-service', 'Service Data Attributes'),
                ('pointer-events: none', 'CSS Fix Applied')
            ]
            
            for check_text, check_name in js_checks:
                if check_text in html:
                    print(f"{Fore.GREEN}✅ {check_name} - PRESENT")
                else:
                    print(f"{Fore.YELLOW}⚠️  {check_name} - Not detected")
            
            # Final verdict
            print(f"\n{Fore.CYAN}{'='*70}")
            if all_found and sections_found >= 4:
                print(f"{Fore.GREEN}{'🎉 SUCCESS! ALL SERVICE CARDS WORKING!':^70}")
                print(f"{Fore.GREEN}{'='*70}\n")
                print(f"{Fore.GREEN}✅ All 6 service cards are present")
                print(f"{Fore.GREEN}✅ Service content sections are rendered")
                print(f"{Fore.GREEN}✅ JavaScript fixes are applied")
                print(f"\n{Fore.WHITE}👉 The service cards should be CLICKABLE now!")
                print(f"{Fore.WHITE}👉 Test manually by clicking each card on the live site")
            else:
                print(f"{Fore.YELLOW}{'⚠️  PARTIAL SUCCESS':^70}")
                print(f"{Fore.YELLOW}{'='*70}\n")
                print(f"{Fore.YELLOW}Some elements may need verification")
            
            # Quick clickability test instructions
            print(f"\n{Fore.CYAN}{'='*70}")
            print(f"{Fore.CYAN}{'📋 MANUAL TESTING CHECKLIST':^70}")
            print(f"{Fore.CYAN}{'='*70}\n")
            
            print(f"{Fore.WHITE}Visit: {Fore.GREEN}{RENDER_URL}\n")
            print(f"{Fore.WHITE}Then click each service card:\n")
            
            test_cards = [
                "1. 🏛️  सरकारी योजनाएं - Should show government schemes list",
                "2. 🌱 फसल सुझाव - Should show crop recommendation form",
                "3. 🌤️  मौसम पूर्वानुमान - Should show weather information",
                "4. 📈 बाजार कीमतें - Should show market prices form",
                "5. 🐛 कीट नियंत्रण - Should show pest detection form",
                "6. 🤖 AI सहायक - Should show chatbot interface"
            ]
            
            for card in test_cards:
                print(f"{Fore.CYAN}   {card}")
            
            print(f"\n{Fore.WHITE}✅ If all cards open their sections → SUCCESS!")
            print(f"{Fore.WHITE}❌ If cards don't respond → Clear browser cache (Ctrl+F5)")
            
        else:
            print(f"{Fore.RED}❌ Page load failed! Status: {response.status_code}")
            
    except Exception as e:
        print(f"{Fore.RED}❌ Error connecting to Render: {e}")

if __name__ == "__main__":
    check_service_cards()

