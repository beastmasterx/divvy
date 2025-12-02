// Preferences storage for Divvy CLI.
//
// Stores user preferences in a local JSON file:
// - Linux/macOS: ~/.divvy/preferences.json
// - Windows: %APPDATA%\divvy\preferences.json

import 'dart:convert';
import 'dart:io';

/// User preferences for the CLI application.
class Preferences {
  String language = 'en_US';
  String apiUrl = 'http://localhost:8000';
  int? defaultGroupId;
  int? lastActiveGroupId;
  int? lastActivePeriodId;

  /// Optional config directory override (for testing).
  final String? _configDirOverride;

  Preferences({String? configDirOverride}) : _configDirOverride = configDirOverride;

  String get _configDir => _configDirOverride ?? _getConfigDirectory();
  String get _configPath => '$_configDir/preferences.json';

  /// Get the configuration directory based on platform.
  String _getConfigDirectory() {
    if (Platform.isWindows) {
      final appData = Platform.environment['APPDATA'];
      if (appData != null) {
        return '$appData\\divvy';
      }
      // Fallback for Windows
      final username = Platform.environment['USERNAME'] ?? 'User';
      return 'C:\\Users\\$username\\.divvy';
    } else {
      // Linux/macOS
      final home = Platform.environment['HOME'];
      return home != null ? '$home/.divvy' : '.divvy';
    }
  }

  /// Load preferences from file, or use defaults if file doesn't exist.
  Future<void> load() async {
    final file = File(_configPath);
    if (!await file.exists()) {
      return; // Use defaults
    }

    try {
      final content = await file.readAsString();
      final json = jsonDecode(content) as Map<String, dynamic>;

      language = json['language'] as String? ?? 'en_US';
      apiUrl = json['apiUrl'] as String? ?? 'http://localhost:8000';
      defaultGroupId = json['defaultGroupId'] as int?;
      lastActiveGroupId = json['lastActiveGroupId'] as int?;
      lastActivePeriodId = json['lastActivePeriodId'] as int?;
    } catch (e) {
      // If file is corrupted, use defaults
      // Could log error in production
    }
  }

  /// Save preferences to file.
  Future<void> save() async {
    final dir = Directory(_configDir);
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }

    final file = File(_configPath);
    final json = <String, dynamic>{'language': language, 'apiUrl': apiUrl};

    if (defaultGroupId != null) {
      json['defaultGroupId'] = defaultGroupId;
    }
    if (lastActiveGroupId != null) {
      json['lastActiveGroupId'] = lastActiveGroupId;
    }
    if (lastActivePeriodId != null) {
      json['lastActivePeriodId'] = lastActivePeriodId;
    }

    await file.writeAsString(const JsonEncoder.withIndent('  ').convert(json));
  }

  /// Set the language preference.
  void setLanguage(String lang) {
    language = lang;
  }

  /// Set the API URL.
  void setApiUrl(String url) {
    apiUrl = url;
  }

  /// Set the default group ID.
  void setDefaultGroup(int? groupId) {
    defaultGroupId = groupId;
  }

  /// Set the last active group ID.
  void setLastActiveGroup(int? groupId) {
    lastActiveGroupId = groupId;
  }

  /// Set the last active period ID.
  void setLastActivePeriod(int? periodId) {
    lastActivePeriodId = periodId;
  }
}
