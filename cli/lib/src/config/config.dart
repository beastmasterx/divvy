// Configuration management for Divvy CLI.
//
// Loads configuration from preferences file.

import 'preferences.dart';

/// Application configuration loaded from preferences.
class Config {
  final Preferences preferences;

  /// API base URL.
  String get apiUrl => preferences.apiUrl;

  /// Base URL for Dio (alias for apiUrl).
  String get baseUrl => preferences.apiUrl;

  /// Current language setting.
  String get language => preferences.language;

  /// Default group ID.
  int? get defaultGroupId => preferences.defaultGroupId;

  /// Last active group ID.
  int? get lastActiveGroupId => preferences.lastActiveGroupId;

  /// Last active period ID.
  int? get lastActivePeriodId => preferences.lastActivePeriodId;

  Config._(this.preferences);

  /// Factory constructor for testing (allows injecting Preferences).
  factory Config.fromPreferences(Preferences preferences) {
    return Config._(preferences);
  }

  /// Load configuration from preferences file.
  static Future<Config> load() async {
    final prefs = Preferences();
    await prefs.load();
    return Config._(prefs);
  }
}
