// API client wrapper for Divvy API.
//
// Provides a convenient interface to the generated API client with
// configuration and error handling.

import 'dart:io';
import 'package:dio/dio.dart';
import 'package:divvy_api_client/src/api/members_api.dart';
import 'package:divvy_api_client/src/api/periods_api.dart';
import 'package:divvy_api_client/src/api/transactions_api.dart';
import 'package:divvy_api_client/src/api/settlement_api.dart';
import 'package:divvy_api_client/src/api/system_api.dart';
import 'package:divvy_api_client/src/api/categories_api.dart';
import 'package:divvy_api_client/src/serializers.dart';

/// Divvy API client wrapper.
class DivvyClient {
  late final Dio _dio;
  late final String _baseUrl;
  late final MembersApi _membersApi;
  late final PeriodsApi _periodsApi;
  late final TransactionsApi _transactionsApi;
  late final SettlementApi _settlementApi;
  late final SystemApi _systemApi;
  late final CategoriesApi _categoriesApi;

  DivvyClient({String? baseUrl}) {
    _baseUrl = baseUrl ?? _getBaseUrlFromEnv();
    _dio = Dio(
      BaseOptions(
        baseUrl: _baseUrl,
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 30),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    // Initialize API clients with serializers
    final serializers = standardSerializers;
    _membersApi = MembersApi(_dio, serializers);
    _periodsApi = PeriodsApi(_dio, serializers);
    _transactionsApi = TransactionsApi(_dio, serializers);
    _settlementApi = SettlementApi(_dio, serializers);
    _systemApi = SystemApi(_dio, serializers);
    _categoriesApi = CategoriesApi(_dio, serializers);
  }

  /// Get base URL from environment variable or use default.
  String _getBaseUrlFromEnv() {
    final envUrl = Platform.environment['DIVVY_API_URL'];
    if (envUrl != null && envUrl.isNotEmpty) {
      return envUrl;
    }
    return 'http://localhost:8000';
  }

  /// Get the base URL being used.
  String get baseUrl => _baseUrl;

  /// Get the Dio instance (for advanced usage).
  Dio get dio => _dio;

  /// Get the members API client
  MembersApi get members => _membersApi;

  /// Get the periods API client
  PeriodsApi get periods => _periodsApi;

  /// Get the transactions API client
  TransactionsApi get transactions => _transactionsApi;

  /// Get the settlement API client
  SettlementApi get settlement => _settlementApi;

  /// Get the system API client
  SystemApi get system => _systemApi;

  /// Get the categories API client
  CategoriesApi get categories => _categoriesApi;

  /// Handle API errors and convert to user-friendly messages.
  ///
  /// Parameters:
  /// - [error]: The error from Dio
  ///
  /// Returns:
  /// A user-friendly error message
  String handleError(dynamic error) {
    if (error is DioException) {
      switch (error.type) {
        case DioExceptionType.connectionTimeout:
        case DioExceptionType.sendTimeout:
        case DioExceptionType.receiveTimeout:
          return 'Connection timeout. Please check your network connection.';
        case DioExceptionType.badResponse:
          final statusCode = error.response?.statusCode;
          final message =
              error.response?.data?['detail'] ??
              error.response?.data?['message'] ??
              'Unknown error';
          if (statusCode == 404) {
            return 'Resource not found: $message';
          } else if (statusCode == 400) {
            return 'Invalid request: $message';
          } else if (statusCode == 422) {
            return 'Validation error: $message';
          } else {
            return 'Server error ($statusCode): $message';
          }
        case DioExceptionType.cancel:
          return 'Request cancelled.';
        case DioExceptionType.unknown:
          if (error.error is SocketException) {
            return 'Cannot connect to server. Please check if the API is running at $_baseUrl';
          }
          return 'Unknown error: ${error.message}';
        default:
          return 'Network error: ${error.message}';
      }
    }
    return 'Unexpected error: $error';
  }
}
