            # 2. Fallback: Generate comprehensive simulated data
            import random
            
            # Define crop database with realistic prices
            crop_database = [
                {'name': 'Wheat', 'name_hindi': 'गेहूं', 'base_price': 2500, 'msp': 2125, 'trend': 'बढ़ रहा'},
                {'name': 'Rice', 'name_hindi': 'चावल', 'base_price': 3000, 'msp': 2040, 'trend': 'स्थिर'},
                {'name': 'Bajra', 'name_hindi': 'बाजरा', 'base_price': 2250, 'msp': 2350, 'trend': 'गिर रहा'},
                {'name': 'Maize', 'name_hindi': 'मक्का', 'base_price': 1900, 'msp': 1962, 'trend': 'बढ़ रहा'},
                {'name': 'Jowar', 'name_hindi': 'ज्वार', 'base_price': 2970, 'msp': 3180, 'trend': 'स्थिर'},
                {'name': 'Barley', 'name_hindi': 'जौ', 'base_price': 1635, 'msp': 1735, 'trend': 'बढ़ रहा'},
                {'name': 'Gram', 'name_hindi': 'चना', 'base_price': 5230, 'msp': 5335, 'trend': 'स्थिर'},
                {'name': 'Arhar', 'name_hindi': 'अरहर', 'base_price': 6600, 'msp': 6950, 'trend': 'बढ़ रहा'},
                {'name': 'Moong', 'name_hindi': 'मूंग', 'base_price': 7275, 'msp': 7755, 'trend': 'गिर रहा'},
                {'name': 'Urad', 'name_hindi': 'उड़द', 'base_price': 6300, 'msp': 6600, 'trend': 'स्थिर'},
            ]
            
            # Select 8-10 crops randomly or based on location
            num_crops = random.randint(8, 10)
            selected_crops = random.sample(crop_database, min(num_crops, len(crop_database)))
            
            # Generate crop data with variations
            crops = []
            for crop_data in selected_crops:
                # Add price variation (+/- 10%)
                price_variation = random.uniform(0.9, 1.1)
                current_price = int(crop_data['base_price'] * price_variation)
                msp = crop_data['msp']
                profit = current_price - msp
                profit_pct = round((profit / msp) * 100, 1) if msp > 0 else 0
                
                crops.append({
                    'name': crop_data['name'], # Correct key for JS
                    'crop_name': crop_data['name'], # Access key
                    'crop_name_hindi': crop_data['name_hindi'],
                    'current_price': current_price,
                    'msp': msp,
                    'trend': crop_data['trend'],
                    'profit_margin': profit, # Correct key for JS
                    'profit': profit,
                    'profit_percentage': f"{profit_pct}%",
                    'demand': random.choice(['उच्च', 'मध्यम', 'कम']),
                    'supply': random.choice(['उच्च', 'मध्यम', 'कम']),
                    'mandi': mandi or f"{location} Mandi",
                    'date': datetime.now().strftime('%d/%m/%Y')
                })
            
            # Generate nearby mandis based on location
            mandi_templates = [
                {'suffix': 'Mandi', 'distance': '2 km', 'status': 'खुला', 'specialty': 'अनाज'},
                {'suffix': 'District Mandi', 'distance': '15 km', 'status': 'खुला', 'specialty': 'सब्जियां'},
                {'suffix': 'Central Market', 'distance': '25 km', 'status': 'बंद', 'specialty': 'फल'},
                {'suffix': 'Wholesale Market', 'distance': '10 km', 'status': 'खुला', 'specialty': 'दालें'},
            ]
            
            nearby_mandis = [
                {
                    'name': f"{location} {template['suffix']}" if template['suffix'] != 'District Mandi' else template['suffix'],
                    'distance': template['distance'],
                    'status': template['status'],
                    'specialty': template['specialty']
                }
                for template in mandi_templates
            ]
            
            return {
                'status': 'success',
                'location': location,
                'mandi': mandi or f"{location} Mandi",
                'market_prices': {
                    'crops': crops,
                    'nearby_mandis': nearby_mandis
                },
                'crops': crops,
                'nearby_mandis': nearby_mandis,
                'nearest_mandis_data': nearby_mandis,
                'data_source': 'Enhanced Market Simulation (API Unavailable)',
                'timestamp': datetime.now().isoformat()
            }
                
        except Exception as e:
            logger.error(f"Error in get_market_prices_v2: {e}")
            # Crash safe fallback with minimal valid V2 structure
            return {
                'status': 'success',
                'location': location,
                'mandi': mandi or f"{location} Mandi",
                'market_prices': {'crops': [], 'nearby_mandis': []},
                'crops': [],
                'data_source': 'System Error Fallback'
            }

    def get_government_schemes(self, location: str) -> Dict[str, Any]:
        """
        Get real-time government schemes.
        """
        try:
            raw_data = self._fetch_government_schemes(location)
            
            if raw_data and raw_data.get('status') == 'success':
                return raw_data
            else:
                return self._get_fallback_schemes_data(location)
        except Exception as e:
            logger.error(f"Error in get_government_schemes: {e}")
            return self._get_fallback_schemes_data(location)

    def _get_fallback_schemes_data(self, location: str) -> Dict[str, Any]:
        """Fallback schemes data"""
        return {
            'status': 'success',
            'schemes': [
                {
                    'name': 'PM Kisan Samman Nidhi',
                    'amount': '₹6,000 per year',
                    'description': 'Direct income support to farmers',
                    'eligibility': 'All farmer families',
                    'helpline': '1800-180-1551',
                    'official_website': 'https://pmkisan.gov.in/',
                    'apply_link': 'https://pmkisan.gov.in/'
                },
                {
                    'name': 'Pradhan Mantri Fasal Bima Yojana',
                    'amount': 'Insurance Cover',
                    'description': 'Crop insurance scheme',
                    'eligibility': 'All farmers',
                    'helpline': '1800-180-1551',
                    'official_website': 'https://pmfby.gov.in/',
                    'apply_link': 'https://pmfby.gov.in/'
                }
            ],
            'data': {
                'central_schemes': [],
                'state_schemes': []
            },
            'sources': ['Fallback Schemes Data'],
            'reliability_score': 0.6
        }
