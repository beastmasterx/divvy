// Token storage and management for authentication.
//
// Stores access and refresh tokens securely in a local file.

import 'dart:convert';
import 'dart:io';

/// Token storage for authentication tokens.
class TokenStorage {
  String? accessToken;
  String? refreshToken;
  DateTime? expiresAt;

  /// Optional config directory override (for testing).
  final String? _configDirOverride;

  TokenStorage({String? configDirOverride}) : _configDirOverride = configDirOverride;

  String get _configDir => _configDirOverride ?? _getConfigDirectory();
  String get _tokenPath => '$_configDir/tokens.json';

  /// Get the configuration directory based on platform.
  String _getConfigDirectory() {
    if (Platform.isWindows) {
      final appData = Platform.environment['APPDATA'];
      if (appData != null) {
        return '$appData\\divvy';
      }
      final username = Platform.environment['USERNAME'] ?? 'User';
      return 'C:\\Users\\$username\\.divvy';
    } else {
      final home = Platform.environment['HOME'];
      return home != null ? '$home/.divvy' : '.divvy';
    }
  }

  /// Load tokens from file.
  Future<void> load() async {
    final file = File(_tokenPath);
    if (!await file.exists()) {
      return;
    }

    try {
      final content = await file.readAsString();
      final json = jsonDecode(content) as Map<String, dynamic>;

      accessToken = json['accessToken'] as String?;
      refreshToken = json['refreshToken'] as String?;
      final expiresAtStr = json['expiresAt'] as String?;
      if (expiresAtStr != null) {
        expiresAt = DateTime.parse(expiresAtStr);
      }
    } catch (e) {
      // If file is corrupted, clear tokens
      accessToken = null;
      refreshToken = null;
      expiresAt = null;
    }
  }

  /// Save tokens to file.
  Future<void> save() async {
    final dir = Directory(_configDir);
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }

    final file = File(_tokenPath);
    final json = <String, dynamic>{};

    if (accessToken != null) {
      json['accessToken'] = accessToken;
    }
    if (refreshToken != null) {
      json['refreshToken'] = refreshToken;
    }
    if (expiresAt != null) {
      json['expiresAt'] = expiresAt!.toIso8601String();
    }

    await file.writeAsString(
      const JsonEncoder.withIndent('  ').convert(json),
    );
  }

  /// Clear all tokens.
  Future<void> clear() async {
    accessToken = null;
    refreshToken = null;
    expiresAt = null;

    final file = File(_tokenPath);
    if (await file.exists()) {
      await file.delete();
    }
  }

  /// Check if access token is expired or will expire soon (within 1 minute).
  bool get isExpired {
    if (expiresAt == null) return true;
    return DateTime.now().add(const Duration(minutes: 1)).isAfter(expiresAt!);
  }

  /// Check if user is authenticated.
  bool get isAuthenticated => accessToken != null && !isExpired;
}

