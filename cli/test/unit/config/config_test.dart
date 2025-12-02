// Tests for configuration loading.

import 'dart:io';

import 'package:test/test.dart';
import 'package:cli/src/config/config.dart';
import 'package:cli/src/config/preferences.dart';

void main() {
  group('Config', () {
    late Directory tempDir;

    setUp(() {
      // Create temp directory for testing
      tempDir = Directory.systemTemp.createTempSync('divvy_test_');
    });

    tearDown(() {
      if (tempDir.existsSync()) {
        tempDir.deleteSync(recursive: true);
      }
    });

    test('loads default configuration when preferences file does not exist', () async {
      // Create preferences with test directory
      final prefs = Preferences(configDirOverride: tempDir.path);
      await prefs.load(); // Load defaults (file doesn't exist)
      
      final config = Config.fromPreferences(prefs);

      expect(config.language, 'en_US');
      expect(config.apiUrl, 'http://localhost:8000');
      expect(config.baseUrl, 'http://localhost:8000');
      expect(config.defaultGroupId, isNull);
    });

    test('loads configuration from preferences file', () async {
      // Create preferences file
      final prefs = Preferences(configDirOverride: tempDir.path);
      prefs.setLanguage('zh_CN');
      prefs.setApiUrl('http://example.com:8080');
      prefs.setDefaultGroup(1);
      prefs.setLastActiveGroup(2);
      prefs.setLastActivePeriod(3);
      await prefs.save();

      final prefs2 = Preferences(configDirOverride: tempDir.path);
      await prefs2.load();
      final config = Config.fromPreferences(prefs2);

      expect(config.language, 'zh_CN');
      expect(config.apiUrl, 'http://example.com:8080');
      expect(config.baseUrl, 'http://example.com:8080');
      expect(config.defaultGroupId, 1);
      expect(config.lastActiveGroupId, 2);
      expect(config.lastActivePeriodId, 3);
    });

    test('baseUrl returns same value as apiUrl', () async {
      final prefs = Preferences(configDirOverride: tempDir.path);
      await prefs.load();
      final config = Config.fromPreferences(prefs);
      expect(config.baseUrl, config.apiUrl);
    });
  });
}

