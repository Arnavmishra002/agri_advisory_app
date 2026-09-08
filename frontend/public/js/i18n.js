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
        nav_profile: {
            hi: 'मेरी प्रोफ़ाइल', en: 'My Profile', bn: 'আমার প্রোফাইল', ta: 'என் சுயவிவரம்',
            te: 'నా ప్రొఫైల్', mr: 'माझी प्रोफाइल', gu: 'મારી પ્રોફાઇલ', kn: 'ನನ್ನ ಪ್ರೊಫೈಲ್',
            ml: 'എന്റെ പ്രൊഫൈൽ', pa: 'ਮੇਰੀ ਪ੍ਰੋਫਾਈਲ', or: 'ମୋର ପ୍ରୋଫାଇଲ', ur: 'میری پروفائل',
            as: 'মোৰ প্ৰফাইল', ne: 'मेरो प्रोफाइल'
        },
        chat_suggested_title: {
            hi: '💡 अक्सर पूछे जाने वाले सवाल:', en: '💡 Suggested questions:',
            bn: '💡 প্রস্তাবিত প্রশ্ন:', ta: '💡 பரிந்துரைக்கப்பட்ட கேள்விகள்:',
            te: '💡 సూచించిన ప్రశ్నలు:', mr: '💡 सुचवलेले प्रश्न:', gu: '💡 સૂચવેલા પ્રશ્નો:',
            kn: '💡 ಸೂಚಿಸಿದ ಪ್ರಶ್ನೆಗಳು:', ml: '💡 നിർദ്ദേശിച്ച ചോദ്യങ്ങൾ:',
            pa: '💡 ਸੁਝਾਏ ਸਵਾਲ:', or: '💡 ପ୍ରସ୍ତାବିତ ପ୍ରଶ୍ନ:', ur: '💡 تجویز کردہ سوالات:',
            as: '💡 প্ৰস্তাৱিত প্ৰশ্ন:', ne: '💡 सुझाव गरिएका प्रश्नहरू:'
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
        // Shown when the official feed has simply not published today's row
        // yet. This replaces a raw English operator string that was reaching
        // farmers verbatim -- it named an env var and an upstream API. Only
        // languages that can be translated accurately are listed; t() falls
        // back to Hindi, which is better than a guessed translation.
        // Home navigation and quick actions. These were hardcoded Hindi in
        // index.html, so a farmer who picked Tamil or Bengali still saw the
        // app's primary buttons in a script they may not read -- measured:
        // selecting Tamil left 14 of 35 visible strings in Devanagari.
        nav_weather: {
            hi: '🌤️ मौसम', en: '🌤️ Weather', bn: '🌤️ আবহাওয়া', te: '🌤️ వాతావరణం',
            mr: '🌤️ हवामान', ta: '🌤️ வானிலை', gu: '🌤️ હવામાન', kn: '🌤️ ಹವಾಮಾನ',
            ml: '🌤️ കാലാവസ്ഥ', pa: '🌤️ ਮੌਸਮ', or: '🌤️ ପାଣିପାଗ', as: '🌤️ বতৰ',
            ur: '🌤️ موسم', ne: '🌤️ मौसम', mai: '🌤️ मौसम'
        },
        nav_market: {
            hi: '💰 बाजार', en: '💰 Market', bn: '💰 বাজার', te: '💰 మార్కెట్',
            mr: '💰 बाजार', ta: '💰 சந்தை', gu: '💰 બજાર', kn: '💰 ಮಾರುಕಟ್ಟೆ',
            ml: '💰 വിപണി', pa: '💰 ਬਾਜ਼ਾਰ', or: '💰 ବଜାର', as: '💰 বজাৰ',
            ur: '💰 بازار', ne: '💰 बजार', mai: '💰 बाजार'
        },
        qa_ask_ai: {
            hi: 'AI से पूछें', en: 'Ask AI', bn: 'AI-কে জিজ্ঞাসা করুন', te: 'AIని అడగండి',
            mr: 'AI ला विचारा', ta: 'AI-யிடம் கேளுங்கள்', gu: 'AI ને પૂછો', kn: 'AI ಕೇಳಿ',
            ml: 'AI-യോട് ചോദിക്കുക', pa: 'AI ਨੂੰ ਪੁੱਛੋ', or: 'AI କୁ ପଚାରନ୍ତୁ', as: 'AI ক সোধক',
            ur: 'AI سے پوچھیں', ne: 'AI लाई सोध्नुहोस्', mai: 'AI सँ पूछू'
        },
        qa_choose_crop: {
            hi: 'फसल चुनें', en: 'Choose Crop', bn: 'ফসল বাছুন', te: 'పంట ఎంచుకోండి',
            mr: 'पीक निवडा', ta: 'பயிரைத் தேர்ந்தெடுக்கவும்', gu: 'પાક પસંદ કરો',
            kn: 'ಬೆಳೆ ಆರಿಸಿ', ml: 'വിള തിരഞ്ഞെടുക്കുക', pa: 'ਫ਼ਸਲ ਚੁਣੋ',
            or: 'ଫସଲ ବାଛନ୍ତୁ', as: 'শস্য বাছক', ur: 'فصل منتخب کریں',
            ne: 'बाली छान्नुहोस्', mai: 'फसल चुनू'
        },
        qa_mandi_price: {
            hi: 'मंडी भाव', en: 'Mandi Prices', bn: 'মান্ডি দাম', te: 'మండి ధరలు',
            mr: 'मंडी भाव', ta: 'மந்தி விலை', gu: 'મંડી ભાવ', kn: 'ಮಂಡಿ ದರ',
            ml: 'മണ്ടി വില', pa: 'ਮੰਡੀ ਭਾਅ', or: 'ମଣ୍ଡି ଦର', as: 'মণ্ডি দাম',
            ur: 'منڈی بھاؤ', ne: 'मन्डी भाउ', mai: 'मंडी भाव'
        },
        qa_photo_check: {
            hi: 'फोटो जांच', en: 'Photo Check', bn: 'ছবি পরীক্ষা', te: 'ఫోటో తనిఖీ',
            mr: 'फोटो तपासणी', ta: 'புகைப்பட சோதனை', gu: 'ફોટો તપાસ', kn: 'ಫೋಟೋ ಪರಿಶೀಲನೆ',
            ml: 'ഫോട്ടോ പരിശോധന', pa: 'ਫ਼ੋਟੋ ਜਾਂਚ', or: 'ଫଟୋ ଯାଞ୍ଚ', as: 'ফটো পৰীক্ষা',
            ur: 'تصویر جانچ', ne: 'फोटो जाँच', mai: 'फोटो जाँच'
        },
        services_eyebrow: {
            hi: 'काम चुनें', en: 'Choose a task', bn: 'একটি কাজ বাছুন', te: 'పనిని ఎంచుకోండి',
            mr: 'काम निवडा', ta: 'ஒரு பணியைத் தேர்ந்தெடுக்கவும்', gu: 'કામ પસંદ કરો',
            kn: 'ಕೆಲಸ ಆರಿಸಿ', ml: 'ജോലി തിരഞ്ഞെടുക്കുക', pa: 'ਕੰਮ ਚੁਣੋ',
            or: 'କାମ ବାଛନ୍ତୁ', as: 'কাম বাছক', ur: 'کام منتخب کریں',
            ne: 'काम छान्नुहोस्', mai: 'काज चुनू'
        },
        services_heading: {
            hi: 'आज आपको किस काम में मदद चाहिए?',
            en: 'What do you need help with today?',
            bn: 'আজ আপনার কোন কাজে সাহায্য দরকার?',
            te: 'ఈరోజు మీకు ఏ పనిలో సహాయం కావాలి?',
            mr: 'आज तुम्हाला कोणत्या कामात मदत हवी आहे?',
            ta: 'இன்று உங்களுக்கு எந்த வேலையில் உதவி தேவை?',
            gu: 'આજે તમને કયા કામમાં મદદ જોઈએ છે?',
            kn: 'ಇಂದು ನಿಮಗೆ ಯಾವ ಕೆಲಸದಲ್ಲಿ ಸಹಾಯ ಬೇಕು?',
            ml: 'ഇന്ന് നിങ്ങൾക്ക് ഏത് ജോലിയിലാണ് സഹായം വേണ്ടത്?',
            pa: 'ਅੱਜ ਤੁਹਾਨੂੰ ਕਿਸ ਕੰਮ ਵਿੱਚ ਮਦਦ ਚਾਹੀਦੀ ਹੈ?',
            or: 'ଆଜି ଆପଣଙ୍କୁ କେଉଁ କାମରେ ସାହାଯ୍ୟ ଦରକାର?',
            as: 'আজি আপোনাক কোন কামত সহায় লাগে?',
            ur: 'آج آپ کو کس کام میں مدد چاہیے؟',
            ne: 'आज तपाईंलाई कुन कामेमा सहयोग चाहिन्छ?',
            mai: 'आइ अहाँकेँ कोन काज मे मदति चाही?'
        },
        market_not_published_today: {
            hi: 'आज का सत्यापित मंडी भाव अभी प्रकाशित नहीं हुआ है',
            en: "Today's verified mandi price has not been published yet",
            bn: 'আজকের যাচাই করা মান্ডি দাম এখনও প্রকাশিত হয়নি',
            te: 'నేటి ధృవీకరించిన మండి ధర ఇంకా ప్రచురించబడలేదు',
            mr: 'आजचा पडताळलेला मंडी भाव अद्याप प्रकाशित झालेला नाही',
            ta: 'இன்றைய சரிபார்க்கப்பட்ட மந்தி விலை இதுவரை வெளியிடப்படவில்லை',
            gu: 'આજનો ચકાસાયેલ મંડી ભાવ હજુ પ્રકાશિત થયો નથી',
            kn: 'ಇಂದಿನ ಪರಿಶೀಲಿಸಿದ ಮಂಡಿ ದರ ಇನ್ನೂ ಪ್ರಕಟವಾಗಿಲ್ಲ',
            ml: 'ഇന്നത്തെ സ്ഥിരീകരിച്ച മണ്ടി വില ഇതുവരെ പ്രസിദ്ധീകരിച്ചിട്ടില്ല',
            pa: 'ਅੱਜ ਦਾ ਪ੍ਰਮਾਣਿਤ ਮੰਡੀ ਭਾਅ ਹਾਲੇ ਪ੍ਰਕਾਸ਼ਿਤ ਨਹੀਂ ਹੋਇਆ',
            or: 'ଆଜିର ଯାଞ୍ଚ ହୋଇଥିବା ମଣ୍ଡି ଦର ଏପର୍ଯ୍ୟନ୍ତ ପ୍ରକାଶିତ ହୋଇନାହିଁ',
            as: 'আজিৰ সত্যাপিত মণ্ডি দাম এতিয়াও প্ৰকাশ হোৱা নাই',
            ur: 'آج کی تصدیق شدہ منڈی قیمت ابھی شائع نہیں ہوئی',
            ne: 'आजको प्रमाणित मन्डी भाउ अझै प्रकाशित भएको छैन',
            mai: 'आइ के प्रमाणित मंडी भाव अखन धरि प्रकाशित नहि भेल अछि'
        },
        // Prefix for the most recent official row we do have, with its date.
        market_latest_official_report: {
            hi: 'नवीनतम आधिकारिक रिपोर्ट',
            en: 'Latest official report',
            bn: 'সর্বশেষ সরকারি প্রতিবেদন',
            te: 'తాజా అధికారిక నివేదిక',
            mr: 'नवीनतम अधिकृत अहवाल',
            ta: 'சமீபத்திய அதிகாரப்பூர்வ அறிக்கை',
            gu: 'નવીનતમ સત્તાવાર અહેવાલ',
            kn: 'ಇತ್ತೀಚಿನ ಅಧಿಕೃತ ವರದಿ',
            ml: 'ഏറ്റവും പുതിയ ഔദ്യോഗിക റിപ്പോർട്ട്',
            pa: 'ਨਵੀਨਤਮ ਸਰਕਾਰੀ ਰਿਪੋਰਟ',
            or: 'ସର୍ବଶେଷ ସରକାରୀ ରିପୋର୍ଟ',
            as: 'শেহতীয়া চৰকাৰী প্ৰতিবেদন',
            ur: 'تازہ ترین سرکاری رپورٹ',
            ne: 'पछिल्लो आधिकारिक प्रतिवेदन',
            mai: 'नवीनतम आधिकारिक रिपोर्ट'
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
        // Auth
        auth_login: {
            hi: 'लॉगिन', en: 'Login', mr: 'लॉगिन', ta: 'உள்நுழை', te: 'లాగిన్',
            gu: 'લૉગિન', pa: 'ਲੌਗਿਨ', bn: 'লগইন', kn: 'ಲಾಗಿನ್', ml: 'ലോഗിൻ',
            or: 'Login', as: 'Login', ur: 'Login', mai: 'Login', kok: 'Login',
            ne: 'Login', mni: 'Login', sd: 'Login', ks: 'Login', doi: 'Login',
            bo: 'Login', sat: 'Login'
        },
        auth_register: {
            hi: 'रजिस्टर', en: 'Register', mr: 'नोंदणी', ta: 'பதிவு', te: 'నమోదు',
            gu: 'નોંધણી', pa: 'ਰਜਿਸਟਰ', bn: 'নিবন্ধন', kn: 'ನೋಂದಣಿ', ml: 'രജിസ്റ്റർ',
            or: 'Register', as: 'Register', ur: 'Register', mai: 'Register', kok: 'Register',
            ne: 'Register', mni: 'Register', sd: 'Register', ks: 'Register', doi: 'Register',
            bo: 'Register', sat: 'Register'
        },
        auth_logout: {
            hi: 'लॉगआउट', en: 'Logout', mr: 'लॉगआउट', ta: 'வெளியேறு', te: 'లాగ్అవుట్',
            gu: 'લૉગઆઉટ', pa: 'ਲੌਗਆਉਟ', bn: 'লগআউট', kn: 'ಲಾಗ್ಔಟ್', ml: 'ലോഗ്ഔട്ട്',
            or: 'Logout', as: 'Logout', ur: 'Logout', mai: 'Logout', kok: 'Logout',
            ne: 'Logout', mni: 'Logout', sd: 'Logout', ks: 'Logout', doi: 'Logout',
            bo: 'Logout', sat: 'Logout'
        },
        auth_tab_otp: {
            hi: 'OTP लॉगिन', en: 'OTP Login', mr: 'OTP लॉगिन', ta: 'OTP உள்நுழைவு', te: 'OTP లాగిన్',
            gu: 'OTP લૉગિન', pa: 'OTP ਲੌਗਿਨ', bn: 'OTP লগইন', kn: 'OTP ಲಾಗಿನ್', ml: 'OTP ലോഗിൻ',
            or: 'OTP Login', as: 'OTP Login', ur: 'OTP Login', mai: 'OTP Login', kok: 'OTP Login',
            ne: 'OTP Login', mni: 'OTP Login', sd: 'OTP Login', ks: 'OTP Login', doi: 'OTP Login',
            bo: 'OTP Login', sat: 'OTP Login'
        },
        auth_tab_password: {
            hi: 'पासवर्ड', en: 'Password', mr: 'पासवर्ड', ta: 'கடவுச்சொல்', te: 'పాస్‌వర్డ్',
            gu: 'પાસવર્ડ', pa: 'ਪਾਸਵਰਡ', bn: 'পাসওয়ার্ড', kn: 'ಪಾಸ್‌ವರ್ಡ್', ml: 'പാസ്‌വേഡ്',
            or: 'Password', as: 'Password', ur: 'Password', mai: 'Password', kok: 'Password',
            ne: 'Password', mni: 'Password', sd: 'Password', ks: 'Password', doi: 'Password',
            bo: 'Password', sat: 'Password'
        },
        auth_tab_register: {
            hi: 'रजिस्टर', en: 'Register', mr: 'नोंदणी', ta: 'பதிவு', te: 'నమోదు',
            gu: 'નોંધણી', pa: 'ਰਜਿਸਟਰ', bn: 'নিবন্ধন', kn: 'ನೋಂದಣಿ', ml: 'രജിസ്റ്റർ',
            or: 'Register', as: 'Register', ur: 'Register', mai: 'Register', kok: 'Register',
            ne: 'Register', mni: 'Register', sd: 'Register', ks: 'Register', doi: 'Register',
            bo: 'Register', sat: 'Register'
        },
        auth_phone_label: {
            hi: 'मोबाइल नंबर', en: 'Mobile Number', mr: 'मोबाइल नंबर', ta: 'மொபைல் எண்', te: 'మొబైల్ నంబర్',
            gu: 'મોબાઈલ નંબર', pa: 'ਮੋਬਾਈਲ ਨੰਬਰ', bn: 'মোবাইল নম্বর', kn: 'ಮೊಬೈಲ್ ಸಂಖ್ಯೆ', ml: 'മൊബൈൽ നമ്പർ',
            or: 'Mobile Number', as: 'Mobile Number', ur: 'Mobile Number', mai: 'Mobile Number', kok: 'Mobile Number',
            ne: 'Mobile Number', mni: 'Mobile Number', sd: 'Mobile Number', ks: 'Mobile Number', doi: 'Mobile Number',
            bo: 'Mobile Number', sat: 'Mobile Number'
        },
        auth_otp_label: {
            hi: 'OTP दर्ज करें', en: 'Enter OTP', mr: 'OTP टाका', ta: 'OTP உள்ளிட', te: 'OTP నమోదు',
            gu: 'OTP દાખલ કરો', pa: 'OTP ਦਰਜ ਕਰੋ', bn: 'OTP লিখুন', kn: 'OTP ನಮೂದಿಸಿ', ml: 'OTP നൽകുക',
            or: 'Enter OTP', as: 'Enter OTP', ur: 'Enter OTP', mai: 'Enter OTP', kok: 'Enter OTP',
            ne: 'Enter OTP', mni: 'Enter OTP', sd: 'Enter OTP', ks: 'Enter OTP', doi: 'Enter OTP',
            bo: 'Enter OTP', sat: 'Enter OTP'
        },
        auth_send_otp: {
            hi: 'OTP भेजें', en: 'Send OTP', mr: 'OTP पाठवा', ta: 'OTP அனுப்பு', te: 'OTP పంపు',
            gu: 'OTP મોકલો', pa: 'OTP ਭੇਜੋ', bn: 'OTP পাঠান', kn: 'OTP ಕಳುಹಿಸಿ', ml: 'OTP അയക്കുക',
            or: 'Send OTP', as: 'Send OTP', ur: 'Send OTP', mai: 'Send OTP', kok: 'Send OTP',
            ne: 'Send OTP', mni: 'Send OTP', sd: 'Send OTP', ks: 'Send OTP', doi: 'Send OTP',
            bo: 'Send OTP', sat: 'Send OTP'
        },
        auth_verify_otp: {
            hi: 'OTP सत्यापित करें', en: 'Verify OTP', mr: 'OTP सत्यापित करा', ta: 'OTP சரிபார்', te: 'OTP ధృవీకరించు',
            gu: 'OTP ચકાસો', pa: 'OTP ਜਾਂਚੋ', bn: 'OTP যাচাই করুন', kn: 'OTP ಪರಿಶೀಲಿಸಿ', ml: 'OTP പരിശോധിക്കുക',
            or: 'Verify OTP', as: 'Verify OTP', ur: 'Verify OTP', mai: 'Verify OTP', kok: 'Verify OTP',
            ne: 'Verify OTP', mni: 'Verify OTP', sd: 'Verify OTP', ks: 'Verify OTP', doi: 'Verify OTP',
            bo: 'Verify OTP', sat: 'Verify OTP'
        },
        auth_password_label: {
            hi: 'पासवर्ड', en: 'Password', mr: 'पासवर्ड', ta: 'கடவுச்சொல்', te: 'పాస్‌వర్డ్',
            gu: 'પાસવર્ડ', pa: 'ਪਾਸਵਰਡ', bn: 'পাসওয়ার্ড', kn: 'ಪಾಸ್‌ವರ್ಡ್', ml: 'പാസ്‌വേഡ്',
            or: 'Password', as: 'Password', ur: 'Password', mai: 'Password', kok: 'Password',
            ne: 'Password', mni: 'Password', sd: 'Password', ks: 'Password', doi: 'Password',
            bo: 'Password', sat: 'Password'
        },
        auth_username_label: {
            hi: 'Username', en: 'Username', mr: 'Username', ta: 'பயனர்பெயர்', te: 'వినియోగదారు పేరు',
            gu: 'વપરાશકર્તા નામ', pa: 'ਯੂਜ਼ਰਨੇਮ', bn: 'ব্যবহারকারীর নাম', kn: 'ಬಳಕೆದಾರ ಹೆಸರು', ml: 'ഉപയോക്തൃ നാമം',
            or: 'Username', as: 'Username', ur: 'Username', mai: 'Username', kok: 'Username',
            ne: 'Username', mni: 'Username', sd: 'Username', ks: 'Username', doi: 'Username',
            bo: 'Username', sat: 'Username'
        },
        auth_name_label: {
            hi: 'नाम', en: 'Name', mr: 'नाव', ta: 'பெயர்', te: 'పేరు',
            gu: 'નામ', pa: 'ਨਾਮ', bn: 'নাম', kn: 'ಹೆಸರು', ml: 'പേര്',
            or: 'Name', as: 'Name', ur: 'Name', mai: 'Name', kok: 'Name',
            ne: 'Name', mni: 'Name', sd: 'Name', ks: 'Name', doi: 'Name',
            bo: 'Name', sat: 'Name'
        },
        auth_state_label: {
            hi: 'राज्य', en: 'State', mr: 'राज्य', ta: 'மாநிலம்', te: 'రాష్ట్రం',
            gu: 'રાજ્ય', pa: 'ਰਾਜ', bn: 'রাজ্য', kn: 'ರಾಜ್ಯ', ml: 'സംസ്ഥാനം',
            or: 'State', as: 'State', ur: 'State', mai: 'State', kok: 'State',
            ne: 'State', mni: 'State', sd: 'State', ks: 'State', doi: 'State',
            bo: 'State', sat: 'State'
        },
        auth_guest_continue: {
            hi: 'Guest के रूप में जारी रखें', en: 'Continue as Guest', mr: 'Guest म्हणून सुरू ठेवा',
            ta: 'விருந்தினராக தொடர', te: 'అతిథిగా కొనసాగించు',
            gu: 'Guest તરીકે ચાલુ રાખો', pa: 'Guest ਵਜੋਂ ਜਾਰੀ ਰੱਖੋ', bn: 'Guest হিসেবে চালিয়ে যান',
            kn: 'Guest ಆಗಿ ಮುಂದುವರಿಯಿರಿ', ml: 'Guest ആയി തുടരുക',
            or: 'Continue as Guest', as: 'Continue as Guest', ur: 'Continue as Guest',
            mai: 'Continue as Guest', kok: 'Continue as Guest', ne: 'Continue as Guest',
            mni: 'Continue as Guest', sd: 'Continue as Guest', ks: 'Continue as Guest',
            doi: 'Continue as Guest', bo: 'Continue as Guest', sat: 'Continue as Guest'
        },
        auth_welcome_back: {
            hi: 'वापस स्वागत है!', en: 'Welcome back!', mr: 'परत स्वागत!', ta: 'மீண்டும் வரவேற்கிறோம்!',
            te: 'తిరిగి స్వాగతం!', gu: 'પાછા આવવા માટે સ્વાગત!', pa: 'ਵਾਪਸ ਸੁਆਗਤ!',
            bn: 'ফিরে আসার জন্য স্বাগত!', kn: 'ಮರಳಿ ಸ್ವಾಗತ!', ml: 'തിരിച്ചു സ്വാഗതം!',
            or: 'Welcome back!', as: 'Welcome back!', ur: 'Welcome back!',
            mai: 'Welcome back!', kok: 'Welcome back!', ne: 'Welcome back!',
            mni: 'Welcome back!', sd: 'Welcome back!', ks: 'Welcome back!',
            doi: 'Welcome back!', bo: 'Welcome back!', sat: 'Welcome back!'
        },
        auth_error_invalid_otp: {
            hi: 'गलत OTP। दोबारा जांचें।', en: 'Invalid OTP. Please check.', mr: 'चुकीचा OTP.',
            ta: 'தவறான OTP.', te: 'తప్పు OTP.',
            gu: 'ખોટો OTP.', pa: 'ਗਲਤ OTP.', bn: 'ভুল OTP.',
            kn: 'ತಪ್ಪು OTP.', ml: 'തെറ്റായ OTP.',
            or: 'Invalid OTP.', as: 'Invalid OTP.', ur: 'Invalid OTP.',
            mai: 'Invalid OTP.', kok: 'Invalid OTP.', ne: 'Invalid OTP.',
            mni: 'Invalid OTP.', sd: 'Invalid OTP.', ks: 'Invalid OTP.',
            doi: 'Invalid OTP.', bo: 'Invalid OTP.', sat: 'Invalid OTP.'
        },
        auth_error_expired_otp: {
            hi: 'OTP समाप्त हो गया। नया OTP भेजें।', en: 'OTP expired. Request a new one.',
            mr: 'OTP कालबाह्य.', ta: 'OTP காலாவதி.', te: 'OTP గడువు ముగిసింది.',
            gu: 'OTP સમાપ્ત.', pa: 'OTP ਮਿਆਦ ਪੁੱਗ ਗਈ.', bn: 'OTP মেয়াদ শেষ.',
            kn: 'OTP ಅವಧಿ ಮೀರಿದೆ.', ml: 'OTP കാലഹരണപ്പെട്ടു.',
            or: 'OTP expired.', as: 'OTP expired.', ur: 'OTP expired.',
            mai: 'OTP expired.', kok: 'OTP expired.', ne: 'OTP expired.',
            mni: 'OTP expired.', sd: 'OTP expired.', ks: 'OTP expired.',
            doi: 'OTP expired.', bo: 'OTP expired.', sat: 'OTP expired.'
        },
        auth_error_rate_limit: {
            hi: 'बहुत अधिक प्रयास। 1 घंटे बाद कोशिश करें।', en: 'Too many attempts. Try after 1 hour.',
            mr: 'खूप जास्त प्रयत्न.', ta: 'அதிக முயற்சிகள்.', te: 'చాలా ప్రయత్నాలు.',
            gu: 'ઘણા પ્રયત્નો.', pa: 'ਬਹੁਤ ਜ਼ਿਆਦਾ ਕੋਸ਼ਿਸ਼ਾਂ.', bn: 'অনেক বেশি চেষ্টা.',
            kn: 'ಹಲವಾರು ಪ್ರಯತ್ನಗಳು.', ml: 'ഒരുപാട് ശ്രമങ്ങൾ.',
            or: 'Too many attempts.', as: 'Too many attempts.', ur: 'Too many attempts.',
            mai: 'Too many attempts.', kok: 'Too many attempts.', ne: 'Too many attempts.',
            mni: 'Too many attempts.', sd: 'Too many attempts.', ks: 'Too many attempts.',
            doi: 'Too many attempts.', bo: 'Too many attempts.', sat: 'Too many attempts.'
        },
        auth_error_network: {
            hi: 'इंटरनेट कनेक्शन जांचें।', en: 'Check internet connection.', mr: 'इंटरनेट तपासा.',
            ta: 'இணைய இணைப்பை சரிபார்க்கவும்.', te: 'ఇంటర్నెట్ తనిఖీ చేయండి.',
            gu: 'ઇન્ટરનેટ ચકાસો.', pa: 'ਇੰਟਰਨੈੱਟ ਜਾਂਚੋ.', bn: 'ইন্টারনেট পরীক্ষা করুন.',
            kn: 'ಇಂಟರ್ನೆಟ್ ಪರಿಶೀಲಿಸಿ.', ml: 'ഇന്റർനെറ്റ് പരിശോധിക്കുക.',
            or: 'Check internet connection.', as: 'Check internet connection.', ur: 'Check internet connection.',
            mai: 'Check internet connection.', kok: 'Check internet connection.', ne: 'Check internet connection.',
            mni: 'Check internet connection.', sd: 'Check internet connection.', ks: 'Check internet connection.',
            doi: 'Check internet connection.', bo: 'Check internet connection.', sat: 'Check internet connection.'
        },
        auth_resend_otp: {
            hi: 'OTP दोबारा भेजें', en: 'Resend OTP', mr: 'OTP पुन्हा पाठवा', ta: 'OTP மீண்டும் அனுப்பு',
            te: 'OTP మళ్లీ పంపు', gu: 'OTP ફરીથી મોકલો', pa: 'OTP ਦੁਬਾਰਾ ਭੇਜੋ',
            bn: 'OTP আবার পাঠান', kn: 'OTP ಮತ್ತೆ ಕಳುಹಿಸಿ', ml: 'OTP വീണ്ടും അയക്കുക',
            or: 'Resend OTP', as: 'Resend OTP', ur: 'Resend OTP',
            mai: 'Resend OTP', kok: 'Resend OTP', ne: 'Resend OTP',
            mni: 'Resend OTP', sd: 'Resend OTP', ks: 'Resend OTP',
            doi: 'Resend OTP', bo: 'Resend OTP', sat: 'Resend OTP'
        },
        auth_or_divider: {
            hi: 'या', en: 'or', mr: 'किंवा', ta: 'அல்லது', te: 'లేదా',
            gu: 'અથવા', pa: 'ਜਾਂ', bn: 'অথবা', kn: 'ಅಥವಾ', ml: 'അല്ലെങ്കിൽ',
            or: 'or', as: 'or', ur: 'or', mai: 'or', kok: 'or',
            ne: 'or', mni: 'or', sd: 'or', ks: 'or', doi: 'or',
            bo: 'or', sat: 'or'
        },

        // ── Farmer-facing controls that were hardcoded Hindi in index.html.
        // Before this, selecting Tamil left the crop-advisory form and the
        // bottom navigation in Devanagari, because the strings never reached
        // t() at all. Languages beyond these fall back hi -> en via t().
        bottomnav_home: { hi: 'होम', en: 'Home', bn: 'হোম', ta: 'முகப்பு', te: 'హోమ్', mr: 'होम', gu: 'હોમ', kn: 'ಮುಖಪುಟ', ml: 'ഹോം', pa: 'ਹੋਮ', or: 'ହୋମ', ur: 'ہوم', as: 'হোম', ne: 'होम' },
        bottomnav_weather: { hi: 'मौसम', en: 'Weather', bn: 'আবহাওয়া', ta: 'வானிலை', te: 'వాతావరణం', mr: 'हवामान', gu: 'હવામાન', kn: 'ಹವಾಮಾನ', ml: 'കാലാവസ്ഥ', pa: 'ਮੌਸਮ', or: 'ପାଣିପାଗ', ur: 'موسم', as: 'বতৰ', ne: 'मौसम' },
        bottomnav_market: { hi: 'बाजार', en: 'Market', bn: 'বাজার', ta: 'சந்தை', te: 'మార్కెట్', mr: 'बाजार', gu: 'બજાર', kn: 'ಮಾರುಕಟ್ಟೆ', ml: 'വിപണി', pa: 'ਬਾਜ਼ਾਰ', or: 'ବଜାର', ur: 'بازار', as: 'বজাৰ', ne: 'बजार' },
        bottomnav_more: { hi: 'और', en: 'More', bn: 'আরও', ta: 'மேலும்', te: 'మరిన్ని', mr: 'अधिक', gu: 'વધુ', kn: 'ಇನ್ನಷ್ಟು', ml: 'കൂടുതൽ', pa: 'ਹੋਰ', or: 'ଅଧିକ', ur: 'مزید', as: 'অধিক', ne: 'थप' },
        field_previous_crop: { hi: '🔄 पिछली फसल', en: '🔄 Previous crop', bn: '🔄 আগের ফসল', ta: '🔄 முந்தைய பயிர்', te: '🔄 మునుపటి పంట', mr: '🔄 मागील पीक', gu: '🔄 અગાઉનો પાક', kn: '🔄 ಹಿಂದಿನ ಬೆಳೆ', ml: '🔄 മുൻ വിള', pa: '🔄 ਪਿਛਲੀ ਫਸਲ', or: '🔄 ପୂର୍ବ ଫସଲ', ur: '🔄 پچھلی فصل', as: '🔄 আগৰ শস্য', ne: '🔄 अघिल्लो बाली' },
        field_irrigation_type: { hi: '🚿 सिंचाई प्रकार', en: '🚿 Irrigation type', bn: '🚿 সেচের ধরন', ta: '🚿 நீர்ப்பாசன வகை', te: '🚿 నీటిపారుదల రకం', mr: '🚿 सिंचन प्रकार', gu: '🚿 સિંચાઈનો પ્રકાર', kn: '🚿 ನೀರಾವರಿ ಪ್ರಕಾರ', ml: '🚿 ജലസേചന തരം', pa: '🚿 ਸਿੰਚਾਈ ਦੀ ਕਿਸਮ', or: '🚿 ଜଳସେଚନ ପ୍ରକାର', ur: '🚿 آبپاشی کی قسم', as: '🚿 জলসিঞ্চনৰ ধৰণ', ne: '🚿 सिँचाइको प्रकार' },
        opt_choose: { hi: '-- चुनें --', en: '-- Choose --', bn: '-- বাছুন --', ta: '-- தேர்ந்தெடுக்கவும் --', te: '-- ఎంచుకోండి --', mr: '-- निवडा --', gu: '-- પસંદ કરો --', kn: '-- ಆಯ್ಕೆಮಾಡಿ --', ml: '-- തിരഞ്ഞെടുക്കുക --', pa: '-- ਚੁਣੋ --', or: '-- ବାଛନ୍ତୁ --', ur: '-- منتخب کریں --', as: '-- বাছনি কৰক --', ne: '-- छान्नुहोस् --' },
        irr_drip: { hi: '💧 ड्रिप इरिगेशन', en: '💧 Drip irrigation', bn: '💧 ড্রিপ সেচ', ta: '💧 சொட்டு நீர்ப்பாசனம்', te: '💧 బిందు సేద్యం', mr: '💧 ठिबक सिंचन', gu: '💧 ટપક સિંચાઈ', kn: '💧 ಹನಿ ನೀರಾವರಿ', ml: '💧 തുള്ളിനന', pa: '💧 ਤੁਪਕਾ ਸਿੰਚਾਈ', or: '💧 ଡ୍ରିପ୍ ଜଳସେଚନ', ur: '💧 ڈرپ آبپاشی', as: '💧 ড্ৰিপ জলসিঞ্চন', ne: '💧 थोपा सिँचाइ' },
        irr_sprinkler: { hi: '🌧 स्प्रिंकलर', en: '🌧 Sprinkler', bn: '🌧 স্প্রিঙ্কলার', ta: '🌧 தெளிப்பான்', te: '🌧 స్ప్రింక్లర్', mr: '🌧 तुषार सिंचन', gu: '🌧 ફુવારા સિંચાઈ', kn: '🌧 ತುಂತುರು ನೀರಾವರಿ', ml: '🌧 സ്പ്രിംഗ്ലർ', pa: '🌧 ਫੁਹਾਰਾ ਸਿੰਚਾਈ', or: '🌧 ସ୍ପ୍ରିଙ୍କଲର', ur: '🌧 چھڑکاؤ آبپاشی', as: '🌧 স্প্ৰিংকলাৰ', ne: '🌧 स्प्रिंक्लर' },
        irr_flood: { hi: '🌊 बाढ़ सिंचाई', en: '🌊 Flood irrigation', bn: '🌊 প্লাবন সেচ', ta: '🌊 வெள்ள நீர்ப்பாசனம்', te: '🌊 వరద సేద్యం', mr: '🌊 पाट पाणी', gu: '🌊 પૂર સિંચાઈ', kn: '🌊 ಪ್ರವಾಹ ನೀರಾವರಿ', ml: '🌊 പ്ലാവന ജലസേചനം', pa: '🌊 ਹੜ੍ਹ ਸਿੰਚਾਈ', or: '🌊 ବନ୍ୟା ଜଳସେଚନ', ur: '🌊 سیلابی آبپاشی', as: '🌊 বান জলসিঞ্চন', ne: '🌊 डुबान सिँचाइ' },
        irr_rainfed: { hi: '🌦 वर्षा आधारित', en: '🌦 Rainfed', bn: '🌦 বৃষ্টিনির্ভর', ta: '🌦 மழையை நம்பிய', te: '🌦 వర్షాధారం', mr: '🌦 पावसावर अवलंबून', gu: '🌦 વરસાદ આધારિત', kn: '🌦 ಮಳೆ ಆಶ್ರಿತ', ml: '🌦 മഴയെ ആശ്രയിച്ച്', pa: '🌦 ਬਾਰਸ਼ ਆਧਾਰਿਤ', or: '🌦 ବର୍ଷା ଆଧାରିତ', ur: '🌦 بارانی', as: '🌦 বৰষুণ নিৰ্ভৰ', ne: '🌦 वर्षामा आधारित' },
        preset_fertile: { hi: '✅ उपजाऊ', en: '✅ Fertile', bn: '✅ উর্বর', ta: '✅ வளமான', te: '✅ సారవంతం', mr: '✅ सुपीक', gu: '✅ ફળદ્રુપ', kn: '✅ ಫಲವತ್ತಾದ', ml: '✅ ഫലഭൂയിഷ്ഠം', pa: '✅ ਉਪਜਾਊ', or: '✅ ଉର୍ବର', ur: '✅ زرخیز', as: '✅ উৰ্বৰ', ne: '✅ उर्वर' },
        preset_deficient: { hi: '⚠️ पोषण-कमी', en: '⚠️ Nutrient-poor', bn: '⚠️ পুষ্টি-ঘাটতি', ta: '⚠️ ஊட்டச்சத்து குறைவு', te: '⚠️ పోషక లోపం', mr: '⚠️ पोषण कमतरता', gu: '⚠️ પોષણ ઉણપ', kn: '⚠️ ಪೋಷಕಾಂಶ ಕೊರತೆ', ml: '⚠️ പോഷക കുറവ്', pa: '⚠️ ਪੌਸ਼ਟਿਕ ਘਾਟ', or: '⚠️ ପୋଷକ ଅଭାବ', ur: '⚠️ غذائی کمی', as: '⚠️ পুষ্টি ঘাটতি', ne: '⚠️ पोषण अभाव' },
        preset_saline: { hi: '🧂 लवणीय', en: '🧂 Saline', bn: '🧂 লবণাক্ত', ta: '🧂 உவர்ப்பு', te: '🧂 లవణ', mr: '🧂 क्षारयुक्त', gu: '🧂 ક્ષારીય', kn: '🧂 ಲವಣಾಂಶ', ml: '🧂 ലവണാംശം', pa: '🧂 ਖਾਰਾ', or: '🧂 ଲବଣାକ୍ତ', ur: '🧂 نمکین', as: '🧂 লোণা', ne: '🧂 नुनिलो' },
        preset_acidic: { hi: '⚗️ अम्लीय', en: '⚗️ Acidic', bn: '⚗️ অম্লীয়', ta: '⚗️ அமிலத்தன்மை', te: '⚗️ ఆమ్ల', mr: '⚗️ आम्लयुक्त', gu: '⚗️ એસિડિક', kn: '⚗️ ಆಮ್ಲೀಯ', ml: '⚗️ അമ്ലം', pa: '⚗️ ਤੇਜ਼ਾਬੀ', or: '⚗️ ଅମ୍ଳୀୟ', ur: '⚗️ تیزابی', as: '⚗️ অম্লীয়', ne: '⚗️ अम्लीय' },
        crop_get_advice: { hi: '🔬 फसल सलाह प्राप्त करें', en: '🔬 Get crop advice', bn: '🔬 ফসলের পরামর্শ নিন', ta: '🔬 பயிர் ஆலோசனை பெறுக', te: '🔬 పంట సలహా పొందండి', mr: '🔬 पीक सल्ला मिळवा', gu: '🔬 પાક સલાહ મેળવો', kn: '🔬 ಬೆಳೆ ಸಲಹೆ ಪಡೆಯಿರಿ', ml: '🔬 വിള ഉപദേശം നേടുക', pa: '🔬 ਫਸਲ ਸਲਾਹ ਲਵੋ', or: '🔬 ଫସଲ ପରାମର୍ଶ ନିଅନ୍ତୁ', ur: '🔬 فصل کا مشورہ لیں', as: '🔬 শস্যৰ পৰামৰ্শ লওক', ne: '🔬 बाली सल्लाह लिनुहोस्' },
        crop_soil_details: { hi: 'मिट्टी जाँच और खेत विवरण', en: 'Soil test and field details', bn: 'মাটি পরীক্ষা ও জমির বিবরণ', ta: 'மண் பரிசோதனை மற்றும் வயல் விவரம்', te: 'నేల పరీక్ష మరియు పొలం వివరాలు', mr: 'माती चाचणी आणि शेत तपशील', gu: 'માટી પરીક્ષણ અને ખેતર વિગત', kn: 'ಮಣ್ಣು ಪರೀಕ್ಷೆ ಮತ್ತು ಹೊಲದ ವಿವರ', ml: 'മണ്ണ് പരിശോധനയും വയൽ വിവരവും', pa: 'ਮਿੱਟੀ ਜਾਂਚ ਅਤੇ ਖੇਤ ਵੇਰਵਾ', or: 'ମାଟି ପରୀକ୍ଷା ଓ କ୍ଷେତ୍ର ବିବରଣୀ', ur: 'مٹی کی جانچ اور کھیت کی تفصیل', as: 'মাটি পৰীক্ষা আৰু পথাৰৰ বিৱৰণ', ne: 'माटो परीक्षण र खेत विवरण' },
        crop_all_crops: { hi: 'सभी फसलें', en: 'All crops', bn: 'সব ফসল', ta: 'அனைத்து பயிர்கள்', te: 'అన్ని పంటలు', mr: 'सर्व पिके', gu: 'બધા પાક', kn: 'ಎಲ್ಲಾ ಬೆಳೆಗಳು', ml: 'എല്ലാ വിളകളും', pa: 'ਸਾਰੀਆਂ ਫਸਲਾਂ', or: 'ସମସ୍ତ ଫସଲ', ur: 'تمام فصلیں', as: 'সকলো শস্য', ne: 'सबै बाली' },
        crop_search_label: { hi: '🌾 फसल खोजें', en: '🌾 Search crop', bn: '🌾 ফসল খুঁজুন', ta: '🌾 பயிரைத் தேடு', te: '🌾 పంట వెతకండి', mr: '🌾 पीक शोधा', gu: '🌾 પાક શોધો', kn: '🌾 ಬೆಳೆ ಹುಡುಕಿ', ml: '🌾 വിള തിരയുക', pa: '🌾 ਫਸਲ ਲੱਭੋ', or: '🌾 ଫସଲ ଖୋଜନ୍ତୁ', ur: '🌾 فصل تلاش کریں', as: '🌾 শস্য বিচাৰক', ne: '🌾 बाली खोज्नुहोस्' },
        mandi_list_label: { hi: '🏪 मंडी सूची:', en: '🏪 Mandi list:', bn: '🏪 মান্ডি তালিকা:', ta: '🏪 மண்டி பட்டியல்:', te: '🏪 మండి జాబితా:', mr: '🏪 मंडी यादी:', gu: '🏪 મંડી યાદી:', kn: '🏪 ಮಂಡಿ ಪಟ್ಟಿ:', ml: '🏪 മണ്ഡി പട്ടിക:', pa: '🏪 ਮੰਡੀ ਸੂਚੀ:', or: '🏪 ମଣ୍ଡି ତାଲିକା:', ur: '🏪 منڈی فہرست:', as: '🏪 মাণ্ডী তালিকা:', ne: '🏪 मन्डी सूची:' },
        mandi_whole_state: { hi: 'पूरा राज्य', en: 'Whole state', bn: 'সম্পূর্ণ রাজ্য', ta: 'முழு மாநிலம்', te: 'మొత్తం రాష్ట్రం', mr: 'संपूर्ण राज्य', gu: 'આખું રાજ્ય', kn: 'ಇಡೀ ರಾಜ್ಯ', ml: 'മുഴുവൻ സംസ്ഥാനം', pa: 'ਪੂਰਾ ਰਾਜ', or: 'ସମ୍ପୂର୍ଣ୍ଣ ରାଜ୍ୟ', ur: 'پورا ریاست', as: 'গোটেই ৰাজ্য', ne: 'पूरै प्रदेश' },
        mandi_load_more: { hi: 'और मंडियां', en: 'More mandis', bn: 'আরও মান্ডি', ta: 'மேலும் மண்டிகள்', te: 'మరిన్ని మండీలు', mr: 'अधिक मंड्या', gu: 'વધુ મંડીઓ', kn: 'ಇನ್ನಷ್ಟು ಮಂಡಿಗಳು', ml: 'കൂടുതൽ മണ്ഡികൾ', pa: 'ਹੋਰ ਮੰਡੀਆਂ', or: 'ଅଧିକ ମଣ୍ଡି', ur: 'مزید منڈیاں', as: 'অধিক মাণ্ডী', ne: 'थप मन्डीहरू' },

        // ── Second localisation pass: section headings, the location bar, the
        // farmer profile form, the auth form and the photo-quality tips. These
        // were hardcoded Hindi, so no language selection could reach them.
        sec_schemes: { hi: '🏛️ सरकारी योजनाएं', en: '🏛️ Government schemes', bn: '🏛️ সরকারি প্রকল্প', ta: '🏛️ அரசு திட்டங்கள்', te: '🏛️ ప్రభుత్వ పథకాలు', mr: '🏛️ सरकारी योजना', gu: '🏛️ સરકારી યોજનાઓ', kn: '🏛️ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು', ml: '🏛️ സർക്കാർ പദ്ധതികൾ', pa: '🏛️ ਸਰਕਾਰੀ ਸਕੀਮਾਂ', or: '🏛️ ସରକାରୀ ଯୋଜନା', ur: '🏛️ سرکاری اسکیمیں', as: '🏛️ চৰকাৰী আঁচনি', ne: '🏛️ सरकारी योजनाहरू' },
        sec_crops: { hi: '🌾 फसल सुझाव', en: '🌾 Crop recommendations', bn: '🌾 ফসলের পরামর্শ', ta: '🌾 பயிர் பரிந்துரைகள்', te: '🌾 పంట సిఫార్సులు', mr: '🌾 पीक शिफारशी', gu: '🌾 પાક ભલામણો', kn: '🌾 ಬೆಳೆ ಶಿಫಾರಸುಗಳು', ml: '🌾 വിള ശുപാർശകൾ', pa: '🌾 ਫਸਲ ਸਿਫਾਰਸ਼ਾਂ', or: '🌾 ଫସଲ ପରାମର୍ଶ', ur: '🌾 فصل کی سفارشات', as: '🌾 শস্যৰ পৰামৰ্শ', ne: '🌾 बाली सिफारिस' },
        sec_weather: { hi: '🌤️ मौसम पूर्वानुमान', en: '🌤️ Weather forecast', bn: '🌤️ আবহাওয়ার পূর্বাভাস', ta: '🌤️ வானிலை முன்னறிவிப்பு', te: '🌤️ వాతావరణ సూచన', mr: '🌤️ हवामान अंदाज', gu: '🌤️ હવામાન આગાહી', kn: '🌤️ ಹವಾಮಾನ ಮುನ್ಸೂಚನೆ', ml: '🌤️ കാലാവസ്ഥാ പ്രവചനം', pa: '🌤️ ਮੌਸਮ ਦੀ ਭਵਿੱਖਬਾਣੀ', or: '🌤️ ପାଣିପାଗ ପୂର୍ବାନୁମାନ', ur: '🌤️ موسم کی پیش گوئی', as: '🌤️ বতৰৰ পূৰ্বানুমান', ne: '🌤️ मौसम पूर्वानुमान' },
        sec_market: { hi: '💰 बाजार कीमतें', en: '💰 Market prices', bn: '💰 বাজার দর', ta: '💰 சந்தை விலைகள்', te: '💰 మార్కెట్ ధరలు', mr: '💰 बाजारभाव', gu: '💰 બજાર ભાવ', kn: '💰 ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು', ml: '💰 വിപണി വിലകൾ', pa: '💰 ਬਾਜ਼ਾਰ ਭਾਅ', or: '💰 ବଜାର ଦର', ur: '💰 بازار کے نرخ', as: '💰 বজাৰৰ দাম', ne: '💰 बजार भाउ' },
        sec_ai: { hi: '🤖 KrishiMitra AI सहायक', en: '🤖 KrishiMitra AI assistant', bn: '🤖 KrishiMitra AI সহায়ক', ta: '🤖 KrishiMitra AI உதவியாளர்', te: '🤖 KrishiMitra AI సహాయకుడు', mr: '🤖 KrishiMitra AI सहाय्यक', gu: '🤖 KrishiMitra AI સહાયક', kn: '🤖 KrishiMitra AI ಸಹಾಯಕ', ml: '🤖 KrishiMitra AI സഹായി', pa: '🤖 KrishiMitra AI ਸਹਾਇਕ', or: '🤖 KrishiMitra AI ସହାୟକ', ur: '🤖 KrishiMitra AI معاون', as: '🤖 KrishiMitra AI সহায়ক', ne: '🤖 KrishiMitra AI सहायक' },
        loc_label: { hi: '📍 स्थान:', en: '📍 Location:', bn: '📍 অবস্থান:', ta: '📍 இடம்:', te: '📍 స్థానం:', mr: '📍 ठिकाण:', gu: '📍 સ્થાન:', kn: '📍 ಸ್ಥಳ:', ml: '📍 സ്ഥലം:', pa: '📍 ਟਿਕਾਣਾ:', or: '📍 ସ୍ଥାନ:', ur: '📍 مقام:', as: '📍 স্থান:', ne: '📍 स्थान:' },
        loc_choose: { hi: 'स्थान चुनें या GPS चलाएं', en: 'Choose a location or use GPS', bn: 'অবস্থান বাছুন বা GPS চালান', ta: 'இடத்தைத் தேர்ந்தெடுக்கவும் அல்லது GPS பயன்படுத்தவும்', te: 'స్థానాన్ని ఎంచుకోండి లేదా GPS ఉపయోగించండి', mr: 'ठिकाण निवडा किंवा GPS वापरा', gu: 'સ્થાન પસંદ કરો અથવા GPS વાપરો', kn: 'ಸ್ಥಳ ಆಯ್ಕೆಮಾಡಿ ಅಥವಾ GPS ಬಳಸಿ', ml: 'സ്ഥലം തിരഞ്ഞെടുക്കുക അല്ലെങ്കിൽ GPS ഉപയോഗിക്കുക', pa: 'ਟਿਕਾਣਾ ਚੁਣੋ ਜਾਂ GPS ਵਰਤੋ', or: 'ସ୍ଥାନ ବାଛନ୍ତୁ କିମ୍ବା GPS ବ୍ୟବହାର କରନ୍ତୁ', ur: 'مقام منتخب کریں یا GPS چلائیں', as: 'স্থান বাছনি কৰক বা GPS ব্যৱহাৰ কৰক', ne: 'स्थान छान्नुहोस् वा GPS चलाउनुहोस्' },
        btn_search: { hi: 'खोजें', en: 'Search', bn: 'খুঁজুন', ta: 'தேடு', te: 'వెతకండి', mr: 'शोधा', gu: 'શોધો', kn: 'ಹುಡುಕಿ', ml: 'തിരയുക', pa: 'ਲੱਭੋ', or: 'ଖୋଜନ୍ତୁ', ur: 'تلاش کریں', as: 'বিচাৰক', ne: 'खोज्नुहोस्' },
        mandi_all_option: { hi: '-- सभी मंडियां --', en: '-- All mandis --', bn: '-- সব মান্ডি --', ta: '-- அனைத்து மண்டிகள் --', te: '-- అన్ని మండీలు --', mr: '-- सर्व मंड्या --', gu: '-- બધી મંડીઓ --', kn: '-- ಎಲ್ಲಾ ಮಂಡಿಗಳು --', ml: '-- എല്ലാ മണ്ഡികളും --', pa: '-- ਸਾਰੀਆਂ ਮੰਡੀਆਂ --', or: '-- ସମସ୍ତ ମଣ୍ଡି --', ur: '-- تمام منڈیاں --', as: '-- সকলো মাণ্ডী --', ne: '-- सबै मन्डी --' },
        opt_choose_short: { hi: 'चुनें', en: 'Choose', bn: 'বাছুন', ta: 'தேர்ந்தெடுக்கவும்', te: 'ఎంచుకోండి', mr: 'निवडा', gu: 'પસંદ કરો', kn: 'ಆಯ್ಕೆಮಾಡಿ', ml: 'തിരഞ്ഞെടുക്കുക', pa: 'ਚੁਣੋ', or: 'ବାଛନ୍ତୁ', ur: 'منتخب کریں', as: 'বাছনি কৰক', ne: 'छान्नुहोस्' },
        profile_title: { hi: 'मेरी किसान प्रोफ़ाइल', en: 'My farmer profile', bn: 'আমার কৃষক প্রোফাইল', ta: 'என் விவசாயி சுயவிவரம்', te: 'నా రైతు ప్రొఫైల్', mr: 'माझी शेतकरी प्रोफाइल', gu: 'મારી ખેડૂત પ્રોફાઇલ', kn: 'ನನ್ನ ರೈತ ಪ್ರೊಫೈಲ್', ml: 'എന്റെ കർഷക പ്രൊഫൈൽ', pa: 'ਮੇਰੀ ਕਿਸਾਨ ਪ੍ਰੋਫਾਈਲ', or: 'ମୋର କୃଷକ ପ୍ରୋଫାଇଲ', ur: 'میری کسان پروفائل', as: 'মোৰ কৃষক প্ৰফাইল', ne: 'मेरो किसान प्रोफाइल' },
        profile_sub: { hi: 'AI को बेहतर सलाह देने में मदद करें', en: 'Help the AI give better advice', bn: 'AI-কে আরও ভালো পরামর্শ দিতে সাহায্য করুন', ta: 'AI சிறந்த ஆலோசனை வழங்க உதவுங்கள்', te: 'AI మెరుగైన సలహా ఇవ్వడానికి సహాయపడండి', mr: 'AI ला अधिक चांगला सल्ला देण्यास मदत करा', gu: 'AI ને વધુ સારી સલાહ આપવામાં મદદ કરો', kn: 'AI ಉತ್ತಮ ಸಲಹೆ ನೀಡಲು ಸಹಾಯ ಮಾಡಿ', ml: 'AI-ക്ക് മികച്ച ഉപദേശം നൽകാൻ സഹായിക്കുക', pa: 'AI ਨੂੰ ਬਿਹਤਰ ਸਲਾਹ ਦੇਣ ਵਿੱਚ ਮਦਦ ਕਰੋ', or: 'AI କୁ ଭଲ ପରାମର୍ଶ ଦେବାରେ ସାହାଯ୍ୟ କରନ୍ତୁ', ur: 'AI کو بہتر مشورہ دینے میں مدد کریں', as: 'AI ক উন্নত পৰামৰ্শ দিবলৈ সহায় কৰক', ne: 'AI लाई राम्रो सल्लाह दिन मद्दत गर्नुहोस्' },
        profile_current_crop: { hi: '🌾 वर्तमान फसल', en: '🌾 Current crop', bn: '🌾 বর্তমান ফসল', ta: '🌾 தற்போதைய பயிர்', te: '🌾 ప్రస్తుత పంట', mr: '🌾 सध्याचे पीक', gu: '🌾 વર્તમાન પાક', kn: '🌾 ಪ್ರಸ್ತುತ ಬೆಳೆ', ml: '🌾 നിലവിലെ വിള', pa: '🌾 ਮੌਜੂਦਾ ਫਸਲ', or: '🌾 ବର୍ତ୍ତମାନ ଫସଲ', ur: '🌾 موجودہ فصل', as: '🌾 বৰ্তমানৰ শস্য', ne: '🌾 हालको बाली' },
        profile_farm_size: { hi: '📐 खेत (बीघा)', en: '📐 Farm size (bigha)', bn: '📐 জমির আকার (বিঘা)', ta: '📐 நில அளவு (பீகா)', te: '📐 పొలం విస్తీర్ణం (బీఘా)', mr: '📐 शेताचा आकार (बिघा)', gu: '📐 ખેતરનું કદ (વીઘા)', kn: '📐 ಹೊಲದ ಗಾತ್ರ (ಬಿಘಾ)', ml: '📐 വയലിന്റെ വലുപ്പം (ബീഘ)', pa: '📐 ਖੇਤ ਦਾ ਆਕਾਰ (ਵਿੱਘਾ)', or: '📐 କ୍ଷେତ୍ରର ଆକାର (ବିଘା)', ur: '📐 کھیت کا رقبہ (بیگھہ)', as: '📐 পথাৰৰ আকাৰ (বিঘা)', ne: '📐 खेतको आकार (बिघा)' },
        profile_soil_ph: { hi: '⚗️ मिट्टी pH', en: '⚗️ Soil pH', bn: '⚗️ মাটির pH', ta: '⚗️ மண் pH', te: '⚗️ నేల pH', mr: '⚗️ मातीचा pH', gu: '⚗️ માટીનો pH', kn: '⚗️ ಮಣ್ಣಿನ pH', ml: '⚗️ മണ്ണിന്റെ pH', pa: '⚗️ ਮਿੱਟੀ ਦਾ pH', or: '⚗️ ମାଟିର pH', ur: '⚗️ مٹی کا pH', as: '⚗️ মাটিৰ pH', ne: '⚗️ माटोको pH' },
        auth_mobile: { hi: '📱 मोबाइल नंबर', en: '📱 Mobile number', bn: '📱 মোবাইল নম্বর', ta: '📱 கைபேசி எண்', te: '📱 మొబైల్ నంబర్', mr: '📱 मोबाइल क्रमांक', gu: '📱 મોબાઇલ નંબર', kn: '📱 ಮೊಬೈಲ್ ಸಂಖ್ಯೆ', ml: '📱 മൊബൈൽ നമ്പർ', pa: '📱 ਮੋਬਾਈਲ ਨੰਬਰ', or: '📱 ମୋବାଇଲ ନମ୍ବର', ur: '📱 موبائل نمبر', as: '📱 ম\'বাইল নম্বৰ', ne: '📱 मोबाइल नम्बर' },
        auth_otp_enter: { hi: '🔑 6-अंकीय OTP दर्ज करें', en: '🔑 Enter the 6-digit OTP', bn: '🔑 ৬-সংখ্যার OTP দিন', ta: '🔑 6-இலக்க OTP-ஐ உள்ளிடவும்', te: '🔑 6-అంకెల OTP నమోదు చేయండి', mr: '🔑 6-अंकी OTP टाका', gu: '🔑 6-અંકનો OTP દાખલ કરો', kn: '🔑 6-ಅಂಕಿಯ OTP ನಮೂದಿಸಿ', ml: '🔑 6-അക്ക OTP നൽകുക', pa: '🔑 6-ਅੰਕਾਂ ਦਾ OTP ਭਰੋ', or: '🔑 6-ଅଙ୍କ OTP ଦିଅନ୍ତୁ', ur: '🔑 6 ہندسوں کا OTP درج کریں', as: '🔑 6-সংখ্যাৰ OTP দিয়ক', ne: '🔑 ६-अङ्कको OTP राख्नुहोस्' },
        auth_username: { hi: '👤 Username या email', en: '👤 Username or email', bn: '👤 ইউজারনেম বা ইমেল', ta: '👤 பயனர்பெயர் அல்லது மின்னஞ்சல்', te: '👤 యూజర్‌నేమ్ లేదా ఇమెయిల్', mr: '👤 वापरकर्तानाव किंवा ईमेल', gu: '👤 વપરાશકર્તાનામ અથવા ઈમેલ', kn: '👤 ಬಳಕೆದಾರಹೆಸರು ಅಥವಾ ಇಮೇಲ್', ml: '👤 ഉപയോക്തൃനാമം അല്ലെങ്കിൽ ഇമെയിൽ', pa: '👤 ਯੂਜ਼ਰਨੇਮ ਜਾਂ ਈਮੇਲ', or: '👤 ୟୁଜରନେମ କିମ୍ବା ଇମେଲ', ur: '👤 یوزر نیم یا ای میل', as: '👤 ইউজাৰনেম বা ইমেইল', ne: '👤 प्रयोगकर्तानाम वा इमेल' },
        auth_name_opt: { hi: '👤 नाम (वैकल्पिक)', en: '👤 Name (optional)', bn: '👤 নাম (ঐচ্ছিক)', ta: '👤 பெயர் (விருப்பம்)', te: '👤 పేరు (ఐచ్ఛికం)', mr: '👤 नाव (ऐच्छिक)', gu: '👤 નામ (વૈકલ્પિક)', kn: '👤 ಹೆಸರು (ಐಚ್ಛಿಕ)', ml: '👤 പേര് (ഐച്ഛികം)', pa: '👤 ਨਾਮ (ਵਿਕਲਪਿਕ)', or: '👤 ନାମ (ଐଚ୍ଛିକ)', ur: '👤 نام (اختیاری)', as: '👤 নাম (ঐচ্ছিক)', ne: '👤 नाम (ऐच्छिक)' },
        auth_mobile_opt: { hi: '📱 मोबाइल नंबर (वैकल्पिक)', en: '📱 Mobile number (optional)', bn: '📱 মোবাইল নম্বর (ঐচ্ছিক)', ta: '📱 கைபேசி எண் (விருப்பம்)', te: '📱 మొబైల్ నంబర్ (ఐచ్ఛికం)', mr: '📱 मोबाइल क्रमांक (ऐच्छिक)', gu: '📱 મોબાઇલ નંબર (વૈકલ્પિક)', kn: '📱 ಮೊಬೈಲ್ ಸಂಖ್ಯೆ (ಐಚ್ಛಿಕ)', ml: '📱 മൊബൈൽ നമ്പർ (ഐച്ഛികം)', pa: '📱 ਮੋਬਾਈਲ ਨੰਬਰ (ਵਿਕਲਪਿਕ)', or: '📱 ମୋବାଇଲ ନମ୍ବର (ଐଚ୍ଛିକ)', ur: '📱 موبائل نمبر (اختیاری)', as: '📱 ম\'বাইল নম্বৰ (ঐচ্ছিক)', ne: '📱 मोबाइल नम्बर (ऐच्छिक)' },
        auth_state_opt: { hi: '🗺️ राज्य (वैकल्पिक)', en: '🗺️ State (optional)', bn: '🗺️ রাজ্য (ঐচ্ছিক)', ta: '🗺️ மாநிலம் (விருப்பம்)', te: '🗺️ రాష్ట్రం (ఐచ్ఛికం)', mr: '🗺️ राज्य (ऐच्छिक)', gu: '🗺️ રાજ્ય (વૈકલ્પિક)', kn: '🗺️ ರಾಜ್ಯ (ಐಚ್ಛಿಕ)', ml: '🗺️ സംസ്ഥാനം (ഐച്ഛികം)', pa: '🗺️ ਰਾਜ (ਵਿਕਲਪਿਕ)', or: '🗺️ ରାଜ୍ୟ (ଐଚ୍ଛିକ)', ur: '🗺️ ریاست (اختیاری)', as: '🗺️ ৰাজ্য (ঐচ্ছিক)', ne: '🗺️ प्रदेश (ऐच्छिक)' },
        photo_tip_full: { hi: '5-10 फीट दूर से पूरी फसल', en: 'Whole plant from 5-10 feet away', bn: '৫-১০ ফুট দূর থেকে পুরো গাছ', ta: '5-10 அடி தூரத்திலிருந்து முழு செடி', te: '5-10 అడుగుల దూరం నుండి మొత్తం మొక్క', mr: '5-10 फूट अंतरावरून संपूर्ण पीक', gu: '5-10 ફૂટ દૂરથી આખો છોડ', kn: '5-10 ಅಡಿ ದೂರದಿಂದ ಇಡೀ ಸಸ್ಯ', ml: '5-10 അടി അകലെ നിന്ന് മുഴുവൻ ചെടിയും', pa: '5-10 ਫੁੱਟ ਦੂਰੋਂ ਪੂਰਾ ਪੌਦਾ', or: '5-10 ଫୁଟ ଦୂରରୁ ସମ୍ପୂର୍ଣ୍ଣ ଗଛ', ur: '5-10 فٹ دور سے پورا پودا', as: '5-10 ফুট দূৰৰ পৰা গোটেই গছ', ne: '५-१० फिट टाढाबाट पूरै बिरुवा' },
        photo_tip_close: { hi: 'रोग/कीट वाले भाग का नजदीकी फोटो', en: 'Close-up of the diseased or infested part', bn: 'রোগ/পোকা লাগা অংশের কাছের ছবি', ta: 'நோய்/பூச்சி பாதித்த பகுதியின் அருகிலான படம்', te: 'వ్యాధి/పురుగు ఉన్న భాగం దగ్గరి ఫోటో', mr: 'रोग/किडीच्या भागाचा जवळून फोटो', gu: 'રોગ/જીવાતવાળા ભાગનો નજીકનો ફોટો', kn: 'ರೋಗ/ಕೀಟ ಇರುವ ಭಾಗದ ಹತ್ತಿರದ ಫೋಟೋ', ml: 'രോഗം/കീടം ബാധിച്ച ഭാഗത്തിന്റെ അടുത്ത ചിത്രം', pa: 'ਬਿਮਾਰੀ/ਕੀੜੇ ਵਾਲੇ ਹਿੱਸੇ ਦੀ ਨੇੜਿਓਂ ਫੋਟੋ', or: 'ରୋଗ/କୀଟ ଥିବା ଅଂଶର ପାଖ ଫଟୋ', ur: 'بیماری/کیڑے والے حصے کی قریبی تصویر', as: 'ৰোগ/পোক লগা অংশৰ ওচৰৰ ফটো', ne: 'रोग/कीरा लागेको भागको नजिकको फोटो' },
        photo_tip_clear: { hi: 'पत्ती की नसें और धब्बे स्पष्ट दिखें', en: 'Leaf veins and spots should be clearly visible', bn: 'পাতার শিরা ও দাগ স্পষ্ট দেখা যাক', ta: 'இலை நரம்புகளும் புள்ளிகளும் தெளிவாகத் தெரிய வேண்டும்', te: 'ఆకు ఈనెలు మరియు మచ్చలు స్పష్టంగా కనిపించాలి', mr: 'पानाच्या शिरा आणि ठिपके स्पष्ट दिसावेत', gu: 'પાનની નસો અને ડાઘ સ્પષ્ટ દેખાવા જોઈએ', kn: 'ಎಲೆಯ ನರಗಳು ಮತ್ತು ಕಲೆಗಳು ಸ್ಪಷ್ಟವಾಗಿ ಕಾಣಬೇಕು', ml: 'ഇലയുടെ ഞരമ്പുകളും പുള്ളികളും വ്യക്തമായി കാണണം', pa: 'ਪੱਤੇ ਦੀਆਂ ਨਾੜਾਂ ਅਤੇ ਧੱਬੇ ਸਾਫ਼ ਦਿਸਣ', or: 'ପତ୍ରର ଶିରା ଓ ଦାଗ ସ୍ପଷ୍ଟ ଦେଖାଯାଉ', ur: 'پتے کی رگیں اور دھبے صاف نظر آئیں', as: 'পাতৰ শিৰা আৰু দাগ স্পষ্টকৈ দেখা যাওক', ne: 'पातका नसा र दाग स्पष्ट देखियोस्' },
        chat_history_title: { hi: 'पुरानी बातचीत', en: 'Past conversations', bn: 'আগের কথোপকথন', ta: 'முந்தைய உரையாடல்கள்', te: 'గత సంభాషణలు', mr: 'मागील संभाषणे', gu: 'અગાઉની વાતચીત', kn: 'ಹಿಂದಿನ ಸಂಭಾಷಣೆಗಳು', ml: 'മുൻ സംഭാഷണങ്ങൾ', pa: 'ਪਿਛਲੀਆਂ ਗੱਲਬਾਤਾਂ', or: 'ପୂର୍ବ କଥାବାର୍ତ୍ତା', ur: 'پچھلی گفتگو', as: 'আগৰ কথা-বতৰা', ne: 'विगतका कुराकानी' },
        chat_history_note: { hi: 'यह इतिहास केवल इसी डिवाइस पर रहता है।', en: 'This history stays on this device only.', bn: 'এই ইতিহাস কেবল এই ডিভাইসেই থাকে।', ta: 'இந்த வரலாறு இந்தச் சாதனத்தில் மட்டுமே இருக்கும்.', te: 'ఈ చరిత్ర ఈ పరికరంలో మాత్రమే ఉంటుంది.', mr: 'हा इतिहास फक्त याच उपकरणावर राहतो.', gu: 'આ ઇતિહાસ ફક્ત આ ડિવાઇસ પર જ રહે છે.', kn: 'ಈ ಇತಿಹಾಸ ಈ ಸಾಧನದಲ್ಲಿ ಮಾತ್ರ ಉಳಿಯುತ್ತದೆ.', ml: 'ഈ ചരിത്രം ഈ ഉപകരണത്തിൽ മാത്രം നിലനിൽക്കും.', pa: 'ਇਹ ਇਤਿਹਾਸ ਸਿਰਫ਼ ਇਸੇ ਡਿਵਾਈਸ ਉੱਤੇ ਰਹਿੰਦਾ ਹੈ।', or: 'ଏହି ଇତିହାସ କେବଳ ଏହି ଡିଭାଇସରେ ରହେ।', ur: 'یہ تاریخ صرف اسی ڈیوائس پر رہتی ہے۔', as: 'এই ইতিহাস কেৱল এই ডিভাইচতে থাকে।', ne: 'यो इतिहास यही यन्त्रमा मात्र रहन्छ।' },
        tagline: { hi: 'किसानों का डिजिटल सहायक', en: 'The farmer\'s digital assistant', bn: 'কৃষকের ডিজিটাল সহায়ক', ta: 'விவசாயியின் டிஜிட்டல் உதவியாளர்', te: 'రైతు డిజిటల్ సహాయకుడు', mr: 'शेतकऱ्यांचा डिजिटल सहाय्यक', gu: 'ખેડૂતોનો ડિજિટલ સહાયક', kn: 'ರೈತರ ಡಿಜಿಟಲ್ ಸಹಾಯಕ', ml: 'കർഷകരുടെ ഡിജിറ്റൽ സഹായി', pa: 'ਕਿਸਾਨਾਂ ਦਾ ਡਿਜੀਟਲ ਸਹਾਇਕ', or: 'କୃଷକଙ୍କ ଡିଜିଟାଲ ସହାୟକ', ur: 'کسانوں کا ڈیجیٹل معاون', as: 'কৃষকৰ ডিজিটেল সহায়ক', ne: 'किसानको डिजिटल सहायक' },
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
            } else if (target === 'aria-label') {
                el.setAttribute('aria-label', translated);
            } else {
                el.textContent = translated;
            }
        });
    };

    function _updateLanguageDropdown(code) {
        const sel = document.getElementById('languageSwitcher');
        if (sel) sel.value = code;
        const chatSel = document.getElementById('chatLanguageSwitcher');
        if (chatSel) chatSel.value = code;
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
