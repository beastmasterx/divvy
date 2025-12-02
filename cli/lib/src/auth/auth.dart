// Authentication service for Divvy CLI.
//
// Handles login, registration, and token management.

import 'package:dio/dio.dart';

import '../api/client.dart';
import '../api/schemas.dart';
import 'token.dart';

/// Authentication service.
class Auth {
  final DivvyClient _client;
  final TokenStorage _tokenStorage;

  Auth(this._client, this._tokenStorage);

  /// Login with email and password.
  ///
  /// Returns true if login successful, false otherwise.
  Future<bool> login(String email, String password) async {
    try {
      final response = await _client.authentication.tokenApiV1AuthTokenPost(
        grantType: 'password',
        username: email,
        password: password,
      );

      if (response.data != null) {
        await _saveTokens(response.data!);
        return true;
      }
      return false;
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        return false;
      }
      rethrow;
    }
  }

  /// Register a new user.
  ///
  /// Returns true if registration successful, false otherwise.
  Future<bool> register(String email, String name, String password) async {
    try {
      final request = RegisterRequest(
        (b) => b
          ..email = email
          ..name = name
          ..password = password,
      );

      final response = await _client.authentication.registerApiV1AuthRegisterPost(registerRequest: request);

      if (response.data != null) {
        await _saveTokens(response.data!);
        return true;
      }
      return false;
    } on DioException catch (e) {
      if (e.response?.statusCode == 409) {
        return false; // Email already exists
      }
      rethrow;
    }
  }

  /// Logout and clear tokens.
  Future<void> logout() async {
    try {
      // Try to revoke refresh token if available
      if (_tokenStorage.refreshToken != null) {
        await _client.authentication.revokeTokenApiV1AuthRevokePost(token: _tokenStorage.refreshToken!);
      }
    } catch (e) {
      // Ignore errors during logout
    } finally {
      await _tokenStorage.clear();
    }
  }

  /// Refresh access token using refresh token.
  ///
  /// Returns true if refresh successful, false otherwise.
  Future<bool> refreshToken() async {
    if (_tokenStorage.refreshToken == null) {
      return false;
    }

    try {
      final response = await _client.authentication.tokenApiV1AuthTokenPost(
        grantType: 'refresh_token',
        refreshToken: _tokenStorage.refreshToken,
      );

      if (response.data != null) {
        await _saveTokens(response.data!);
        return true;
      }
      return false;
    } on DioException {
      // Refresh failed, clear tokens
      await _tokenStorage.clear();
      return false;
    }
  }

  /// Check if user is authenticated.
  bool get isAuthenticated => _tokenStorage.isAuthenticated;

  /// Get current access token.
  String? get accessToken => _tokenStorage.accessToken;

  /// Save tokens from token response.
  Future<void> _saveTokens(TokenResponse tokenResponse) async {
    _tokenStorage.accessToken = tokenResponse.accessToken;
    _tokenStorage.refreshToken = tokenResponse.refreshToken;

    // Calculate expiration time (default to 1 hour if not provided)
    final expiresIn = tokenResponse.expiresIn;
    _tokenStorage.expiresAt = DateTime.now().add(Duration(seconds: expiresIn));

    await _tokenStorage.save();
  }
}
