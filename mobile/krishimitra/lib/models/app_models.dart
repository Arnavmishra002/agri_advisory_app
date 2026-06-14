/// KrishiMitra App — Core Data Models
library;

// ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessage {
  final String id;
  final String role;        // 'user' | 'assistant'
  final String content;
  final DateTime timestamp;
  final String? intent;
  final String? language;
  final String? dataSource;
  final List<String> sources;

  const ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.timestamp,
    this.intent,
    this.language,
    this.dataSource,
    this.sources = const [],
  });

  bool get isUser => role == 'user';

  factory ChatMessage.fromJson(Map<String, dynamic> j) => ChatMessage(
    id:         j['id']        as String? ?? DateTime.now().toIso8601String(),
    role:       j['role']      as String? ?? 'assistant',
    content:    j['content']   as String? ?? j['answer'] as String? ?? '',
    timestamp:  j['timestamp'] != null
                    ? DateTime.tryParse(j['timestamp'] as String) ?? DateTime.now()
                    : DateTime.now(),
    intent:     j['intent']    as String?,
    language:   j['language']  as String?,
    dataSource: j['data_source'] as String?,
    sources:    (j['sources'] as List?)?.cast<String>() ?? [],
  );

  Map<String, dynamic> toJson() => {
    'id':        id,
    'role':      role,
    'content':   content,
    'timestamp': timestamp.toIso8601String(),
    'intent':    intent,
    'language':  language,
  };
}

// ── Weather ───────────────────────────────────────────────────────────────────

class WeatherData {
  final String location;
  final double? temperature;
  final double? humidity;
  final double? rainfallMm;
  final String condition;
  final String conditionLocal;
  final String farmingAdvice;
  final List<WeatherForecastDay> forecast;
  final bool isLive;

  const WeatherData({
    required this.location,
    this.temperature,
    this.humidity,
    this.rainfallMm,
    required this.condition,
    required this.conditionLocal,
    required this.farmingAdvice,
    required this.forecast,
    required this.isLive,
  });

  factory WeatherData.fromJson(Map<String, dynamic> j) {
    final cur = (j['current'] ?? j['current_weather']) as Map<String, dynamic>? ?? {};
    return WeatherData(
      location:       j['location'] as String? ?? '',
      temperature:    (cur['temperature'] as num?)?.toDouble(),
      humidity:       (cur['humidity'] as num?)?.toDouble(),
      rainfallMm:     (cur['rainfall_mm'] as num?)?.toDouble(),
      condition:      cur['condition'] as String? ?? '',
      conditionLocal: cur['condition_local'] as String? ?? '',
      farmingAdvice:  j['farming_advice'] as String? ?? '',
      isLive:         j['is_live'] as bool? ?? false,
      forecast: ((j['forecast_7day'] ?? j['forecast_7_days']) as List?)
          ?.map((d) => WeatherForecastDay.fromJson(d as Map<String, dynamic>))
          .toList() ?? [],
    );
  }
}

class WeatherForecastDay {
  final String date;
  final double? maxTemp;
  final double? minTemp;
  final double? rainfallMm;
  final int? rainProbability;

  const WeatherForecastDay({
    required this.date,
    this.maxTemp,
    this.minTemp,
    this.rainfallMm,
    this.rainProbability,
  });

  factory WeatherForecastDay.fromJson(Map<String, dynamic> j) => WeatherForecastDay(
    date:            j['date'] as String? ?? '',
    maxTemp:         (j['max_temp'] as num?)?.toDouble(),
    minTemp:         (j['min_temp'] as num?)?.toDouble(),
    rainfallMm:      (j['rainfall_mm'] as num?)?.toDouble(),
    rainProbability: j['rain_probability'] as int?,
  );
}

// ── Market / Mandi ────────────────────────────────────────────────────────────

class MandiInfo {
  final String name;
  final String district;
  final String state;
  final double? distanceKm;
  final bool isLive;
  final String proximity;       // 'very_near' | 'near' | 'regional' | 'unknown'
  final String proximityLabel;  // "~12 km — आपके पास"

  const MandiInfo({
    required this.name,
    required this.district,
    required this.state,
    this.distanceKm,
    required this.isLive,
    this.proximity = 'unknown',
    this.proximityLabel = '',
  });

  factory MandiInfo.fromJson(Map<String, dynamic> j) => MandiInfo(
    name:           j['name']     as String? ?? '',
    district:       j['district'] as String? ?? '',
    state:          j['state']    as String? ?? '',
    distanceKm:     (j['distance_km'] as num?)?.toDouble(),
    isLive:         j['live']     as bool? ?? false,
    proximity:      j['proximity'] as String? ?? 'unknown',
    proximityLabel: j['proximity_label'] as String? ?? '',
  );

  String get displayDistance => distanceKm != null
      ? '${distanceKm!.toStringAsFixed(0)} km'
      : '';
}

class CropPrice {
  final String cropName;
  final String cropNameHindi;
  final String cropId;
  final double? modalPrice;
  final double? msp;
  final double? profitVsMsp;
  final String trend;       // 'up' | 'down' | ''
  final String mandiName;
  final String state;
  final bool isLive;
  final double? oneDayPrice;

  const CropPrice({
    required this.cropName,
    required this.cropNameHindi,
    required this.cropId,
    this.modalPrice,
    this.msp,
    this.profitVsMsp,
    required this.trend,
    required this.mandiName,
    required this.state,
    required this.isLive,
    this.oneDayPrice,
  });

  factory CropPrice.fromJson(Map<String, dynamic> j) => CropPrice(
    cropName:       j['crop_name']        as String? ?? '',
    cropNameHindi:  j['crop_name_hindi']  as String? ?? '',
    cropId:         j['crop_id']          as String? ?? '',
    modalPrice:     (j['modal_price']     as num?)?.toDouble(),
    msp:            (j['msp']             as num?)?.toDouble(),
    profitVsMsp:    (j['profit_vs_msp']   as num?)?.toDouble(),
    trend:          j['trend']            as String? ?? '',
    mandiName:      j['mandi_name']       as String? ?? '',
    state:          j['state']            as String? ?? '',
    isLive:         j['is_live']          as bool? ?? false,
    oneDayPrice:    (j['one_day_price']   as num?)?.toDouble(),
  );

  bool get aboveMsp => (profitVsMsp ?? 0) >= 0;
}

// ── Crop Recommendation ───────────────────────────────────────────────────────

class CropRecommendation {
  final String cropName;
  final String cropNameHindi;
  final int suitabilityScore;
  final double profitPerHectare;
  final int mspPerQuintal;
  final String season;
  final String reason;

  const CropRecommendation({
    required this.cropName,
    required this.cropNameHindi,
    required this.suitabilityScore,
    required this.profitPerHectare,
    required this.mspPerQuintal,
    required this.season,
    required this.reason,
  });

  factory CropRecommendation.fromJson(Map<String, dynamic> j) => CropRecommendation(
    cropName:         j['crop_name']         as String? ?? '',
    cropNameHindi:    j['crop_name_hindi']    as String? ?? '',
    suitabilityScore: (j['suitability_score'] as num?)?.toInt() ?? 0,
    profitPerHectare: (j['profit_per_hectare'] as num?)?.toDouble() ?? 0,
    mspPerQuintal:    (j['msp_per_quintal']   as num?)?.toInt() ?? 0,
    season:           j['season']            as String? ?? '',
    reason:           (j['reason_hindi'] ?? j['reason']) as String? ?? '',
  );

  String get scoreLabel {
    if (suitabilityScore >= 85) return '🟢';
    if (suitabilityScore >= 65) return '🟡';
    return '🔴';
  }
}

// ── Government Scheme ─────────────────────────────────────────────────────────

class GovScheme {
  final String name;
  final String nameHindi;
  final String description;
  final String applyUrl;
  final String helpline;
  final String category;
  final double? benefitAmount;

  const GovScheme({
    required this.name,
    required this.nameHindi,
    required this.description,
    required this.applyUrl,
    required this.helpline,
    required this.category,
    this.benefitAmount,
  });

  factory GovScheme.fromJson(Map<String, dynamic> j) => GovScheme(
    name:          j['name']        as String? ?? '',
    nameHindi:     j['name_hindi']  as String? ?? j['name'] as String? ?? '',
    description:   j['description'] as String? ?? '',
    applyUrl:      j['apply_url']   as String? ?? j['url'] as String? ?? '',
    helpline:      j['helpline']    as String? ?? '',
    category:      j['category']    as String? ?? '',
    benefitAmount: (j['benefit_amount'] as num?)?.toDouble(),
  );
}

// ── Farmer Profile ────────────────────────────────────────────────────────────

class FarmerProfile {
  final String? sessionId;
  final String? phoneNumber;
  final String? name;
  final String? village;
  final String? district;
  final String? state;
  final double? farmSizeBigha;
  final String? currentCrop;
  final String? irrigationType;
  final String? soilType;
  final bool hasPmKisan;
  final String language;

  const FarmerProfile({
    this.sessionId,
    this.phoneNumber,
    this.name,
    this.village,
    this.district,
    this.state,
    this.farmSizeBigha,
    this.currentCrop,
    this.irrigationType,
    this.soilType,
    this.hasPmKisan = false,
    this.language = 'hi',
  });

  factory FarmerProfile.empty() => const FarmerProfile();

  Map<String, dynamic> toJson() => {
    if (sessionId   != null) 'session_id':      sessionId,
    if (phoneNumber != null) 'phone_number':     phoneNumber,
    if (name        != null) 'name':             name,
    if (village     != null) 'village':          village,
    if (district    != null) 'district':         district,
    if (state       != null) 'state':            state,
    if (farmSizeBigha != null) 'farm_size_bigha': farmSizeBigha,
    if (currentCrop != null) 'current_crop':     currentCrop,
    if (irrigationType != null) 'irrigation_type': irrigationType,
    if (soilType    != null) 'soil_type':        soilType,
    'has_pm_kisan':  hasPmKisan,
    'language':      language,
  };

  FarmerProfile copyWith({
    String? sessionId,
    String? phoneNumber,
    String? name,
    String? village,
    String? district,
    String? state,
    double? farmSizeBigha,
    String? currentCrop,
    String? irrigationType,
    String? soilType,
    bool?   hasPmKisan,
    String? language,
  }) => FarmerProfile(
    sessionId:      sessionId      ?? this.sessionId,
    phoneNumber:    phoneNumber    ?? this.phoneNumber,
    name:           name           ?? this.name,
    village:        village        ?? this.village,
    district:       district       ?? this.district,
    state:          state          ?? this.state,
    farmSizeBigha:  farmSizeBigha  ?? this.farmSizeBigha,
    currentCrop:    currentCrop    ?? this.currentCrop,
    irrigationType: irrigationType ?? this.irrigationType,
    soilType:       soilType       ?? this.soilType,
    hasPmKisan:     hasPmKisan     ?? this.hasPmKisan,
    language:       language       ?? this.language,
  );
}
