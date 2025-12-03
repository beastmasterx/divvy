// API client wrapper for Divvy API.
//
// Provides a convenient interface to the generated API client with
// authentication and error handling.

import 'package:dio/dio.dart';
import 'package:divvy_api_client/divvy_api_client.dart';

import '../auth/token.dart';

/// Divvy API client wrapper.
class Client {
  late final Dio _dio;
  late final String _baseUrl;
  late final TokenStorage _token;

  late final AuthenticationApi _authenticationApi;
  late final CategoriesApi _categoriesApi;
  late final GroupsApi _groupsApi;
  late final PeriodsApi _periodsApi;
  late final TransactionsApi _transactionsApi;
  late final UserApi _userApi;

  Client({required String baseUrl, required TokenStorage token}) : _baseUrl = baseUrl, _token = token {
    _dio = Dio(
      BaseOptions(
        baseUrl: _baseUrl,
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 30),
        headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
      ),
    );

    // Add interceptor for authentication
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          // Add access token to requests if available
          if (_token.accessToken != null) {
            options.headers['Authorization'] = 'Bearer ${_token.accessToken}';
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          // Handle 401 errors - token might be expired
          if (error.response?.statusCode == 401) {
            // Could implement token refresh here if needed
          }
          handler.next(error);
        },
      ),
    );

    // Initialize API clients with serializers
    final serializers = standardSerializers;
    _authenticationApi = AuthenticationApi(_dio, serializers);
    _categoriesApi = CategoriesApi(_dio, serializers);
    _groupsApi = GroupsApi(_dio, serializers);
    _periodsApi = PeriodsApi(_dio, serializers);
    _transactionsApi = TransactionsApi(_dio, serializers);
    _userApi = UserApi(_dio, serializers);
  }

  /// Get the base URL being used.
  String get baseUrl => _baseUrl;

  /// Get the Dio instance (for advanced usage).
  Dio get dio => _dio;

  /// Get the authentication API client.
  AuthenticationApi get authentication => _authenticationApi;

  /// Get the categories API client.
  CategoriesApi get categories => _categoriesApi;

  /// Get the groups API client.
  GroupsApi get groups => _groupsApi;

  /// Get the periods API client.
  PeriodsApi get periods => _periodsApi;

  /// Get the transactions API client.
  TransactionsApi get transactions => _transactionsApi;

  /// Get the user API client.
  UserApi get user => _userApi;

  /// Update access token (called after refresh).
  void updateAccessToken(String? token) {
    _token.accessToken = token;
  }
}
