// Tests for preferences system.

import 'dart:io';

import 'package:test/test.dart';
import 'package:cli/src/config/preferences.dart';

void main() {
  group('Preferences', () {
    late Directory tempDir;

    setUp(() {
      // Create temp directory for testing
      tempDir = Directory.systemTemp.createTempSync('divvy_test_');
    });

    tearDown(() {
      // Clean up temp directory
      if (tempDir.existsSync()) {
        tempDir.deleteSync(recursive: true);
      }
    });

    test('loads default values when file does not exist', () async {
      final prefs = Preferences(configDirOverride: tempDir.path);
      await prefs.load();

      expect(prefs.language, 'en_US');
      expect(prefs.apiUrl, 'http://localhost:8000');
      expect(prefs.defaultGroupId, isNull);
      expect(prefs.lastActiveGroupId, isNull);
      expect(prefs.lastActivePeriodId, isNull);
    });

    test('saves and loads preferences correctly', () async {
      final prefs = Preferences(configDirOverride: tempDir.path);
      prefs.setLanguage('zh_CN');
      prefs.setApiUrl('http://example.com:8080');
      prefs.setDefaultGroup(1);
      prefs.setLastActiveGroup(2);
      prefs.setLastActivePeriod(3);

      await prefs.save();

      // Load in new instance
      final prefs2 = Preferences(configDirOverride: tempDir.path);
      await prefs2.load();

      expect(prefs2.language, 'zh_CN');
      expect(prefs2.apiUrl, 'http://example.com:8080');
      expect(prefs2.defaultGroupId, 1);
      expect(prefs2.lastActiveGroupId, 2);
      expect(prefs2.lastActivePeriodId, 3);
    });

    test('handles invalid JSON gracefully', () async {
      final prefs = Preferences(configDirOverride: tempDir.path);
      // Create a file with invalid JSON by saving first, then corrupting
      await prefs.save();
      final file = File('${tempDir.path}/preferences.json');
      await file.writeAsString('invalid json {');

      // Should not throw, should use defaults
      final prefs2 = Preferences(configDirOverride: tempDir.path);
      await prefs2.load();
      expect(prefs2.language, 'en_US');
      expect(prefs2.apiUrl, 'http://localhost:8000');
    });

    test('updates individual fields', () async {
      final prefs = Preferences(configDirOverride: tempDir.path);
      await prefs.load();

      prefs.setLanguage('zh_CN');
      expect(prefs.language, 'zh_CN');

      prefs.setApiUrl('http://test.com');
      expect(prefs.apiUrl, 'http://test.com');

      prefs.setDefaultGroup(5);
      expect(prefs.defaultGroupId, 5);

      prefs.setDefaultGroup(null);
      expect(prefs.defaultGroupId, isNull);
    });

    test('creates config directory if it does not exist', () async {
      final prefs = Preferences(configDirOverride: tempDir.path);
      final configDir = Directory(tempDir.path);
      if (configDir.existsSync()) {
        configDir.deleteSync(recursive: true);
      }

      await prefs.save();

      expect(configDir.existsSync(), isTrue);
      final file = File('${tempDir.path}/preferences.json');
      expect(file.existsSync(), isTrue);
    });
  });
}

