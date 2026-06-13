/**
 * KrishiMitra AI — Multi-Language UI System
 * Supports all 22 Scheduled Indian Languages + English
 *
 * Usage:
 *   setLanguage('ta');           // switch to Tamil
 *   t('nav_home');               // returns translated string
 *   applyTranslations();         // re-render all [data-i18n] elements
 */

(function () {

    // ── Language metadata ──────────────────────────────────────────────
    window.SUPPORTED_LANGUAGES = [
        { code: 'hi',  name: 'हिन्दी',         english: 'Hindi',      dir: 'ltr' },
        { code: 'en',  name: 'English',         english: 'English',    dir: 'ltr' },
        { code: 'bn',  name: 'বাংলা',           english: 'Bengali',    dir: 'ltr' },
        { code: 'te',  name: 'తెలుగు',          english: 'Telugu',     dir: 'ltr' },
        { code: 'mr',  name: 'मराठी',           english: 'Marathi',    dir: 'ltr' },
        { code: 'ta',  name: 'தமிழ்',           english: 'Tamil',      dir: 'ltr' },
        { code: 'gu',  name: 'ગુજરાતી',         english: 'Gujarati',   dir: 'ltr' },
        { code: 'kn',  name: 'ಕನ್ನಡ',           english: 'Kannada',    dir: 'ltr' },
        { code: 'ml',  name: 'മലയാളം',          english: 'Malayalam',  dir: 'ltr' },
        { code: 'pa',  name: 'ਪੰਜਾਬੀ',          english: 'Punjabi',    dir: 'ltr' },
        { code: 'or',  name: 'ଓଡ଼ିଆ',           english: 'Odia',       dir: 'ltr' },
        { code: 'as',  name: 'অসমীয়া',         english: 'Assamese',   dir: 'ltr' },
        { code: 'ur',  name: 'اردو',            english: 'Urdu',       dir: 'rtl' },
        { code: 'mai', name: 'मैथिली',          english: 'Maithili',   dir: 'ltr' },
        { code: 'kok', name: 'कोंकणी',          english: 'Konkani',    dir: 'ltr' },
        { code: 'ne',  name: 'नेपाली',          english: 'Nepali',     dir: 'ltr' },
        { code: 'mni', name: 'মৈতৈলোন্',        english: 'Manipuri',   dir: 'ltr' },
        { code: 'sd',  name: 'سنڌي',           english: 'Sindhi',     dir: 'rtl' },
        { code: 'ks',  name: 'کشمیری',          english: 'Kashmiri',   dir: 'rtl' },
        { code: 'doi', name: 'डोगरी',           english: 'Dogri',      dir: 'ltr' },
        { code: 'bo',  name: 'बड़ो',            english: 'Bodo',       dir: 'ltr' },
        { code: 'sat', name: 'ᱥᱟᱱᱛᱟᱲᱤ',        english: 'Santali',    dir: 'ltr' },
    ];

    // ── Translations dictionary ────────────────────────────────────────
    const T = {
        // Navigation
        nav_home: {
            hi: 'होम', en: 'Home', bn: 'হোম', te: 'హోమ్', mr: 'मुख्यपृष्ठ',
            ta: 'முகப்பு', gu: 'હોમ', kn: 'ಮುಖಪುಟ', ml: 'ഹോം',
            pa: 'ਹੋਮ', or: 'ହୋମ', as: 'হোম', ur: 'ہوم'
        },
        nav_schemes: {
            hi: 'योजनाएं', en: 'Schemes', bn: 'প্রকল্প', te: 'పథకాలు', mr: 'योजना',
            ta: 'திட்டங்கள்', gu: 'યોજنаઓ', kn: 'ಯೋಜನೆಗಳು', ml: 'പദ്ധതികൾ',
            pa: 'ਸਕੀਮਾਂ', or: 'ଯୋଜନା', as: 'আঁচনি', ur: 'اسکیمیں'
        },
        nav_ai: {
            hi: 'AI सहायक', en: 'AI Assistant', bn: 'AI সহায়ক', te: 'AI సహాయకుడు',
            mr: 'AI सहाय्यक', ta: 'AI உதவியாளர்', gu: 'AI સહાયક', kn: 'AI ಸಹಾಯಕ',
            ml: 'AI സഹായി', pa: 'AI ਸਹਾਇਕ', or: 'AI ସହାୟକ', as: 'AI সহায়ক', ur: 'AI معاون'
        },
        // Hero
        hero_title: {
            hi: '🌾 कृषिमित्र AI', en: '🌾 KrishiMitra AI', bn: '🌾 কৃষিমিত্র AI',
            te: '🌾 కృషిమిత్ర AI', mr: '🌾 कृषिमित्र AI', ta: '🌾 கிருஷிமித்ர AI',
            gu: '🌾 કૃષિમિત્ર AI', kn: '🌾 ಕೃಷಿಮಿತ್ರ AI', ml: '🌾 കൃഷിമിത്ര AI',
            pa: '🌾 ਕ੍ਰਿਸ਼ੀਮਿਤਰ AI', or: '🌾 କୃଷିମିତ୍ର AI', as: '🌾 কৃষিমিত্ৰ AI', ur: '🌾 کرشی متر AI'
        },
        hero_subtitle: {
            hi: 'किसानों का सबसे अच्छा दोस्त — AI से स्मार्ट खेती करें',
            en: "Farmer's best friend — farm smarter with AI",
            bn: 'কৃষকের সেরা বন্ধু — AI দিয়ে স্মার্ট চাষ করুন',
            te: 'రైతు యొక్క అత్యుత్తమ స్నేహితుడు — AI తో స్మార్ట్ వ్యవసాయం',
            mr: 'शेतकऱ्याचा सर्वोत्तम मित्र — AI ने स्मार्ट शेती करा',
            ta: 'விவசாயியின் சிறந்த நண்பன் — AI கொண்டு திறமையாக விவசாயம்',
            gu: 'ખેડૂતનો સૌથી સારો મિત્ર — AI સાથે સ્માર્ટ ખેતી',
            kn: 'ರೈತರ ಉತ್ತಮ ಸ್ನೇಹಿತ — AI ನಿಂದ ಸ್ಮಾರ್ಟ್ ಕೃಷಿ',
            ml: 'കർഷകന്റെ ഏറ്റവും നല്ല സുഹൃത്ത് — AI ഉപയോഗിച്ച് ഒ smart കൃഷി',
            pa: 'ਕਿਸਾਨ ਦਾ ਸਭ ਤੋਂ ਚੰਗਾ ਦੋਸਤ — AI ਨਾਲ ਸਮਾਰਟ ਖੇਤੀ',
            or: 'ଚାଷୀଙ୍କ ସର୍ବୋତ୍ତମ ବନ୍ଧୁ — AI ସହ ସ୍ମାର୍ଟ ଚାଷ',
            as: 'কৃষকৰ সৰ্বশ্ৰেষ্ঠ বন্ধু — AI সৈতে স্মাৰ্ট খেতি',
            ur: 'کسان کا بہترین دوست — AI کے ساتھ ذہین کھیتی'
        },
        // Location search
        location_placeholder: {
            hi: 'शहर, जिला या गाँव खोजें...',
            en: 'Search city, district or village...',
            bn: 'শহর, জেলা বা গ্রাম খুঁজুন...',
            te: 'నగరం, జిల్లా లేదా గ్రామం శోధించండి...',
            mr: 'शहर, जिल्हा किंवा गाव शोधा...',
            ta: 'நகர், மாவட்டம் அல்லது கிராமம் தேடுங்கள்...',
            gu: 'શહેર, જિલ્લો અથવા ગામ શોધો...',
            kn: 'ನಗರ, ಜಿಲ್ಲೆ ಅಥವಾ ಗ್ರಾಮ ಹುಡುಕಿ...',
            ml: 'നഗരം, ജില്ല അല്ലെങ്കിൽ ഗ്രാമം തിരയുക...',
            pa: 'ਸ਼ਹਿਰ, ਜ਼ਿਲ੍ਹਾ ਜਾਂ ਪਿੰਡ ਖੋਜੋ...',
            or: 'ସହର, ଜିଲ୍ଲା ବା ଗ୍ରାମ ଖୋଜନ୍ତୁ...',
            as: 'চহৰ, জিলা বা গাঁও বিচাৰক...',
            ur: 'شہر، ضلع یا گاؤں تلاش کریں...'
        },
        // Services
        service_schemes: {
            hi: 'सरकारी योजनाएं', en: 'Government Schemes', bn: 'সরকারি প্রকল্প',
            te: 'ప్రభుత్వ పథకాలు', mr: 'सरकारी योजना', ta: 'அரசு திட்டங்கள்',
            gu: 'સરકારી યોજнаઓ', kn: 'ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು', ml: 'സർക്കാർ പദ്ധതികൾ',
            pa: 'ਸਰਕਾਰੀ ਸਕੀਮਾਂ', or: 'ସରକାରୀ ଯୋଜନା', as: 'চৰকাৰী আঁচনি', ur: 'سرکاری اسکیمیں'
        },
        service_crops: {
            hi: 'फसल सुझाव', en: 'Crop Recommendations', bn: 'ফসল পরামর্শ',
            te: 'పంట సూచనలు', mr: 'पीक शिफारशी', ta: 'பயிர் பரிந்துரைகள்',
            gu: 'પાક ભલামણ', kn: 'ಬೆಳೆ ಶಿಫಾರಸ್ಸುಗಳು', ml: 'വിള ശുപാർശകൾ',
            pa: 'ਫ਼ਸਲ ਸੁਝਾਅ', or: 'ଫସଲ ପରାମର୍ଶ', as: 'শস্য পৰামৰ্শ', ur: 'فصل کی سفارشات'
        },
        service_weather: {
            hi: 'मौसम पूर्वानुमान', en: 'Weather Forecast', bn: 'আবহাওয়ার পূর্বাভাস',
            te: 'వాతావరణ అంచనా', mr: 'हवामान अंदाज', ta: 'வானிலை முன்னறிவிப்பு',
            gu: 'હવામાન આગાહી', kn: 'ಹವಾಮಾನ ಮುನ್ಸೂಚನೆ', ml: 'കാലാവസ്ഥ പ്രവചനം',
            pa: 'ਮੌਸਮ ਪੂਰਵਾਨੁਮਾਨ', or: 'ପାଣିପାଗ ପୂର୍ବାନୁମାନ', as: 'বতৰ পূৰ্বাভাস', ur: 'موسم کی پیشگوئی'
        },
        service_market: {
            hi: 'बाजार कीमतें', en: 'Market Prices', bn: 'বাজার মূল্য',
            te: 'మార్కెట్ ధరలు', mr: 'बाजार भाव', ta: 'சந்தை விலைகள்',
            gu: 'બજાર ભાવ', kn: 'ಮಾರ್ಕೆಟ್ ಬೆಲೆಗಳು', ml: 'ചന്ത വിലകൾ',
            pa: 'ਬਾਜ਼ਾਰ ਭਾਅ', or: 'ବଜାର ଦର', as: 'বজাৰৰ মূল্য', ur: 'بازار کی قیمتیں'
        },
        service_pest: {
            hi: 'फसल रक्षा', en: 'Crop Protection', bn: 'ফসল সুরক্ষা',
            te: 'పంట రక్షణ', mr: 'पीक संरक्षण', ta: 'பயிர் பாதுகாப்பு',
            gu: 'પાક સુરક્ષા', kn: 'ಬೆಳೆ ರಕ್ಷಣೆ', ml: 'വിള സംരക്ഷണം',
            pa: 'ਫ਼ਸਲ ਸੁਰੱਖਿਆ', or: 'ଫସଲ ସୁରକ୍ଷା', as: 'শস্য সুৰক্ষা', ur: 'فصل تحفظ'
        },
        service_ai: {
            hi: 'AI सहायक', en: 'AI Assistant', bn: 'AI সহায়ক', te: 'AI సహాయకుడు',
            mr: 'AI सहाय्यक', ta: 'AI உதவியாளர்', gu: 'AI સહાયક', kn: 'AI ಸಹಾಯಕ',
            ml: 'AI സഹായി', pa: 'AI ਸਹਾਇਕ', or: 'AI ସହାୟକ', as: 'AI সহায়ক', ur: 'AI معاون'
        },
        service_field: {
            hi: 'खेत-स्तरीय सलाह', en: 'Field Advisory', bn: 'মাঠ-স্তরীয় পরামর্শ',
            te: 'పొలం స్థాయి సలహా', mr: 'शेत-स्तरीय सल्ला', ta: 'வயல் அளவிலான ஆலோசனை',
            // Bug #8 fix: 'gu' value was corrupted: 'ખેત-સ્તriy Slaah' (mixed Gujarati/Latin gibberish)
            // Correct Gujarati for 'Field Advisory' is 'ખેત-સ્તરીય સલાહ'
            gu: 'ખેત-સ્તરીય સલાહ', kn: 'ಕ್ಷೇತ್ರ ಮಟ್ಟದ ಸಲಹೆ', ml: 'ഫീൽഡ് ഉപദേശം',
            pa: 'ਖੇਤ-ਪੱਧਰੀ ਸਲਾਹ', or: 'ଫିଲ୍ଡ ଆଡ଼ଭାଇଜ', as: 'পথাৰ-স্তৰীয় পৰামৰ্শ', ur: 'فیلڈ ایڈوائزری'
        },
        // AI Chat
        chat_placeholder: {
            hi: 'अपना सवाल यहाँ लिखें... (हिंदी, English, Hinglish)',
            en: 'Type your question here... (any Indian language or English)',
            bn: 'এখানে আপনার প্রশ্ন লিখুন...',
            te: 'మీ ప్రశ్నను ఇక్కడ టైప్ చేయండి...',
            mr: 'तुमचा प्रश्न येथे लिहा...',
            ta: 'உங்கள் கேள்வியை இங்கே தட்டச்சு செய்யுங்கள்...',
            gu: 'તમારો પ્રશ્ન અહીં ટાઈપ કરો...',
            kn: 'ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಇಲ್ಲಿ ಟೈಪ್ ಮಾಡಿ...',
            ml: 'നിങ്ങളുടെ ചോദ്യം ഇവിടെ ടൈപ്പ് ചെയ്യുക...',
            pa: 'ਇੱਥੇ ਆਪਣਾ ਸਵਾਲ ਟਾਈਪ ਕਰੋ...',
            or: 'ଆପଣଙ୍କ ପ୍ରଶ୍ନ ଏଠାରେ ଲିଖନ୍ତୁ...',
            as: 'আপোনাৰ প্ৰশ্ন ইয়াত লিখক...',
            ur: 'اپنا سوال یہاں ٹائپ کریں...'
        },
        chat_send: {
            hi: 'भेजें', en: 'Send', bn: 'পাঠান', te: 'పంపు', mr: 'पाठवा',
            ta: 'அனுப்பு', gu: 'મોકલો', kn: 'ಕಳಿಸಿ', ml: 'അയയ്‌ക്കുക',
            pa: 'ਭੇਜੋ', or: 'ପଠାନ୍ତୁ', as: 'পঠাওক', ur: 'بھیجیں'
        },
        // Market
        market_select_mandi: {
            hi: '🏪 मंडी चुनें', en: '🏪 Select Mandi', bn: '🏪 মান্ডি নির্বাচন করুন',
            te: '🏪 మండి ఎంచుకోండి', mr: '🏪 मंडी निवडा', ta: '🏪 மந்தி தேர்ந்தெடுக்கவும்',
            gu: '🏪 મંડી પસંદ કરો', kn: '🏪 ಮಂಡಿ ಆರಿಸಿ', ml: '🏪 മണ്ടി തിരഞ്ഞെടുക്കുക',
            pa: '🏪 ਮੰਡੀ ਚੁਣੋ', or: '🏪 ମଣ୍ଡି ଚୟନ', as: '🏪 মণ্ডি বাছক', ur: '🏪 منڈی منتخب کریں'
        },
        market_refresh: {
            hi: 'रिफ्रेश करें', en: 'Refresh', bn: 'রিফ্রেশ করুন', te: 'రిఫ్రెష్',
            mr: 'ताजे करा', ta: 'புதுப்பிக்கவும்', gu: 'રીફ્રેશ', kn: 'ರಿಫ್ರೆಶ್',
            ml: 'പുതുക്കുക', pa: 'ਤਾਜ਼ਾ ਕਰੋ', or: 'ତାଜା କରନ୍ତୁ', as: 'সতেজ কৰক', ur: 'تازہ کریں'
        },
        // Weather
        weather_temp: {
            hi: 'तापमान', en: 'Temperature', bn: 'তাপমাত্রা', te: 'ఉష్ణోగ్రత',
            mr: 'तापमान', ta: 'வெப்பநிலை', gu: 'તાપમાન', kn: 'ತಾಪಮಾನ',
            ml: 'താപനില', pa: 'ਤਾਪਮਾਨ', or: 'ତାପମାତ୍ରା', as: 'উষ্ণতা', ur: 'درجہ حرارت'
        },
        weather_humidity: {
            hi: 'नमी', en: 'Humidity', bn: 'আর্দ্রতা', te: 'తేమ',
            mr: 'आर्द्रता', ta: 'ஈரப்பதம்', gu: 'ભેજ', kn: 'ಆರ್ದ್ರತೆ',
            ml: 'ഈർപ്പം', pa: 'ਨਮੀ', or: 'ଆର୍ଦ୍ରତା', as: 'আৰ্দ্ৰতা', ur: 'نمی'
        },
        weather_wind: {
            hi: 'हवा की गति', en: 'Wind Speed', bn: 'বাতাসের গতি', te: 'గాలి వేగం',
            mr: 'वाऱ्याचा वेग', ta: 'காற்று வேகம்', gu: 'પવનની ઝડપ', kn: 'ಗಾಳಿಯ ವೇಗ',
            ml: 'കാറ്റ് വേഗത', pa: 'ਹਵਾ ਦੀ ਗਤੀ', or: 'ପବନ ବେଗ', as: 'বতাহৰ গতি', ur: 'ہوا کی رفتار'
        },
        weather_rain: {
            hi: 'वर्षा', en: 'Rainfall', bn: 'বৃষ্টিপাত', te: 'వర్షపాతం',
            mr: 'पर्जन्यमान', ta: 'மழைப்பொழிவு', gu: 'વરસાદ', kn: 'ಮಳೆ',
            ml: 'മഴ', pa: 'ਬਾਰਿਸ਼', or: 'ବୃଷ୍ଟି', as: 'বৰষুণ', ur: 'بارش'
        },
        // Loading/error
        loading: {
            hi: 'लोड हो रहा है...', en: 'Loading...', bn: 'লোড হচ্ছে...',
            te: 'లోడ్ అవుతోంది...', mr: 'लोड होत आहे...', ta: 'ஏற்றுகிறது...',
            gu: 'લોડ થઈ રહ્યું છે...', kn: 'ಲೋಡ್ ಆಗುತ್ತಿದೆ...', ml: 'ലോഡ് ആകുന്നു...',
            pa: 'ਲੋਡ ਹੋ ਰਿਹਾ ਹੈ...', or: 'ଲୋଡ ହେଉଛି...', as: 'লোড হৈছে...', ur: 'لوڈ ہو رہا ہے...'
        },
        detect_location: {
            hi: 'स्थान पता करें', en: 'Detect Location', bn: 'অবস্থান সনাক্ত করুন',
            te: 'స్థానాన్ని గుర్తించండి', mr: 'स्थान शोधा', ta: 'இடத்தை கண்டறியுங்கள்',
            gu: 'સ્થાન શોધો', kn: 'ಸ್ಥಳ ಪತ್ತೆ ಮಾಡಿ', ml: 'സ്ഥാനം കണ്ടെത്തുക',
            pa: 'ਸਥਾਨ ਲੱਭੋ', or: 'ଅବସ୍ଥାନ ଖୋଜନ୍ତୁ', as: 'স্থান বিচাৰক', ur: 'مقام تلاش کریں'
        },
        // Crop recommendation section
        crop_search_placeholder: {
            hi: 'फसल खोजें (जैसे: गेहूं, धान, मक्का)...',
            en: 'Search crop (e.g. Wheat, Rice, Maize)...',
            bn: 'ফসল খুঁজুন (যেমন: গম, ধান, ভুট্টা)...',
            te: 'పంట శోధించండి (ఉదా: గోధుమ, వరి, మొక్కజొన్న)...',
            mr: 'पीक शोधा (उदा: गहू, भात, मका)...',
            ta: 'பயிர் தேடுங்கள் (எ.கா: கோதுமை, நெல், சோளம்)...',
            gu: 'પાક શોધો (ઉ.દા: ઘઉં, ડાંગર, મકાઈ)...',
            kn: 'ಬೆಳೆ ಹುಡುಕಿ (ಉದಾ: ಗೋಧಿ, ಭತ್ತ, ಜೋಳ)...',
            ml: 'വിള തിരയുക (ഉദാ: ഗോതമ്പ്, നെല്ല്, ചോളം)...',
            pa: 'ਫ਼ਸਲ ਖੋਜੋ (ਜਿਵੇਂ: ਕਣਕ, ਝੋਨਾ, ਮੱਕੀ)...',
            or: 'ଫସଲ ଖୋଜନ୍ତୁ (ଉ.ଦା: ଗହମ, ଧାନ, ମକା)...',
            as: 'শস্য বিচাৰক (যেনে: ঘেঁহু, ধান, ভুট্টা)...',
            ur: 'فصل تلاش کریں (مثلاً: گندم، دھان، مکئی)...'
        },
        // Schemes
        scheme_apply: {
            hi: 'अभी आवेदन करें', en: 'Apply Now', bn: 'এখনই আবেদন করুন',
            te: 'ఇప్పుడే దరఖాస్తు', mr: 'आता अर्ज करा', ta: 'இப்போது விண்ணப்பிக்கவும்',
            gu: 'હવે અરજી કરો', kn: 'ಈಗ ಅರ್ಜಿ ಹಾಕಿ', ml: 'ഇപ്പോൾ അപേക്ഷിക്കുക',
            pa: 'ਹੁਣੇ ਅਰਜ਼ੀ ਕਰੋ', or: 'ଏବେ ଆବେଦନ', as: 'এতিয়াই আবেদন কৰক', ur: 'ابھی درخواست دیں'
        },
        // Language selector label
        language_label: {
            hi: '🌐 भाषा', en: '🌐 Language', bn: '🌐 ভাষা', te: '🌐 భాష', mr: '🌐 भाषा',
            ta: '🌐 மொழி', gu: '🌐 ભાષા', kn: '🌐 ಭಾಷೆ', ml: '🌐 ഭാഷ',
            pa: '🌐 ਭਾਸ਼ਾ', or: '🌐 ଭାଷା', as: '🌐 ভাষা', ur: '🌐 زبان'
        },
    };

    // ── Current language state ─────────────────────────────────────────
    let _currentLang = 'hi';

    /** Translate a key to the current language (falls back to Hindi, then key). */
    window.t = function (key, lang) {
        const l = lang || _currentLang;
        const entry = T[key];
        if (!entry) return key;
        return entry[l] || entry['hi'] || entry['en'] || key;
    };

    window.getCurrentLang = function () { return _currentLang; };

    /** Set active language and update the whole UI. */
    window.setLanguage = function (code) {
        code = (code || 'hi').toLowerCase();
        // Find in supported list; fallback to first 2 chars
        const known = SUPPORTED_LANGUAGES.find(l => l.code === code);
        if (!known) {
            const short = code.slice(0, 2);
            const byShort = SUPPORTED_LANGUAGES.find(l => l.code === short);
            code = byShort ? byShort.code : 'hi';
        }
        _currentLang = code;

        // Persist
        try { localStorage.setItem('km_lang', code); } catch (_) {}

        // RTL support
        const langObj = SUPPORTED_LANGUAGES.find(l => l.code === code);
        document.documentElement.lang = langObj ? langObj.bcp47 || code : code;
        document.documentElement.dir = (langObj && langObj.dir === 'rtl') ? 'rtl' : 'ltr';

        applyTranslations();
        _updateLanguageDropdown(code);
    };

    /** Apply translations to all [data-i18n] elements. */
    window.applyTranslations = function () {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const target = el.getAttribute('data-i18n-target') || 'textContent';
            const translated = window.t(key);
            if (target === 'placeholder') {
                el.placeholder = translated;
            } else if (target === 'title') {
                el.title = translated;
            } else {
                el.textContent = translated;
            }
        });
    };

    function _updateLanguageDropdown(code) {
        const sel = document.getElementById('languageSwitcher');
        if (sel) sel.value = code;
    }

    /** Build and inject the language switcher dropdown into the navbar. */
    window.buildLanguageSwitcher = function () {
        const nav = document.querySelector('.navbar-nav');
        if (!nav || document.getElementById('languageSwitcher')) return;

        const li = document.createElement('li');
        li.className = 'nav-item';

        const sel = document.createElement('select');
        sel.id = 'languageSwitcher';
        sel.className = 'form-select form-select-sm language-switcher';
        sel.title = 'भाषा / Language';
        sel.style.cssText = (
            'width:auto;min-width:130px;margin:6px 8px;'
            + 'border:1.5px solid rgba(255,255,255,0.4);background:rgba(255,255,255,0.15);'
            + 'color:white;border-radius:20px;padding:4px 10px;font-size:0.88rem;cursor:pointer;'
        );

        SUPPORTED_LANGUAGES.forEach(lang => {
            const opt = document.createElement('option');
            opt.value = lang.code;
            opt.textContent = `${lang.name} (${lang.english})`;
            if (lang.code === _currentLang) opt.selected = true;
            sel.appendChild(opt);
        });

        sel.addEventListener('change', function () {
            window.setLanguage(this.value);
        });

        li.appendChild(sel);
        nav.appendChild(li);
    };

    /** Detect best language from browser locale or persisted preference. */
    window.detectInitialLanguage = function () {
        // 1. Persisted preference
        try {
            const saved = localStorage.getItem('km_lang');
            if (saved) return saved;
        } catch (_) {}

        // 2. Browser language
        const bcp = (navigator.language || navigator.userLanguage || 'hi').toLowerCase();
        // Map browser BCP-47 to our codes
        const browserMap = {
            'hi': 'hi', 'en': 'en', 'bn': 'bn', 'te': 'te', 'mr': 'mr',
            'ta': 'ta', 'gu': 'gu', 'kn': 'kn', 'ml': 'ml', 'pa': 'pa',
            'or': 'or', 'as': 'as', 'ur': 'ur', 'ne': 'ne',
        };
        const prefix = bcp.split('-')[0];
        if (browserMap[prefix]) return browserMap[prefix];

        return 'hi';
    };

    // ── Initialise on DOM ready ────────────────────────────────────────
    function _init() {
        const lang = window.detectInitialLanguage();
        _currentLang = lang;
        window.buildLanguageSwitcher();
        window.applyTranslations();
        document.documentElement.lang = lang;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _init);
    } else {
        _init();
    }

})();
