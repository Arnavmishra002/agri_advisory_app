"""
Government Schemes Data
Real government schemes for farmers with official links
"""

CENTRAL_GOVERNMENT_SCHEMES = [
    {
        'id': 'pm_kisan',
        'name': 'प्रधानमंत्री किसान सम्मान निधि (PM-KISAN)',
        'name_en': 'PM-Kisan Samman Nidhi',
        'amount': '₹6,000 प्रति वर्ष',
        'description': 'सभी भूमिधारक किसान परिवारों को तीन किस्तों में ₹2,000 की सीधी आय सहायता',
        'eligibility': 'सभी भूमिधारक किसान परिवार',
        'benefits': ['₹2,000 प्रति 4 महीने', 'सीधे बैंक खाते में', 'ऑनलाइन आवेदन'],
        'official_website': 'https://pmkisan.gov.in/',
        'helpline': '155261 / 011-24300606',
        'apply_link': 'https://pmkisan.gov.in/RegistrationForm.aspx'
    },
    {
        'id': 'fasal_bima',
        'name': 'प्रधानमंत्री फसल बीमा योजना (PMFBY)',
        'name_en': 'Pradhan Mantri Fasal Bima Yojana',
        'amount': 'कम प्रीमियम पर पूर्ण फसल सुरक्षा',
        'description': 'प्राकृतिक आपदाओं से फसल नुकसान के लिए बीमा कवरेज। किसानों के लिए बहुत कम प्रीमियम दर',
        'eligibility': 'सभी किसान (स्वामी और किरायेदार)',
        'benefits': ['खरीफ: 2% प्रीमियम', 'रबी: 1.5% प्रीमियम', 'तुरंत क्लेम सेटलमेंट'],
        'official_website': 'https://pmfby.gov.in/',
        'helpline': '011-23382012',
        'apply_link': 'https://pmfby.gov.in/farmerRegistrationLogin'
    },
    {
        'id': 'kisan_credit',
        'name': 'किसान क्रेडिट कार्ड (KCC)',
        'name_en': 'Kisan Credit Card',
        'amount': 'कम ब्याज दर पर ₹3 लाख तक ऋण',
        'description': 'किसानों को खेती के लिए समय पर और पर्याप्त ऋण उपलब्ध कराना',
        'eligibility': 'सभी किसान, मछुआरे, पशुपालक',
        'benefits': ['4% ब्याज दर', '₹3 लाख तक ऋण', 'आसान प्रक्रिया'],
        'official_website': 'https://www.nabard.org/content1.aspx?id=575&catid=8&mid=530',
        'helpline': '1800-180-1111',
        'apply_link': 'https://www.nabard.org/content1.aspx?id=575&catid=8&mid=530'
    },
    {
        'id': 'pm_kusum',
        'name': 'PM-KUSUM योजना',
        'name_en': 'PM-KUSUM (Solar Pump)',
        'amount': '60% सब्सिडी सोलर पंप पर',
        'description': 'किसानों को सोलर पंप की स्थापना के लिए 60% सब्सिडी',
        'eligibility': 'सभी किसान',
        'benefits': ['60% सब्सिडी', 'बिजली बिल में बचत', 'पर्यावरण अनुकूल'],
        'official_website': 'https://mnre.gov.in/solar/schemes/',
        'helpline': '1800-180-3333',
        'apply_link': 'https://pmkusum.mnre.gov.in/'
    },
    {
        'id': 'kisan_rath',
        'name': 'किसान रथ मोबाइल ऐप',
        'name_en': 'Kisan Rath Mobile App',
        'amount': 'निःशुल्क परिवहन सुविधा',
        'description': 'किसानों और परिवहन वाहनों को जोड़ने के लिए ऐप',
        'eligibility': 'सभी किसान',
        'benefits': ['निःशुल्क', 'तुरंत ट्रांसपोर्ट', 'ऑनलाइन बुकिंग'],
        'official_website': 'https://kisanrath.nic.in/',
        'helpline': '1800-180-1551',
        'apply_link': 'https://play.google.com/store/apps/details?id=com.nic.KisanRath'
    },
    {
        'id': 'soil_health',
        'name': 'सॉयल हेल्थ कार्ड योजना',
        'name_en': 'Soil Health Card Scheme',
        'amount': 'निःशुल्क मिट्टी परीक्षण',
        'description': 'किसानों को मिट्टी की सेहत की जानकारी देने के लिए कार्ड',
        'eligibility': 'सभी किसान',
        'benefits': ['मुफ्त मिट्टी परीक्षण', 'सही खाद की सलाह', 'उत्पादकता बढ़ाएं'],
        'official_website': 'https://soilhealth.dac.gov.in/',
        'helpline': '011-24305948',
        'apply_link': 'https://soilhealth.dac.gov.in/'
    },
    {
        'id': 'kisan_drone',
        'name': 'किसान ड्रोन योजना',
        'name_en': 'Kisan Drone Yojana',
        'amount': '40-50% सब्सिडी ड्रोन पर',
        'description': 'कृषि कार्यों के लिए ड्रोन खरीदने पर सब्सिडी',
        'eligibility': 'किसान, एफपीओ, ग्रामीण उद्यमी',
        'benefits': ['SC/ST: 50% सब्सिडी', 'महिला: 50% सब्सिडी', 'अन्य: 40% सब्सिडी'],
        'official_website': 'https://agricoop.nic.in/',
        'helpline': '011-23382691',
        'apply_link': 'https://agricoop.nic.in/en/kisan-drones'
    },
    {
        'id': 'organic_farming',
        'name': 'परंपरागत कृषि विकास योजना (PKVY)',
        'name_en': 'Paramparagat Krishi Vikas Yojana',
        'amount': '₹50,000 प्रति हेक्टेयर',
        'description': 'जैविक खेती को बढ़ावा देने के लिए वित्तीय सहायता',
        'eligibility': 'जैविक खेती करने वाले किसान',
        'benefits': ['₹50,000/हेक्टेयर', 'प्रशिक्षण', 'प्रमाणीकरण सहायता'],
        'official_website': 'https://pgsindia-ncof.gov.in/',
        'helpline': '011-23070004',
        'apply_link': 'https://pgsindia-ncof.gov.in/PKVY/Index.aspx'
    },
    {
        'id': 'kisan_mall',
        'name': 'किसान ई-मॉल',
        'name_en': 'Kisan e-Mall',
        'amount': 'ऑनलाइन खरीदारी सुविधा',
        'description': 'कृषि इनपुट ऑनलाइन खरीदने की सुविधा',
        'eligibility': 'सभी किसान',
        'benefits': ['घर बैठे खरीदारी', 'सही कीमत', 'गुणवत्ता की गारंटी'],
        'official_website': 'https://www.kisanemall.com/',
        'helpline': '1800-180-1551',
        'apply_link': 'https://www.kisanemall.com/'
    },
    {
        'id': 'mkisan',
        'name': 'mKisan पोर्टल',
        'name_en': 'mKisan Portal',
        'amount': 'मुफ्त SMS सलाह',
        'description': 'मोबाइल पर खेती की सलाह SMS के माध्यम से',
        'eligibility': 'सभी किसान',
        'benefits': ['मुफ्त SMS', 'मौसम की जानकारी', 'बाजार भाव'],
        'official_website': 'https://mkisan.gov.in/',
        'helpline': '1800-180-1551',
        'apply_link': 'https://mkisan.gov.in/Home/English'
    }
]

STATE_SPECIFIC_SCHEMES = {
    'Delhi': [
        {
            'name': 'मुख्यमंत्री किसान और सर्वहित बीमा योजना',
            'amount': '₹5 लाख दुर्घटना बीमा',
            'description': 'दिल्ली के किसानों के लिए निःशुल्क बीमा',
            'website': 'http://delhi.gov.in/'
        }
    ],
    'Punjab': [
        {
            'name': 'पंजाब किसान कर्ज माफी योजना',
            'amount': 'ऋण माफी',
            'description': 'छोटे और सीमांत किसानों का कर्ज माफ',
            'website': 'https://punjab.gov.in/'
        }
    ],
    'Maharashtra': [
        {
            'name': 'महात्मा ज्योतिबा फुले कर्ज मुक्ति योजना',
            'amount': 'ऋण माफी',
            'description': 'किसानों का कर्ज माफ करने की योजना',
            'website': 'https://maharashtra.gov.in/'
        }
    ],
    'Kerala': [
        {
            'name': 'केरल किसान ऋण राहत योजना',
            'amount': 'ब्याज मुक्त ऋण',
            'description': 'किसानों को ब्याज मुक्त ऋण',
            'website': 'https://kerala.gov.in/'
        }
    ],
    'Tamil Nadu': [
        {
            'name': 'सीएम किसान सम्मान योजना',
            'amount': '₹4,000 प्रति वर्ष',
            'description': 'किसानों को अतिरिक्त आर्थिक सहायता',
            'website': 'https://tn.gov.in/'
        }
    ]
}

def get_all_schemes(location='Delhi'):
    """Get all government schemes for a location"""
    schemes_data = {
        'central_schemes': CENTRAL_GOVERNMENT_SCHEMES,
        'state_schemes': STATE_SPECIFIC_SCHEMES.get(location, []),
        'total_schemes': len(CENTRAL_GOVERNMENT_SCHEMES) + len(STATE_SPECIFIC_SCHEMES.get(location, [])),
        'location': location
    }
    return schemes_data

def get_scheme_by_id(scheme_id):
    """Get specific scheme by ID"""
    for scheme in CENTRAL_GOVERNMENT_SCHEMES:
        if scheme['id'] == scheme_id:
            return scheme
    return None

