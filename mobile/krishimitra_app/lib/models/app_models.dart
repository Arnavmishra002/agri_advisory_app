// ignore_for_file: non_constant_identifier_names

class ChatMessage {
  final String id;
  final String role;
  final String content;
  final DateTime timestamp;
  final String? intent;
  final String? dataSource;

  const ChatMessage({
    required this.id, required this.role,
    required this.content, required this.timestamp,
    this.intent, this.dataSource,
  });

  bool get isUser => role == 'user';

  factory ChatMessage.user(String text) => ChatMessage(
    id: DateTime.now().millisecondsSinceEpoch.toString(),
    role: 'user', content: text, timestamp: DateTime.now(),
  );

  factory ChatMessage.fromJson(Map<String, dynamic> j) => ChatMessage(
    id:         j['id']?.toString() ?? DateTime.now().millisecondsSinceEpoch.toString(),
    role:       j['role'] as String? ?? 'assistant',
    content:    (j['content'] ?? j['answer'] ?? j['response'] ?? '') as String,
    timestamp:  j['timestamp'] != null
                    ? DateTime.tryParse(j['timestamp'] as String) ?? DateTime.now()
                    : DateTime.now(),
    intent:     j['intent'] as String?,
    dataSource: j['data_source'] as String?,
  );

  Map<String, dynamic> toJson() => {
    'id': id, 'role': role, 'content': content,
    'timestamp': timestamp.toIso8601String(),
  };
}

class WeatherData {
  final String location;
  final double? temperature;
  final double? humidity;
  final double? rainfallMm;
  final String condition;
  final String conditionLocal;
  final String farmingAdvice;
  final List<ForecastDay> forecast;
  final bool isLive;
  final String dataSource;
  final int? dataAgeMinutes;   // minutes since observation was recorded
  final String fetchedAt;       // UTC ISO-8601 of when API was called

  const WeatherData({
    required this.location, this.temperature, this.humidity,
    this.rainfallMm, required this.condition, required this.conditionLocal,
    required this.farmingAdvice, required this.forecast,
    required this.isLive, this.dataSource = '',
    this.dataAgeMinutes, this.fetchedAt = '',
  });

  factory WeatherData.fromJson(Map<String, dynamic> j) {
    final cur = (j['current'] ?? j['current_weather']) as Map<String, dynamic>? ?? {};
    return WeatherData(
      location:        j['location'] as String? ?? '',
      temperature:     (cur['temperature'] as num?)?.toDouble(),
      humidity:        (cur['humidity'] as num?)?.toDouble(),
      rainfallMm:      (cur['rainfall_mm'] as num?)?.toDouble(),
      condition:       cur['condition'] as String? ?? '',
      conditionLocal:  cur['condition_local'] as String? ?? cur['condition'] as String? ?? '',
      farmingAdvice:   j['farming_advice'] as String? ?? '',
      isLive:          j['is_live'] as bool? ?? false,
      dataSource:      j['data_source'] as String? ?? '',
      dataAgeMinutes:  j['data_age_minutes'] as int?,
      fetchedAt:       j['fetched_at'] as String? ?? '',
      forecast: ((j['forecast_7day'] ?? j['forecast_7_days']) as List? ?? [])
          .map((d) => ForecastDay.fromJson(d as Map<String, dynamic>))
          .toList(),
    );
  }

  /// Human-readable data age label for display under the temperature.
  String get ageLabel {
    if (dataAgeMinutes == null) return '';
    if (dataAgeMinutes! < 2)  return 'Just updated';
    if (dataAgeMinutes! < 60) return '$dataAgeMinutes min ago';
    final h = (dataAgeMinutes! / 60).round();
    return '$h hour${h > 1 ? 's' : ''} ago';
  }
}

class ForecastDay {
  final String date;
  final double? maxTemp;
  final double? minTemp;
  final double? rainfallMm;
  final int? rainProb;

  const ForecastDay({required this.date, this.maxTemp, this.minTemp,
      this.rainfallMm, this.rainProb});

  factory ForecastDay.fromJson(Map<String, dynamic> j) => ForecastDay(
    date:       j['date'] as String? ?? '',
    maxTemp:    (j['max_temp'] as num?)?.toDouble(),
    minTemp:    (j['min_temp'] as num?)?.toDouble(),
    rainfallMm: (j['rainfall_mm'] as num?)?.toDouble(),
    rainProb:   j['rain_probability'] as int?,
  );
}

class MandiInfo {
  final String name;
  final String district;
  final String state;
  final double? distanceKm;
  final bool isLive;
  final String proximity;
  final String proximityLabel;

  const MandiInfo({
    required this.name, required this.district, required this.state,
    this.distanceKm, required this.isLive,
    this.proximity = 'unknown', this.proximityLabel = '',
  });

  factory MandiInfo.fromJson(Map<String, dynamic> j) => MandiInfo(
    name:           j['name']     as String? ?? '',
    district:       j['district'] as String? ?? '',
    state:          j['state']    as String? ?? '',
    distanceKm:     (j['distance_km'] as num?)?.toDouble(),
    isLive:         j['live']     as bool? ?? false,
    proximity:      j['proximity']       as String? ?? 'unknown',
    proximityLabel: j['proximity_label'] as String? ?? '',
  );

  String get distLabel =>
      distanceKm != null ? '${distanceKm!.toStringAsFixed(0)} km' : '';
}

class CropPrice {
  final String cropName;
  final String cropNameHindi;
  final String cropId;
  final double? modalPrice;
  final double? msp;
  final double? profitVsMsp;
  final String trend;
  final String mandiName;
  final bool isLive;
  final String reportedDate;   // "12-06-2026" from Agmarknet
  final String priceSource;    // "agmarknet_direct" | "live_mandi" | "msp_seasonal_estimate"
  final double? oneDayPrice;   // yesterday's price — enables trend display
  final double? twoDayPrice;

  const CropPrice({
    required this.cropName, required this.cropNameHindi, required this.cropId,
    this.modalPrice, this.msp, this.profitVsMsp, required this.trend,
    required this.mandiName, required this.isLive,
    this.reportedDate = '', this.priceSource = '',
    this.oneDayPrice, this.twoDayPrice,
  });

  factory CropPrice.fromJson(Map<String, dynamic> j) => CropPrice(
    cropName:      j['crop_name']       as String? ?? '',
    cropNameHindi: j['crop_name_hindi'] as String? ?? '',
    cropId:        j['crop_id']         as String? ?? '',
    modalPrice:    (j['modal_price']    as num?)?.toDouble(),
    msp:           (j['msp']            as num?)?.toDouble(),
    profitVsMsp:   (j['profit_vs_msp']  as num?)?.toDouble(),
    trend:         j['trend']           as String? ?? '',
    mandiName:     j['mandi_name']      as String? ?? '',
    isLive:        j['is_live']         as bool? ?? false,
    reportedDate:  j['reported_date']   as String? ?? '',
    priceSource:   j['price_source']    as String? ?? '',
    oneDayPrice:   (j['one_day_price']  as num?)?.toDouble(),
    twoDayPrice:   (j['two_day_price']  as num?)?.toDouble(),
  );

  bool get aboveMsp => (profitVsMsp ?? 0) >= 0;

  /// Human-readable age string: "आज" / "Today" for same-day, "X hours ago" otherwise.
  String ageLabel({bool hindi = true}) {
    if (reportedDate.isEmpty) return '';
    try {
      final parts = reportedDate.split('-');
      if (parts.length < 3) return reportedDate;
      final dt = DateTime(int.parse(parts[2]), int.parse(parts[1]), int.parse(parts[0]));
      final now = DateTime.now();
      final diffDays = now.difference(dt).inDays;
      if (diffDays == 0) return hindi ? 'आज (Agmarknet)' : 'Today (Agmarknet)';
      if (diffDays == 1) return hindi ? 'कल के भाव' : 'Yesterday';
      return hindi ? '$diffDays दिन पहले' : '$diffDays days ago';
    } catch (_) { return reportedDate; }
  }
}

class CropRec {
  final String cropName;
  final String cropNameHindi;
  final int score;
  final double profit;
  final int mspPerQuintal;
  final String season;
  final String reason;

  const CropRec({
    required this.cropName, required this.cropNameHindi,
    required this.score, required this.profit,
    required this.mspPerQuintal, required this.season, required this.reason,
  });

  factory CropRec.fromJson(Map<String, dynamic> j) => CropRec(
    // Handle both /api/advisories/ and /api/advisories/crop-recommendation/ formats
    cropName:      (j['crop_name'] ?? j['name'] ?? '') as String,
    cropNameHindi: (j['crop_name_hindi'] ?? j['name_hindi'] ?? j['hindi'] ?? '') as String,
    score:         ((j['suitability_score'] ?? j['score'] ?? 0) as num).toInt(),
    profit:        ((j['profit_per_hectare'] ?? j['profit'] ?? 0) as num).toDouble(),
    mspPerQuintal: ((j['msp_per_quintal'] ?? j['msp'] ?? 0) as num).toInt(),
    season:        (j['season'] ?? '') as String,
    reason:        ((j['reason_hindi'] ?? j['reason'] ?? j['season_fit'] ?? '') as String),
  );

  String get badge => score >= 85 ? '🟢' : score >= 65 ? '🟡' : '🔴';
  String get displayName => cropNameHindi.isNotEmpty ? cropNameHindi : cropName;
}
