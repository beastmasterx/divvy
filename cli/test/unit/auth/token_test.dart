// Tests for token storage.

import 'dart:io';

import 'package:test/test.dart';
import 'package:cli/src/auth/token.dart';

void main() {
  group('TokenStorage', () {
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

    test('loads empty tokens when file does not exist', () async {
      final storage = TokenStorage(configDirOverride: tempDir.path);
      await storage.load();

      expect(storage.accessToken, isNull);
      expect(storage.refreshToken, isNull);
      expect(storage.expiresAt, isNull);
    });

    test('saves and loads tokens correctly', () async {
      final storage = TokenStorage(configDirOverride: tempDir.path);
      storage.accessToken = 'access_token_123';
      storage.refreshToken = 'refresh_token_456';
      storage.expiresAt = DateTime.now().add(const Duration(hours: 1));

      await storage.save();

      // Load in new instance
      final storage2 = TokenStorage(configDirOverride: tempDir.path);
      await storage2.load();

      expect(storage2.accessToken, 'access_token_123');
      expect(storage2.refreshToken, 'refresh_token_456');
      expect(storage2.expiresAt, isNotNull);
    });

    test('clears tokens correctly', () async {
      final storage = TokenStorage(configDirOverride: tempDir.path);
      storage.accessToken = 'token';
      storage.refreshToken = 'refresh';
      await storage.save();

      await storage.clear();

      expect(storage.accessToken, isNull);
      expect(storage.refreshToken, isNull);
      expect(storage.expiresAt, isNull);
    });

    test('isExpired returns true when expiresAt is null', () {
      final storage = TokenStorage(configDirOverride: tempDir.path);
      expect(storage.isExpired, isTrue);
    });

    test('isExpired returns false when token is not expired', () {
      final storage = TokenStorage(configDirOverride: tempDir.path);
      storage.expiresAt = DateTime.now().add(const Duration(hours: 1));
      expect(storage.isExpired, isFalse);
    });

    test('isExpired returns true when token is expired', () {
      final storage = TokenStorage(configDirOverride: tempDir.path);
      storage.expiresAt = DateTime.now().subtract(const Duration(hours: 1));
      expect(storage.isExpired, isTrue);
    });

    test('isExpired returns true when token expires within 1 minute', () {
      final storage = TokenStorage(configDirOverride: tempDir.path);
      storage.expiresAt = DateTime.now().add(const Duration(seconds: 30));
      expect(storage.isExpired, isTrue); // Within 1 minute buffer
    });

    test('isAuthenticated returns false when no token', () {
      final storage = TokenStorage(configDirOverride: tempDir.path);
      expect(storage.isAuthenticated, isFalse);
    });

    test('isAuthenticated returns true when token is valid', () {
      final storage = TokenStorage(configDirOverride: tempDir.path);
      storage.accessToken = 'token';
      storage.expiresAt = DateTime.now().add(const Duration(hours: 1));
      expect(storage.isAuthenticated, isTrue);
    });

    test('isAuthenticated returns false when token is expired', () {
      final storage = TokenStorage(configDirOverride: tempDir.path);
      storage.accessToken = 'token';
      storage.expiresAt = DateTime.now().subtract(const Duration(hours: 1));
      expect(storage.isAuthenticated, isFalse);
    });

    test('handles invalid JSON gracefully', () async {
      final storage = TokenStorage(configDirOverride: tempDir.path);
      await storage.save(); // Create file first

      // Corrupt the file
      final file = File('${tempDir.path}/tokens.json');
      await file.writeAsString('invalid json {');

      // Should not throw, should clear tokens
      final storage2 = TokenStorage(configDirOverride: tempDir.path);
      await storage2.load();
      expect(storage2.accessToken, isNull);
      expect(storage2.refreshToken, isNull);
    });
  });
}

